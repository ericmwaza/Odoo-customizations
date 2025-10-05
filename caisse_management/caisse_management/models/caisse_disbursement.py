# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta


class CaisseDisbursement(models.Model):
    _name = 'caisse.disbursement'
    _description = 'Décaissement de Caisse'
    _order = 'disbursement_date desc, id desc'
    _rec_name = 'display_name'

    # Basic Information
    name = fields.Char(
        string='Référence',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau Décaissement')
    )

    display_name = fields.Char(
        string='Nom Affiché',
        compute='_compute_display_name',
        store=True
    )

    # Related Request
    request_id = fields.Many2one(
        'caisse.request',
        string='Demande Liée',
        required=True,
        ondelete='cascade'
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employé',
        required=True,
        tracking=True
    )

    # Disbursement Details
    disbursement_date = fields.Datetime(
        string='Date de Décaissement',
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )

    amount = fields.Float(
        string='Montant Décaissé',
        required=True,
        tracking=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    description = fields.Text(
        string='Description',
        required=True
    )

    # Payment Method
    payment_method = fields.Selection([
        ('cash', 'Espèces'),
        ('bank_transfer', 'Virement Bancaire'),
        ('check', 'Chèque')
    ], string='Mode de Paiement', default='cash', required=True)

    # Bank details for transfers
    bank_account_id = fields.Many2one(
        'res.partner.bank',
        string='Compte Bancaire',
        help="Compte bancaire de l'employé pour les virements"
    )

    check_number = fields.Char(
        string='Numéro de Chèque',
        help="Numéro du chèque si payé par chèque"
    )

    # Analytical Tracking
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Compte Analytique',
        help="Compte analytique pour le suivi des dépenses"
    )

    # Accounting
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        domain="[('type', 'in', ['cash', 'bank'])]"
    )

    move_id = fields.Many2one(
        'account.move',
        string='Accounting Entry',
        readonly=True,
        help="Generated accounting entry"
    )

    # Authorization
    cashier_id = fields.Many2one(
        'hr.employee',
        string='Cashier',
        required=False,
        default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1),
        tracking=True
    )

    authorized_by = fields.Many2one(
        'res.users',
        string='Authorized By',
        required=True,
        default=lambda self: self.env.user,
        tracking=True
    )

    # Status
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('disbursed', 'Décaissé'),
        ('cancelled', 'Annulé')
    ], string='Statut', default='draft', tracking=True)

    # Additional Information
    notes = fields.Text(
        string='Internal Notes'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    # Related Fields for easier access
    request_type_id = fields.Many2one(
        'caisse.request.type',
        related='request_id.request_type_id',
        string='Type de Demande',
        store=True,
        readonly=True
    )

    department_id = fields.Many2one(
        related='employee_id.department_id',
        string='Department',
        store=True,
        readonly=True
    )

    @api.depends('name', 'employee_id', 'amount')
    def _compute_display_name(self):
        for record in self:
            if record.name and record.name != _('New Disbursement'):
                record.display_name = f"{record.name} - {record.employee_id.name} ({record.amount:,.0f})"
            else:
                record.display_name = f"Disbursement - {record.employee_id.name}"

    @api.model
    def create(self, vals):
        if vals.get('name', _('New Disbursement')) == _('New Disbursement'):
            vals['name'] = self.env['ir.sequence'].next_by_code('caisse.disbursement') or _('New Disbursement')
        return super().create(vals)

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_("Disbursement amount must be greater than zero"))

    @api.constrains('amount', 'request_id')
    def _check_disbursement_amount(self):
        for record in self:
            if record.request_id and record.amount > record.request_id.amount:
                raise ValidationError(_("Disbursement amount cannot exceed requested amount"))

    @api.onchange('request_id')
    def _onchange_request_id(self):
        if self.request_id:
            self.employee_id = self.request_id.employee_id
            self.amount = self.request_id.amount
            self.description = self.request_id.description
            self.analytic_account_id = self.request_id.analytic_account_id

            # Set default journal from configuration
            config = self.env['caisse.config'].get_default_config()
            if config:
                self.journal_id = config.journal_id

    def action_disburse(self):
        """Confirm disbursement and create accounting entries"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Only draft disbursements can be confirmed"))

            # Validate disbursement limits
            self._validate_disbursement_limits()

            # Create accounting entries
            if record._should_create_accounting_entries():
                record._create_accounting_entries()

            record.state = 'disbursed'
            # Disbursement confirmed and accounting entries created

    def action_cancel(self):
        """Cancel disbursement"""
        for record in self:
            if record.state == 'disbursed' and record.move_id:
                raise UserError(_("Cannot cancel disbursement with posted accounting entries. Please reverse the entries first."))

            record.state = 'cancelled'
            if record.move_id:
                record.move_id.button_cancel()
            # Disbursement cancelled

    def _validate_disbursement_limits(self):
        """Validate disbursement against configured limits"""
        config = self.env['caisse.config'].get_default_config()
        if not config:
            return

        # Check single transaction limit
        if self.amount > config.cashier_disbursement_limit:
            raise UserError(_(
                "Le montant du décaissement (%.2f) dépasse la limite du caissier (%.2f)"
            ) % (self.amount, config.cashier_disbursement_limit))

        # Check daily limit
        today_disbursements = self.search([
            ('disbursement_date', '>=', fields.Date.today()),
            ('disbursement_date', '<', fields.Date.today() + timedelta(days=1)),
            ('state', '=', 'disbursed'),
            ('company_id', '=', self.company_id.id)
        ])

        total_today = sum(today_disbursements.mapped('amount')) + self.amount
        if total_today > config.daily_disbursement_limit:
            raise UserError(_(
                "Limite de décaissement journalière dépassée. Aujourd'hui: %.2f, Limite: %.2f"
            ) % (total_today, config.daily_disbursement_limit))

    def _should_create_accounting_entries(self):
        """Check if accounting entries should be created"""
        config = self.env['caisse.config'].get_default_config()
        return config and config.auto_create_accounting_entries

    def _create_accounting_entries(self):
        """Create accounting entries for the disbursement"""
        config = self.env['caisse.config'].get_default_config()
        if not config:
            raise UserError(_("Caisse configuration not found"))

        # Determine the account based on request type
        if self.request_type_id and self.request_type_id.code == 'advance':
            debit_account = config.advance_account_id
        else:
            debit_account = config.expense_account_id

        if not debit_account:
            raise UserError(_("Debit account not configured for request type: %s") % self.request_type)

        credit_account = self.journal_id.default_account_id
        if not credit_account:
            raise UserError(_("Default account not configured for journal: %s") % self.journal_id.name)

        # Create journal entry
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': self.disbursement_date.date(),
            'ref': f"Caisse Disbursement - {self.name}",
            'company_id': self.company_id.id,
            'line_ids': [
                (0, 0, {
                    'name': f"Disbursement to {self.employee_id.name} - {self.description}",
                    'account_id': debit_account.id,
                    'debit': self.amount,
                    'credit': 0.0,
                    'partner_id': self._get_employee_partner_id(),
                    'analytic_distribution': {self.analytic_account_id.id: 100} if self.analytic_account_id else False,
                }),
                (0, 0, {
                    'name': f"Cash disbursement - {self.name}",
                    'account_id': credit_account.id,
                    'debit': 0.0,
                    'credit': self.amount,
                    'analytic_distribution': {self.analytic_account_id.id: 100} if self.analytic_account_id else False,
                })
            ]
        }

        move = self.env['account.move'].create(move_vals)
        move.action_post()

        self.move_id = move.id
        if self.request_id:
            self.request_id.move_id = move.id

    def action_view_accounting_entry(self):
        """View the related accounting entry"""
        self.ensure_one()
        if not self.move_id:
            raise UserError(_("No accounting entry found for this disbursement"))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Accounting Entry'),
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _get_employee_partner_id(self):
        """Get the partner ID for the employee, handling different field structures"""
        if not self.employee_id:
            return False

        # Try different possible partner relationships
        if hasattr(self.employee_id, 'user_id') and self.employee_id.user_id:
            if hasattr(self.employee_id.user_id, 'partner_id') and self.employee_id.user_id.partner_id:
                return self.employee_id.user_id.partner_id.id

        # Try work_contact_id if it exists
        if hasattr(self.employee_id, 'work_contact_id') and self.employee_id.work_contact_id:
            return self.employee_id.work_contact_id.id

        # Try address_home_id if it exists (older versions)
        if hasattr(self.employee_id, 'address_home_id') and self.employee_id.address_home_id:
            return self.employee_id.address_home_id.id

        return False