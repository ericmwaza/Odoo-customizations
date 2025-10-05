# -*- coding: utf-8 -*-

from odoo import models


class BankListingXlsx(models.AbstractModel):
    _name = 'report.payroll_listings.xlsx_bank_listing'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Bank Listing XLSX Report'

    def generate_xlsx_report(self, workbook, data, wizard):
        sheet = workbook.add_worksheet('Bank Listing')
        
        # Formats
        title_format = workbook.add_format({
            'bold': True, 
            'font_size': 16, 
            'underline': True,
            'align': 'center'
        })
        bank_header_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'bg_color': '#D3D3D3',
            'border': 1,
            'align': 'center'
        })
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#E0E0E0',
            'border': 1,
            'align': 'center'
        })
        cell_format = workbook.add_format({'border': 1})
        money_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        total_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FFE4B5',
            'border': 1,
            'num_format': '#,##0.00'
        })

        row_idx = 0
        
        # Add company logo if available
        try:
            company_obj = wizard.company_id
            if company_obj and company_obj.logo:
                import base64
                import io
                logo_data = base64.b64decode(company_obj.logo)
                logo_stream = io.BytesIO(logo_data)
                sheet.set_row(row_idx, 40)
                sheet.insert_image(row_idx, 0, 'logo.png', {
                    'image_data': logo_stream,
                    'x_scale': 0.03,
                    'y_scale': 0.03
                })
        except:
            pass
        
        row_idx += 1
        
        # Title with month/year - centered
        report_title = data.get('report_type_label', 'Bank Listing Report')
        period = data.get('period', {})
        month_year = period.get('month_year', '')
        if month_year:
            report_title = f"{report_title} - {month_year}"
        sheet.merge_range(row_idx, 0, row_idx, 3, report_title, title_format)
        row_idx += 2
        
        grand_total = 0
        data_by_bank = data.get('data_by_bank', {})
        
        for bank_name, bank_data in data_by_bank.items():
            # Bank name as simple header
            sheet.merge_range(row_idx, 0, row_idx, 3, bank_name.upper(), bank_header_format)
            row_idx += 1
            
            # Headers for this bank section
            headers = ['Nom et Prénom', 'Matricule', 'Numéro de Compte', 'Net à Payer']
            for i, header in enumerate(headers):
                sheet.write(row_idx, i, header, header_format)
            row_idx += 1
            
            bank_total = 0
            for record in bank_data.get('records', []):
                sheet.write(row_idx, 0, record.get('employee_name') or '', cell_format)
                sheet.write(row_idx, 1, record.get('employee_matricule') or '', cell_format)
                sheet.write(row_idx, 2, record.get('bank_account') or '', cell_format)
                net_wage = record.get('net_wage', 0.0)
                sheet.write(row_idx, 3, net_wage, money_format)
                bank_total += net_wage
                grand_total += net_wage
                row_idx += 1
            
            # Bank subtotal
            sheet.write(row_idx, 2, f'Total {bank_name}', header_format)
            sheet.write(row_idx, 3, bank_total, total_format)
            row_idx += 2

        # Grand Total
        sheet.write(row_idx, 2, 'Total Général', header_format)
        sheet.write(row_idx, 3, grand_total, total_format)
        
        # Auto-adjust column widths
        sheet.set_column(0, 0, 15)  # Banque
        sheet.set_column(1, 1, 20)  # Numéro de Compte
        sheet.set_column(2, 2, 25)  # Nom de l'Employé
        sheet.set_column(3, 3, 15)  # Net à Payer