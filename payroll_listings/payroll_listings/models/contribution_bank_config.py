# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ContributionBankConfig(models.Model):
    _name = 'contribution.bank.config'
    _description = 'Contribution Bank Configuration'
    _rec_name = 'display_name'

    contribution_type = fields.Selection([
        ('ipr', 'IPR'),
        ('inss', 'INSS'),
        ('mutuelle', 'MUTUELLE'),
        ('onpr', 'ONPR'),
        ('special_contribution', 'SPECIAL CONTRIBUTION'),
        ('credit_interne', 'CRÉDIT INTERNE')
    ], string='Contribution Type', required=True, index=True)
    
    bank_id = fields.Many2one(
        'res.bank', 
        string='Bank',
        required=True
    )
    
    bank_account = fields.Char(
        string='Bank Account',
        required=True
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    display_name = fields.Char(
        string='Name',
        compute='_compute_display_name',
        store=True
    )

    @api.depends('contribution_type', 'bank_id', 'bank_account')
    def _compute_display_name(self):
        for record in self:
            if record.contribution_type and record.bank_id and record.bank_account:
                record.display_name = f"{record.contribution_type.upper()} - {record.bank_id.name} ({record.bank_account})"
            else:
                record.display_name = "Configuration incomplète"

    @api.model
    def get_bank_for_contribution(self, contribution_type):
        """Get the configured bank and account for a specific contribution type"""
        config = self.search([
            ('contribution_type', '=', contribution_type),
            ('active', '=', True)
        ], limit=1)
        
        if config:
            return f"{config.bank_id.name} - {config.bank_account}"
        return 'Sans Banque Configurée'

    _sql_constraints = [
        ('unique_config', 'unique(contribution_type)', 
         'Only one bank configuration per contribution type is allowed!')
    ]