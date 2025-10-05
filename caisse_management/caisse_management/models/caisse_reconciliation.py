# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class CaisseReconciliation(models.Model):
    _name = 'caisse.reconciliation'
    _description = 'Caisse Reconciliation'
    _order = 'reconciliation_date desc, id desc'
    _rec_name = 'display_name'

    # Basic Information
    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New Reconciliation')
    )

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    # Period Information
    reconciliation_date = fields.Date(
        string='Reconciliation Date',
        required=True,
        default=fields.Date.today,
        tracking=True
    )

    period_from = fields.Date(
        string='Period From',
        required=True,
        tracking=True
    )

    period_to = fields.Date(
        string='Period To',
        required=True,
        tracking=True
    )

    reconciliation_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('custom', 'Custom Period')
    ], string='Reconciliation Type', required=True, default='daily')

    # Balances
    opening_balance = fields.Float(
        string='Opening Balance',
        required=True,
        tracking=True
    )

    total_disbursements = fields.Float(
        string='Total Disbursements',
        compute='_compute_totals',
        store=True,
        readonly=True
    )

    total_receipts = fields.Float(
        string='Total Receipts',
        compute='_compute_totals',
        store=True,
        readonly=True
    )

    calculated_balance = fields.Float(
        string='Calculated Balance',
        compute='_compute_calculated_balance',
        store=True,
        readonly=True
    )

    actual_balance = fields.Float(
        string='Actual Balance',
        tracking=True,
        help="Actual physical cash count"
    )

    variance = fields.Float(
        string='Variance',
        compute='_compute_variance',
        store=True,
        readonly=True
    )

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('reconciled', 'Reconciled'),
        ('closed', 'Closed')
    ], string='Status', default='draft', tracking=True)

    # Reconciliation Details
    cashier_id = fields.Many2one(
        'hr.employee',
        string='Cashier',
        required=True,
        default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1),
        tracking=True
    )

    supervisor_id = fields.Many2one(
        'hr.employee',
        string='Supervisor',
        tracking=True
    )

    reconciliation_notes = fields.Text(
        string='Reconciliation Notes'
    )

    variance_explanation = fields.Text(
        string='Variance Explanation',
        help="Explanation for any variance between calculated and actual balance"
    )

    # Configuration
    config_id = fields.Many2one(
        'caisse.config',
        string='Caisse Configuration',
        required=True,
        default=lambda self: self.env['caisse.config'].get_default_config()
    )

    journal_id = fields.Many2one(
        related='config_id.journal_id',
        string='Journal',
        store=True,
        readonly=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        readonly=True
    )

    # Related Records
    disbursement_ids = fields.Many2many(
        'caisse.disbursement',
        string='Related Disbursements',
        compute='_compute_related_records',
        help="Disbursements in this reconciliation period"
    )

    disbursement_count = fields.Integer(
        string='Disbursement Count',
        compute='_compute_related_records'
    )

    # Cash Denomination Details
    denomination_line_ids = fields.One2many(
        'caisse.reconciliation.denomination',
        'reconciliation_id',
        string='Cash Denominations'
    )

    @api.depends('name', 'reconciliation_date', 'reconciliation_type')
    def _compute_display_name(self):
        for record in self:
            if record.name and record.name != _('New Reconciliation'):
                record.display_name = f"{record.name} - {record.reconciliation_date} ({record.reconciliation_type.title()})"
            else:
                record.display_name = f"{record.reconciliation_type.title()} Reconciliation - {record.reconciliation_date}"

    @api.depends('period_from', 'period_to')
    def _compute_totals(self):
        for record in self:
            if record.period_from and record.period_to:
                # Get disbursements in period
                disbursements = self.env['caisse.disbursement'].search([
                    ('disbursement_date', '>=', record.period_from),
                    ('disbursement_date', '<=', record.period_to),
                    ('state', '=', 'disbursed'),
                    ('company_id', '=', record.company_id.id)
                ])
                record.total_disbursements = sum(disbursements.mapped('amount'))

                # Get receipts in period (settlements, cash inflows)
                # For now, we'll track settlements as receipts
                settled_requests = self.env['caisse.request'].search([
                    ('settlement_date', '>=', record.period_from),
                    ('settlement_date', '<=', record.period_to),
                    ('state', '=', 'settled'),
                    ('company_id', '=', record.company_id.id)
                ])
                record.total_receipts = sum(settled_requests.mapped('settlement_amount'))
            else:
                record.total_disbursements = 0.0
                record.total_receipts = 0.0

    @api.depends('opening_balance', 'total_disbursements', 'total_receipts')
    def _compute_calculated_balance(self):
        for record in self:
            record.calculated_balance = record.opening_balance - record.total_disbursements + record.total_receipts

    @api.depends('calculated_balance', 'actual_balance')
    def _compute_variance(self):
        for record in self:
            record.variance = record.actual_balance - record.calculated_balance

    @api.depends('period_from', 'period_to')
    def _compute_related_records(self):
        for record in self:
            if record.period_from and record.period_to:
                disbursements = self.env['caisse.disbursement'].search([
                    ('disbursement_date', '>=', record.period_from),
                    ('disbursement_date', '<=', record.period_to),
                    ('state', '=', 'disbursed'),
                    ('company_id', '=', record.company_id.id)
                ])
                record.disbursement_ids = disbursements
                record.disbursement_count = len(disbursements)
            else:
                record.disbursement_ids = False
                record.disbursement_count = 0

    @api.model
    def create(self, vals):
        if vals.get('name', _('New Reconciliation')) == _('New Reconciliation'):
            vals['name'] = self.env['ir.sequence'].next_by_code('caisse.reconciliation') or _('New Reconciliation')
        return super().create(vals)

    @api.constrains('period_from', 'period_to')
    def _check_period(self):
        for record in self:
            if record.period_from > record.period_to:
                raise ValidationError(_("Period 'From' date must be before 'To' date"))

    @api.onchange('reconciliation_type', 'reconciliation_date')
    def _onchange_reconciliation_type(self):
        """Auto-set period based on reconciliation type"""
        if self.reconciliation_type and self.reconciliation_date:
            if self.reconciliation_type == 'daily':
                self.period_from = self.reconciliation_date
                self.period_to = self.reconciliation_date
            elif self.reconciliation_type == 'weekly':
                # Start of week (Monday)
                start_of_week = self.reconciliation_date - timedelta(days=self.reconciliation_date.weekday())
                self.period_from = start_of_week
                self.period_to = start_of_week + timedelta(days=6)
            elif self.reconciliation_type == 'monthly':
                # Start of month
                start_of_month = self.reconciliation_date.replace(day=1)
                # End of month
                if self.reconciliation_date.month == 12:
                    end_of_month = self.reconciliation_date.replace(year=self.reconciliation_date.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    end_of_month = self.reconciliation_date.replace(month=self.reconciliation_date.month + 1, day=1) - timedelta(days=1)
                self.period_from = start_of_month
                self.period_to = end_of_month

    def action_load_opening_balance(self):
        """Load opening balance from last reconciliation or journal"""
        self.ensure_one()

        # Find last reconciliation before this period
        last_reconciliation = self.search([
            ('period_to', '<', self.period_from),
            ('state', '=', 'closed'),
            ('company_id', '=', self.company_id.id)
        ], order='period_to desc', limit=1)

        if last_reconciliation:
            self.opening_balance = last_reconciliation.actual_balance
        else:
            # Calculate from journal balance
            if self.journal_id and self.journal_id.default_account_id:
                account_lines = self.env['account.move.line'].search([
                    ('account_id', '=', self.journal_id.default_account_id.id),
                    ('date', '<', self.period_from),
                    ('company_id', '=', self.company_id.id)
                ])
                self.opening_balance = sum(account_lines.mapped('balance'))

    def action_calculate_denominations(self):
        """Calculate actual balance from denominations"""
        self.ensure_one()
        total = sum(line.subtotal for line in self.denomination_line_ids)
        self.actual_balance = total

    def action_reconcile(self):
        """Mark reconciliation as complete"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Only draft reconciliations can be completed"))

            record.state = 'reconciled'
            # Reconciliation completed

    def action_close(self):
        """Close reconciliation period"""
        for record in self:
            if record.state != 'reconciled':
                raise UserError(_("Only reconciled periods can be closed"))

            # Require supervisor approval for closing
            if not record.supervisor_id:
                raise UserError(_("Supervisor approval required to close reconciliation"))

            record.state = 'closed'
            # Reconciliation period closed

    def action_reopen(self):
        """Reopen closed reconciliation"""
        for record in self:
            if record.state != 'closed':
                raise UserError(_("Only closed reconciliations can be reopened"))

            record.state = 'reconciled'
            # Reconciliation reopened

    def action_view_disbursements(self):
        """View disbursements in this period"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Period Disbursements'),
            'res_model': 'caisse.disbursement',
            'view_mode': 'list,form',
            'domain': [
                ('disbursement_date', '>=', self.period_from),
                ('disbursement_date', '<=', self.period_to),
                ('state', '=', 'disbursed'),
                ('company_id', '=', self.company_id.id)
            ],
            'target': 'current',
        }


class CaisseReconciliationDenomination(models.Model):
    _name = 'caisse.reconciliation.denomination'
    _description = 'Cash Denomination for Reconciliation'
    _order = 'denomination desc'

    reconciliation_id = fields.Many2one(
        'caisse.reconciliation',
        string='Reconciliation',
        required=True,
        ondelete='cascade'
    )

    denomination = fields.Float(
        string='Denomination',
        required=True,
        help="Value of each note/coin"
    )

    quantity = fields.Integer(
        string='Quantity',
        default=0,
        help="Number of notes/coins"
    )

    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_subtotal',
        store=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='reconciliation_id.company_id.currency_id',
        readonly=True
    )

    @api.depends('denomination', 'quantity')
    def _compute_subtotal(self):
        for record in self:
            record.subtotal = record.denomination * record.quantity