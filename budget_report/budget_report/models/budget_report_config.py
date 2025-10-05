# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    budget_encaissement_plan_ids = fields.Many2many(
        'account.analytic.plan',
        'budget_config_encaissement_plan_rel',
        'config_id',
        'plan_id',
        string='Plans Analytiques Encaissement',
        related='company_id.budget_encaissement_plan_ids',
        readonly=False,
        help="Plans analytiques représentant les encaissements (recettes)"
    )

    budget_execution_plan_ids = fields.Many2many(
        'account.analytic.plan',
        'budget_config_execution_plan_rel',
        'config_id',
        'plan_id',
        string='Plans Analytiques Exécution',
        related='company_id.budget_execution_plan_ids',
        readonly=False,
        help="Plans analytiques représentant les exécutions (dépenses)"
    )


class ResCompany(models.Model):
    _inherit = 'res.company'

    budget_encaissement_plan_ids = fields.Many2many(
        'account.analytic.plan',
        'company_budget_encaissement_plan_rel',
        'company_id',
        'plan_id',
        string='Plans Analytiques Encaissement'
    )

    budget_execution_plan_ids = fields.Many2many(
        'account.analytic.plan',
        'company_budget_execution_plan_rel',
        'company_id',
        'plan_id',
        string='Plans Analytiques Exécution'
    )
