# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CaisseReportWizard(models.TransientModel):
    _name = 'caisse.report.wizard'
    _description = 'Caisse Report Wizard'

    report_type = fields.Selection([
        ('summary', 'Resume Caisse'),
        ('disbursements', 'Rapport Decaissements'),
        ('outstanding_advances', 'Avances en Cours'),
        ('reconciliation', 'Reconciliation'),
    ], string='Type de Rapport', required=True, default='summary')

    date_from = fields.Date(
        string='Date de Debut',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1)
    )

    date_to = fields.Date(
        string='Date de Fin',
        required=True,
        default=fields.Date.today
    )

    company_id = fields.Many2one(
        'res.company',
        string='Societe',
        required=True,
        default=lambda self: self.env.company
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from > wizard.date_to:
                raise UserError(_('La date de debut doit etre anterieure a la date de fin.'))

    def action_print_report(self):
        self.ensure_one()

        if self.report_type == 'summary':
            # Get caisse config
            config = self.env['caisse.config'].search([
                ('company_id', '=', self.company_id.id),
                ('active', '=', True)
            ], limit=1)

            if not config:
                raise UserError(_('Aucune configuration de caisse trouvee pour cette societe.'))

            return self.env.ref('caisse_management.action_report_caisse_summary').report_action(config)

        elif self.report_type == 'disbursements':
            # Get disbursements in date range
            disbursements = self.env['caisse.disbursement'].search([
                ('company_id', '=', self.company_id.id),
                ('disbursement_date', '>=', self.date_from),
                ('disbursement_date', '<=', self.date_to),
                ('state', '=', 'disbursed')
            ])

            if not disbursements:
                raise UserError(_('Aucun decaissement trouve pour cette periode.'))

            return self.env.ref('caisse_management.action_report_disbursements').report_action(disbursements)

        elif self.report_type == 'outstanding_advances':
            # Get outstanding advances
            requests = self.env['caisse.request'].search([
                ('company_id', '=', self.company_id.id),
                ('state', '=', 'disbursed'),
                ('request_type', '=', 'advance')
            ])

            if not requests:
                raise UserError(_('Aucune avance en cours trouvee.'))

            return self.env.ref('caisse_management.action_report_outstanding_advances').report_action(requests)

        elif self.report_type == 'reconciliation':
            # Get reconciliations in date range
            reconciliations = self.env['caisse.reconciliation'].search([
                ('company_id', '=', self.company_id.id),
                ('reconciliation_date', '>=', self.date_from),
                ('reconciliation_date', '<=', self.date_to)
            ])

            if not reconciliations:
                raise UserError(_('Aucune reconciliation trouvee pour cette periode.'))

            return self.env.ref('caisse_management.action_report_reconciliation').report_action(reconciliations)
