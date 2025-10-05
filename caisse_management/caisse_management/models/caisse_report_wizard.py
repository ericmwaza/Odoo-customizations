# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CaisseReportWizard(models.TransientModel):
    _name = 'caisse.report.wizard'
    _description = 'Wizard de Rapport Caisse'

    report_type = fields.Selection([
        ('resume', 'Resume Caisse'),
    ], string='Type de Rapport', required=True, default='resume')

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

        # Get caisse config
        config = self.env['caisse.config'].search([
            ('company_id', '=', self.company_id.id),
            ('active', '=', True)
        ], limit=1)

        if not config:
            raise UserError(_('Aucune configuration de caisse trouvee pour cette societe.'))

        # Pass date range in context as strings to avoid serialization issues
        return self.env.ref('caisse_management.action_report_caisse_summary').with_context(
            date_from=str(self.date_from),
            date_to=str(self.date_to)
        ).report_action(config)
