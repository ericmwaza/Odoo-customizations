# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class CaisseConfig(models.Model):
    _name = 'caisse.config'
    _description = 'Caisse Configuration'
    _rec_name = 'name'

    name = fields.Char(
        string='Nom de Configuration',
        required=True,
        default='Configuration Caisse Principale'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company
    )

    # Journal & Account Configuration
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal de Caisse',
        required=True,
        domain="[('type', 'in', ['cash', 'bank'])]",
        help="Le journal utilisé pour les décaissements"
    )

    advance_account_id = fields.Many2one(
        'account.account',
        string='Compte Avance Employé',
        required=True,
        help="Compte utilisé pour suivre les avances des employés"
    )

    expense_account_id = fields.Many2one(
        'account.account',
        string='Compte Petite Caisse',
        required=True,
        help="Compte utilisé pour les dépenses de petite caisse"
    )

    default_analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Compte Analytique par Défaut',
        help="Compte analytique par défaut pour les transactions"
    )

    # Approval Limits
    manager_approval_limit = fields.Float(
        string='Limite d\'Approbation Manager',
        default=10000.0,
        help="Montant maximum qu'un manager peut approuver"
    )

    cashier_disbursement_limit = fields.Float(
        string='Limite Décaissement Caissier',
        default=50000.0,
        help="Montant maximum qu'un caissier peut décaisser par transaction"
    )

    daily_disbursement_limit = fields.Float(
        string='Limite Décaissement Journalière',
        default=200000.0,
        help="Montant total maximum pouvant être décaissé par jour"
    )

    # Workflow Settings
    require_manager_approval = fields.Boolean(
        string='Approbation Manager Requise',
        default=True,
        help="Si l'approbation du manager est requise pour les demandes"
    )

    auto_create_accounting_entries = fields.Boolean(
        string='Créer Écritures Comptables Auto',
        default=True,
        help="Créer automatiquement les écritures comptables lors du décaissement"
    )

    settlement_days = fields.Integer(
        string='Jours de Règlement',
        default=30,
        help="Number of days to settle advances"
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    # Current Balance
    current_balance = fields.Float(
        string='Current Balance',
        compute='_compute_current_balance',
        store=False,
        help="Current balance of the caisse"
    )

    # Daily Available Balance
    daily_available_balance = fields.Float(
        string='Daily Available Balance',
        compute='_compute_daily_available_balance',
        store=False,
        help="Available balance for today considering daily limit and processed requests"
    )

    # Dashboard Statistics - Last 7 Days
    total_requests_7days = fields.Integer(
        string='Total Requests (7 days)',
        compute='_compute_dashboard_stats',
        store=False
    )
    approved_requests_7days = fields.Integer(
        string='Demandes Approuvées (7 jours)',
        compute='_compute_dashboard_stats',
        store=False
    )
    disbursed_requests_7days = fields.Integer(
        string='Demandes Décaissées (7 jours)',
        compute='_compute_dashboard_stats',
        store=False
    )
    rejected_requests_7days = fields.Integer(
        string='Demandes Rejetées (7 jours)',
        compute='_compute_dashboard_stats',
        store=False
    )

    # Dashboard Statistics - Alerts
    pending_approvals_count = fields.Integer(
        string='Approbations en Attente',
        compute='_compute_dashboard_stats',
        store=False
    )
    overdue_settlements_count = fields.Integer(
        string='Règlements en Retard',
        compute='_compute_dashboard_stats',
        store=False
    )
    near_due_settlements_count = fields.Integer(
        string='Règlements Bientôt Dus',
        compute='_compute_dashboard_stats',
        store=False
    )
    pending_requests_count = fields.Integer(
        string='Demandes en Attente',
        compute='_compute_dashboard_stats',
        store=False
    )

    # Dashboard Statistics - Today's Activity
    today_disbursed_count = fields.Integer(
        string='Décaissements Aujourd\'hui',
        compute='_compute_dashboard_stats',
        store=False
    )
    today_pending_count = fields.Integer(
        string='Demandes en Attente Aujourd\'hui',
        compute='_compute_dashboard_stats',
        store=False
    )

    # Approval Rate
    approval_rate = fields.Float(
        string='Approval Rate %',
        compute='_compute_dashboard_stats',
        store=False
    )
    rejection_rate = fields.Float(
        string='Rejection Rate %',
        compute='_compute_dashboard_stats',
        store=False
    )

    @api.depends('journal_id')
    def _compute_current_balance(self):
        for record in self:
            if record.journal_id:
                # Get the current balance from the journal's default account
                account = record.journal_id.default_account_id
                if account:
                    balance = self.env['account.move.line'].search([
                        ('account_id', '=', account.id),
                        ('company_id', '=', record.company_id.id)
                    ])
                    record.current_balance = sum(balance.mapped('balance'))
                else:
                    record.current_balance = 0.0
            else:
                record.current_balance = 0.0

    @api.depends('daily_disbursement_limit', 'company_id')
    def _compute_daily_available_balance(self):
        for record in self:
            if not record.daily_disbursement_limit or record.daily_disbursement_limit <= 0:
                # No limit - use current balance
                record.daily_available_balance = record.current_balance
            else:
                # Calculate today's disbursements
                today = fields.Date.today()
                today_disbursements = self.env['caisse.disbursement'].search([
                    ('disbursement_date', '>=', today),
                    ('disbursement_date', '<', today + timedelta(days=1)),
                    ('state', '=', 'disbursed'),
                    ('company_id', '=', record.company_id.id)
                ])

                total_today = sum(today_disbursements.mapped('amount'))
                remaining_limit = record.daily_disbursement_limit - total_today

                # Available balance is the minimum of remaining limit and current balance
                record.daily_available_balance = min(remaining_limit, record.current_balance) if remaining_limit > 0 else 0.0

    def _compute_dashboard_stats(self):
        """Compute all dashboard statistics"""
        for record in self:
            today = fields.Date.today()
            seven_days_ago = today - timedelta(days=7)

            # Get all requests for this company
            Request = self.env['caisse.request']

            # Last 7 days statistics
            requests_7days = Request.search([
                ('company_id', '=', record.company_id.id),
                ('request_date', '>=', seven_days_ago),
                ('request_date', '<=', today)
            ])

            record.total_requests_7days = len(requests_7days)
            record.approved_requests_7days = len(requests_7days.filtered(
                lambda r: r.state in ['manager_approved', 'disbursed']
            ))
            record.disbursed_requests_7days = len(requests_7days.filtered(
                lambda r: r.state == 'disbursed'
            ))
            record.rejected_requests_7days = len(requests_7days.filtered(
                lambda r: r.state == 'rejected'
            ))

            # Approval rate calculation
            total_processed = Request.search_count([
                ('company_id', '=', record.company_id.id),
                ('state', 'in', ['manager_approved', 'disbursed', 'rejected'])
            ])
            total_approved = Request.search_count([
                ('company_id', '=', record.company_id.id),
                ('state', 'in', ['manager_approved', 'disbursed'])
            ])

            if total_processed > 0:
                record.approval_rate = (total_approved / total_processed) * 100
                record.rejection_rate = 100 - record.approval_rate
            else:
                record.approval_rate = 0.0
                record.rejection_rate = 0.0

            # Alerts
            record.pending_approvals_count = Request.search_count([
                ('company_id', '=', record.company_id.id),
                ('state', '=', 'submitted')
            ])

            # Get advance request type
            advance_type = self.env['caisse.request.type'].search([('code', '=', 'advance')], limit=1)

            cutoff_date = today - timedelta(days=record.settlement_days)
            record.overdue_settlements_count = Request.search_count([
                ('company_id', '=', record.company_id.id),
                ('state', '=', 'disbursed'),
                ('request_type_id', '=', advance_type.id if advance_type else False),
                ('disbursement_date', '<=', cutoff_date)
            ]) if advance_type else 0

            near_due_date = today - timedelta(days=record.settlement_days - 3)  # 3 days before due
            record.near_due_settlements_count = Request.search_count([
                ('company_id', '=', record.company_id.id),
                ('state', '=', 'disbursed'),
                ('request_type_id', '=', advance_type.id if advance_type else False),
                ('disbursement_date', '<=', near_due_date),
                ('disbursement_date', '>', cutoff_date)
            ]) if advance_type else 0

            record.pending_requests_count = Request.search_count([
                ('company_id', '=', record.company_id.id),
                ('state', 'in', ['submitted', 'manager_approved'])
            ])

            # Today's activity - fix datetime comparison
            today_start = datetime.combine(today, datetime.min.time())
            today_end = datetime.combine(today, datetime.max.time())

            record.today_disbursed_count = Request.search_count([
                ('company_id', '=', record.company_id.id),
                ('state', '=', 'disbursed'),
                ('disbursement_date', '>=', today_start),
                ('disbursement_date', '<=', today_end)
            ])

            record.today_pending_count = Request.search_count([
                ('company_id', '=', record.company_id.id),
                ('state', 'in', ['submitted', 'manager_approved'])
            ])

    @api.constrains('manager_approval_limit', 'cashier_disbursement_limit', 'daily_disbursement_limit')
    def _check_limits(self):
        for record in self:
            if record.manager_approval_limit < 0:
                raise ValidationError(_("Manager approval limit must be positive"))
            if record.cashier_disbursement_limit < 0:
                raise ValidationError(_("Cashier disbursement limit must be positive"))
            if record.daily_disbursement_limit < 0:
                raise ValidationError(_("Daily disbursement limit must be positive"))

    @api.constrains('settlement_days')
    def _check_settlement_days(self):
        for record in self:
            if record.settlement_days <= 0:
                raise ValidationError(_("Settlement days must be greater than 0"))

    @api.constrains('company_id')
    def _check_unique_config_per_company(self):
        """Ensure only one active configuration per company"""
        for record in self:
            existing = self.search([
                ('company_id', '=', record.company_id.id),
                ('active', '=', True),
                ('id', '!=', record.id)
            ])
            if existing:
                raise ValidationError(_(
                    "Une seule configuration active est autorisée par société. "
                    "Veuillez désactiver l'autre configuration d'abord."
                ))

    @api.model
    def get_default_config(self):
        """Get the default configuration"""
        config = self.search([
            ('company_id', '=', self.env.company.id),
            ('active', '=', True)
        ], limit=1)
        return config

    @api.model
    def _create_default_config(self):
        """Create a default configuration with basic settings"""
        # Find a default cash journal
        cash_journal = self.env['account.journal'].search([
            ('type', 'in', ['cash', 'bank']),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        # Find default accounts (accounts are automatically filtered by current company in Odoo 18)
        advance_account = self.env['account.account'].search([
            ('code', '=like', '2%'),  # Usually liability accounts
        ], limit=1)

        expense_account = self.env['account.account'].search([
            ('code', '=like', '6%'),  # Usually expense accounts
        ], limit=1)

        config_vals = {
            'name': 'Default Caisse Configuration',
            'company_id': self.env.company.id,
            'manager_approval_limit': 10000.0,
            'cashier_disbursement_limit': 50000.0,
            'daily_disbursement_limit': 200000.0,
            'require_manager_approval': True,
            'auto_create_accounting_entries': True,
            'settlement_days': 30,
        }

        # Add journal and accounts if found
        if cash_journal:
            config_vals['journal_id'] = cash_journal.id
        if advance_account:
            config_vals['advance_account_id'] = advance_account.id
        if expense_account:
            config_vals['expense_account_id'] = expense_account.id

        return self.create(config_vals)

    @api.model
    def get_dashboard_config(self):
        """Get configuration for dashboard - create one if none exists"""
        config = self.get_default_config()
        if not config:
            # Create a default configuration automatically
            config = self._create_default_config()
        return config

    @api.model
    def default_get(self, fields_list):
        """Override default_get to ensure we have a configuration for dashboard"""
        res = super().default_get(fields_list)

        # If this is being called from dashboard context, try to use existing config
        if self.env.context.get('from_dashboard'):
            config = self.get_default_config()
            if config:
                # Return the existing config data
                for field in fields_list:
                    if hasattr(config, field):
                        res[field] = getattr(config, field)

        return res

    def action_dashboard_view(self):
        """Open dashboard view for this configuration"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Caisse Dashboard',
            'res_model': 'caisse.config',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def action_open_cashier_dashboard(self):
        """Open cashier dashboard with proper configuration"""
        config = self.get_default_config()
        if not config:
            # Create a default configuration automatically
            config = self._create_default_config()

        view_id = self.env.ref('caisse_management.view_caisse_dashboard_cashier').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cashier Dashboard',
            'res_model': 'caisse.config',
            'res_id': config.id,
            'view_mode': 'form',
            'view_id': view_id,
            'views': [(view_id, 'form')],
            'target': 'current',
        }

    @api.model
    def action_open_manager_dashboard(self):
        """Open manager dashboard with proper configuration"""
        config = self.get_default_config()
        if not config:
            # Create a default configuration automatically
            config = self._create_default_config()

        view_id = self.env.ref('caisse_management.view_caisse_dashboard_manager').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Manager Dashboard',
            'res_model': 'caisse.config',
            'res_id': config.id,
            'view_mode': 'form',
            'view_id': view_id,
            'views': [(view_id, 'form')],
            'target': 'current',
        }

    def validate_configuration(self):
        """Validate that the configuration is complete"""
        self.ensure_one()
        if not self.journal_id:
            raise UserError(_("Please configure a Cash Journal in the Caisse Configuration before proceeding."))
        if not self.advance_account_id:
            raise UserError(_("Please configure an Employee Advance Account in the Caisse Configuration."))
        if not self.expense_account_id:
            raise UserError(_("Please configure an Expense Account in the Caisse Configuration."))

    # Dashboard action methods
    def action_view_requests(self):
        """View all caisse requests"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fund Requests',
            'res_model': 'caisse.request',
            'view_mode': 'list,form',
            'domain': [('company_id', '=', self.company_id.id)],
            'target': 'current',
        }

    def action_view_disbursements(self):
        """View all disbursements"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Disbursements',
            'res_model': 'caisse.disbursement',
            'view_mode': 'list,form',
            'domain': [('company_id', '=', self.company_id.id)],
            'target': 'current',
        }

    def action_view_reconciliations(self):
        """View all reconciliations"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reconciliations',
            'res_model': 'caisse.reconciliation',
            'view_mode': 'list,form',
            'domain': [('company_id', '=', self.company_id.id)],
            'target': 'current',
        }

    def action_view_pending_requests(self):
        """View pending requests that need attention"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Demandes en Attente',
            'res_model': 'caisse.request',
            'view_mode': 'list,form',
            'domain': [
                ('company_id', '=', self.company_id.id),
                ('state', 'in', ['submitted', 'manager_approved'])
            ],
            'context': {},
            'target': 'current',
        }

    def action_view_pending_disbursements(self):
        """View requests approved and ready for disbursement"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Prêt pour Décaissement',
            'res_model': 'caisse.request',
            'view_mode': 'list,form',
            'domain': [
                ('company_id', '=', self.company_id.id),
                ('state', '=', 'manager_approved')
            ],
            'context': {},
            'target': 'current',
        }

    def action_create_reconciliation(self):
        """Create a new reconciliation"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'New Reconciliation',
            'res_model': 'caisse.reconciliation',
            'view_mode': 'form',
            'context': {
                'default_company_id': self.company_id.id,
                'default_reconciliation_date': fields.Date.today(),
                'default_state': 'draft',
            },
            'target': 'current',
        }

    def action_view_today_disbursements(self):
        """View today's disbursements - fixed to show disbursed requests"""
        today = fields.Date.today()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        return {
            'type': 'ir.actions.act_window',
            'name': 'Décaissements Aujourd\'hui',
            'res_model': 'caisse.request',
            'view_mode': 'list,form',
            'domain': [
                ('company_id', '=', self.company_id.id),
                ('disbursement_date', '>=', today_start),
                ('disbursement_date', '<=', today_end),
                ('state', '=', 'disbursed')
            ],
            'context': {},
            'target': 'current',
        }

    def action_view_requests_to_approve(self):
        """View requests requiring manager approval"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Demandes à Approuver',
            'res_model': 'caisse.request',
            'view_mode': 'list,form',
            'domain': [
                ('company_id', '=', self.company_id.id),
                ('state', '=', 'submitted')
            ],
            'context': {},
            'target': 'current',
        }

    def action_view_overdue_settlements(self):
        """View overdue advance settlements"""
        advance_type = self.env['caisse.request.type'].search([('code', '=', 'advance')], limit=1)
        cutoff_date = fields.Date.today() - timedelta(days=self.settlement_days)
        cutoff_datetime = datetime.combine(cutoff_date, datetime.max.time())

        domain = [
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'disbursed'),
            ('disbursement_date', '<=', cutoff_datetime)
        ]

        if advance_type:
            domain.append(('request_type_id', '=', advance_type.id))

        return {
            'type': 'ir.actions.act_window',
            'name': 'Règlements en Retard',
            'res_model': 'caisse.request',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {},
            'target': 'current',
        }

    def action_view_near_due_settlements(self):
        """View near due settlements (within 7 days of due date)"""
        advance_type = self.env['caisse.request.type'].search([('code', '=', 'advance')], limit=1)
        today = fields.Date.today()
        cutoff_date = today - timedelta(days=self.settlement_days)
        near_due_start = cutoff_date + timedelta(days=1)
        near_due_end = today - timedelta(days=self.settlement_days - 7)

        near_due_start_dt = datetime.combine(near_due_start, datetime.min.time())
        near_due_end_dt = datetime.combine(near_due_end, datetime.max.time())

        domain = [
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'disbursed'),
            ('disbursement_date', '>', near_due_start_dt),
            ('disbursement_date', '<=', near_due_end_dt)
        ]

        if advance_type:
            domain.append(('request_type_id', '=', advance_type.id))

        return {
            'type': 'ir.actions.act_window',
            'name': 'Règlements Arrive à Échéance',
            'res_model': 'caisse.request',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {},
            'target': 'current',
        }

    def action_view_all_requests(self):
        """View all requests"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Toutes les Demandes',
            'res_model': 'caisse.request',
            'view_mode': 'list,form',
            'domain': [('company_id', '=', self.company_id.id)],
            'context': {},
            'target': 'current',
        }

    def action_view_reports(self):
        """View reports dashboard or pivot view"""
        # Calculate first day of current month
        today = fields.Date.today()
        first_day_of_month = today.replace(day=1)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Caisse Reports',
            'res_model': 'caisse.request',
            'view_mode': 'pivot,graph',
            'domain': [
                ('company_id', '=', self.company_id.id),
                ('state', '=', 'disbursed'),
                ('request_date', '>=', first_day_of_month)
            ],
            'context': {
                'group_by': ['state', 'request_type_id', 'employee_id'],
            },
            'target': 'current',
        }

    def action_print_resume_caisse(self):
        """Print Resume Caisse report"""
        return self.env.ref('caisse_management.action_report_caisse_summary').report_action(self)

    def action_print_decaissements(self):
        """Print Decaissements report with date selection"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rapport Decaissements',
            'res_model': 'caisse.disbursement',
            'view_mode': 'list,form',
            'domain': [
                ('company_id', '=', self.company_id.id),
                ('state', '=', 'disbursed')
            ],
            'context': {
                'search_default_group_by_date': 1,
            },
            'target': 'current',
        }

    def action_open_configuration(self):
        """Open caisse configuration settings"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Caisse Configuration',
            'res_model': 'caisse.config',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    def action_view_audit_trail(self):
        """View audit trail - all caisse-related activities"""
        # Calculate first day of current month
        today = fields.Date.today()
        first_day_of_month = today.replace(day=1)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Piste d\'Audit Caisse',
            'res_model': 'caisse.request',
            'view_mode': 'list,form',
            'domain': [
                ('company_id', '=', self.company_id.id),
                ('state', 'in', ['disbursed', 'rejected']),
                ('request_date', '>=', first_day_of_month)
            ],
            'context': {
                'group_by': ['state', 'request_type_id'],
            },
            'target': 'current',
        }

    # Dashboard stat box actions - show ACTUAL data for each state
    def action_view_approved_requests(self):
        """View approved requests (manager_approved state)"""
        seven_days_ago = fields.Date.today() - timedelta(days=7)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Demandes Approuvées',
            'res_model': 'caisse.request',
            'view_mode': 'list,form',
            'domain': [
                ('company_id', '=', self.company_id.id),
                ('state', '=', 'manager_approved'),
                ('request_date', '>=', seven_days_ago)
            ],
            'context': {},
            'target': 'current',
        }

    def action_view_disbursed_requests(self):
        """View disbursed requests"""
        seven_days_ago = fields.Date.today() - timedelta(days=7)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Demandes Décaissées',
            'res_model': 'caisse.request',
            'view_mode': 'list,form',
            'domain': [
                ('company_id', '=', self.company_id.id),
                ('state', '=', 'disbursed'),
                ('disbursement_date', '>=', seven_days_ago)
            ],
            'context': {},
            'target': 'current',
        }

    def action_view_rejected_requests(self):
        """View rejected requests"""
        seven_days_ago = fields.Date.today() - timedelta(days=7)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Demandes Rejetées',
            'res_model': 'caisse.request',
            'view_mode': 'list,form',
            'domain': [
                ('company_id', '=', self.company_id.id),
                ('state', '=', 'rejected'),
                ('request_date', '>=', seven_days_ago)
            ],
            'context': {},
            'target': 'current',
        }