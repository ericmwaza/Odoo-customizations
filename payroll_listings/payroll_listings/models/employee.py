from odoo import fields, models

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    x_employee_no = fields.Char(
        string="Matricule",
        groups="hr.group_hr_user",
        help="Employee identification number."
    )
    x_employee_status = fields.Selection(
        [('active', 'Actif'), ('inactive', 'Inactif')],
        string="Employee Status",
        default='active',
        groups="hr.group_hr_user",
        help="Employee's current status."
    )