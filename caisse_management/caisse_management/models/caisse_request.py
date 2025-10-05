# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class CaisseRequest(models.Model):
    _name = 'caisse.request'
    _description = 'Demande de Fonds Caisse'
    _order = 'request_date desc, id desc'
    _rec_name = 'display_name'

    # Basic Information
    name = fields.Char(
        string='Référence',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouvelle Demande')
    )

    display_name = fields.Char(
        string='Nom d\'affichage',
        compute='_compute_display_name',
        store=True
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employé',
        required=True,
        default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1),
        tracking=True
    )

    request_date = fields.Datetime(
        string='Date de Demande',
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )

    # Request Details
    request_type_id = fields.Many2one(
        'caisse.request.type',
        string='Type de Demande',
        required=True,
        tracking=True
    )

    amount = fields.Float(
        string='Montant Demandé',
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
        string='Objet/Description',
        required=True,
        tracking=True
    )

    justification = fields.Text(
        string='Justification',
        help="Justification supplémentaire pour la demande"
    )

    # Analytical Tracking
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Compte Analytique',
        help="Compte analytique pour le suivi des dépenses"
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Département',
        related='employee_id.department_id',
        store=True,
        readonly=True
    )

    # Workflow States
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('submitted', 'Soumise'),
        ('manager_approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
        ('disbursed', 'Décaissé'),
        ('cancelled', 'Annulé')
    ], string='Statut', default='draft', tracking=True, readonly=True)

    # Approval Information
    manager_id = fields.Many2one(
        'hr.employee',
        string='Manager Approbateur',
        tracking=True
    )

    manager_approval_date = fields.Datetime(
        string='Date d\'Approbation Manager',
        tracking=True
    )

    manager_comments = fields.Text(
        string='Commentaires Manager'
    )

    cashier_id = fields.Many2one(
        'hr.employee',
        string='Caissier',
        tracking=True
    )

    disbursement_date = fields.Datetime(
        string='Date de Décaissement',
        tracking=True
    )

    # Settlement Information
    settlement_deadline = fields.Date(
        string='Date Limite de Règlement',
        compute='_compute_settlement_deadline',
        store=True
    )

    settlement_date = fields.Datetime(
        string='Date de Règlement',
        tracking=True
    )

    settlement_amount = fields.Float(
        string='Montant Réglé',
        help="Montant réglé (peut être différent du montant décaissé)"
    )

    settlement_description = fields.Text(
        string='Description du Règlement'
    )

    # Related Records
    disbursement_id = fields.Many2one(
        'caisse.disbursement',
        string='Décaissement Associé',
        readonly=True
    )

    move_id = fields.Many2one(
        'account.move',
        string='Écriture Comptable',
        readonly=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company
    )

    # Computed Fields
    is_overdue = fields.Boolean(
        string='En Retard',
        compute='_compute_is_overdue',
        store=True
    )

    days_to_settle = fields.Integer(
        string='Jours pour Régler',
        compute='_compute_days_to_settle'
    )

    @api.depends('name', 'employee_id', 'request_type_id', 'amount')
    def _compute_display_name(self):
        for record in self:
            if record.name and record.name != _('Nouvelle Demande'):
                employee_name = record.employee_id.name if record.employee_id else _('Employé Inconnu')
                record.display_name = f"{record.name} - {employee_name} ({record.amount:,.0f})"
            else:
                request_type_name = record.request_type_id.name if record.request_type_id else _('Nouveau')
                employee_name = record.employee_id.name if record.employee_id else _('Employé Inconnu')
                record.display_name = f"{request_type_name} - {employee_name}"

    @api.depends('disbursement_date', 'request_type_id')
    def _compute_settlement_deadline(self):
        config = self.env['caisse.config'].get_default_config()
        settlement_days = config.settlement_days if config else 30

        for record in self:
            if record.disbursement_date and record.request_type_id and record.request_type_id.code == 'advance':
                record.settlement_deadline = record.disbursement_date.date() + timedelta(days=settlement_days)
            else:
                record.settlement_deadline = False

    @api.depends('settlement_deadline', 'state')
    def _compute_is_overdue(self):
        today = fields.Date.today()
        for record in self:
            record.is_overdue = (
                record.settlement_deadline and
                record.settlement_deadline < today and
                record.state == 'disbursed'
            )

    @api.depends('settlement_deadline')
    def _compute_days_to_settle(self):
        today = fields.Date.today()
        for record in self:
            if record.settlement_deadline:
                delta = record.settlement_deadline - today
                record.days_to_settle = delta.days
            else:
                record.days_to_settle = 0

    @api.model
    def create(self, vals):
        if vals.get('name', _('Nouvelle Demande')) == _('Nouvelle Demande'):
            vals['name'] = self.env['ir.sequence'].next_by_code('caisse.request') or _('Nouvelle Demande')
        return super().create(vals)

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_("Le montant de la demande doit être supérieur à zéro"))

    def action_submit(self):
        """Submit request for approval"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Seules les demandes en brouillon peuvent être soumises"))

            # All requests must be submitted for manager approval
            record.state = 'submitted'
            # Request submitted for manager approval

    def action_approve(self):
        """Manager approval"""
        for record in self:
            if record.state != 'submitted':
                raise UserError(_("Seules les demandes soumises peuvent être approuvées"))

            record.state = 'manager_approved'
            record.manager_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
            record.manager_approval_date = fields.Datetime.now()
            # Request approved by manager

    def action_reject(self):
        """Reject request"""
        for record in self:
            if record.state not in ['submitted', 'manager_approved']:
                raise UserError(_("Seules les demandes soumises ou approuvées peuvent être rejetées"))

            record.state = 'rejected'
            # Request rejected

    def action_disburse(self):
        """Create and confirm disbursement in one step"""
        for record in self:
            if record.state != 'manager_approved':
                raise UserError(_("Seules les demandes approuvées peuvent être décaissées"))

            # Get caisse configuration
            config = self.env['caisse.config'].get_default_config()
            if not config:
                raise UserError(_("Configuration de la caisse introuvable"))

            # Get cashier (current user) - optional for flexibility
            cashier = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

            # Create disbursement record
            disbursement_vals = {
                'request_id': record.id,
                'employee_id': record.employee_id.id,
                'amount': record.amount,
                'description': record.description,
                'analytic_account_id': record.analytic_account_id.id if record.analytic_account_id else False,
                'journal_id': config.journal_id.id,
                'company_id': record.company_id.id,
            }

            # Add cashier if available, otherwise let the model handle it
            if cashier:
                disbursement_vals['cashier_id'] = cashier.id

            disbursement = self.env['caisse.disbursement'].create(disbursement_vals)

            # Automatically confirm the disbursement
            disbursement.action_disburse()

            record.disbursement_id = disbursement.id
            record.state = 'disbursed'
            if cashier:
                record.cashier_id = cashier.id
            record.disbursement_date = fields.Datetime.now()
            # Funds disbursed and accounting entries created

    def action_settle(self):
        """Mark request as settled"""
        for record in self:
            if record.state != 'disbursed':
                raise UserError(_("Seules les demandes décaissées peuvent être réglées"))

            record.state = 'settled'
            record.settlement_date = fields.Datetime.now()
            if not record.settlement_amount:
                record.settlement_amount = record.amount
            # Request settled

    def action_cancel(self):
        """Cancel request"""
        for record in self:
            if record.state == 'disbursed':
                raise UserError(_("Impossible d'annuler une demande décaissée"))

            record.state = 'cancelled'
            # Request cancelled

    def action_reset_to_draft(self):
        """Reset to draft"""
        for record in self:
            if record.state not in ['rejected', 'cancelled']:
                raise UserError(_("Seules les demandes rejetées ou annulées peuvent être remises en brouillon"))

            record.state = 'draft'
            # Request reset to draft

    def action_view_disbursement(self):
        """View related disbursement"""
        self.ensure_one()
        if not self.disbursement_id:
            raise UserError(_("Aucun décaissement trouvé pour cette demande"))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Décaissement'),
            'res_model': 'caisse.disbursement',
            'res_id': self.disbursement_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_accounting_entry(self):
        """View related accounting entry"""
        self.ensure_one()
        if not self.move_id:
            raise UserError(_("Aucune écriture comptable trouvée pour cette demande"))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Écriture Comptable'),
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }