# -*- coding: utf-8 -*-

from odoo import api, models


class ReportBankListing(models.AbstractModel):
    _name = 'report.payroll_listings.report_bank_listing'
    _description = 'Bank Listing PDF Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['payroll.listing.wizard'].browse(docids[0]) if docids else None
        if not wizard:
            return {}
        
        # Always generate fresh data
        dataset = wizard._gather_dataset()
        
        # Ensure company is available for template
        if 'company' not in dataset or not dataset['company']:
            dataset['company'] = wizard.company_id
        
        return dataset
