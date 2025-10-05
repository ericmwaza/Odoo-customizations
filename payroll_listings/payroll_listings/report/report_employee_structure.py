# -*- coding: utf-8 -*-

from odoo import api, models


class ReportEmployeeStructure(models.AbstractModel):
    _name = 'report.payroll_listings.report_employee_structure_pdf_document'
    _description = 'Employee Structure PDF Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['payroll.listing.wizard'].browse(docids[0]) if docids else None
        if not wizard:
            return {}
        
        # Always generate fresh dataset from wizard
        dataset = wizard._gather_dataset()
        
        # Return with docs containing the wizard object for template access
        return {
            'doc_ids': docids,
            'doc_model': 'payroll.listing.wizard',
            'docs': wizard,
            'data_by_bank': dataset.get('data_by_bank'),
            'rules': dataset.get('rules'),
            'report_type_label': dataset.get('report_type_label'),
            'period': dataset.get('period'),
            'company': wizard.company_id,
        }