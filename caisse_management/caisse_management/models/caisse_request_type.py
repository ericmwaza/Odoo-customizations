# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CaisseRequestType(models.Model):
    _name = 'caisse.request.type'
    _description = 'Type de Demande de Caisse'
    _order = 'sequence, name'

    name = fields.Char(
        string='Nom',
        required=True,
        translate=True
    )

    code = fields.Char(
        string='Code',
        required=True,
        help="Code technique unique pour ce type"
    )

    sequence = fields.Integer(
        string='Séquence',
        default=10,
        help="Ordre d'affichage"
    )

    active = fields.Boolean(
        string='Actif',
        default=True
    )

    description = fields.Text(
        string='Description',
        translate=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        default=lambda self: self.env.company
    )

    @api.constrains('code')
    def _check_code_unique(self):
        for record in self:
            existing = self.search([
                ('code', '=', record.code),
                ('id', '!=', record.id),
                ('company_id', '=', record.company_id.id)
            ])
            if existing:
                raise ValidationError(_("Le code doit être unique par société"))

    @api.model
    def _create_default_types(self):
        """Create default request types if they don't exist"""
        default_types = [
            {
                'name': 'Avance sur Salaire',
                'code': 'advance',
                'sequence': 10,
            },
            {
                'name': 'Petite Caisse',
                'code': 'petty_cash',
                'sequence': 20,
            },
            {
                'name': 'Autre Dépense',
                'code': 'expense',
                'sequence': 30,
            },
            {
                'name': 'Fonds d\'Urgence',
                'code': 'emergency',
                'sequence': 40,
            },
        ]

        for type_vals in default_types:
            existing = self.search([
                ('code', '=', type_vals['code']),
                ('company_id', '=', self.env.company.id)
            ])
            if not existing:
                self.create(type_vals)
