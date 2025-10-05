from odoo import models


class EmployeeStructureXlsx(models.AbstractModel):
    _name = 'report.payroll_listings.xlsx_employee_structure'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Employee Structure XLSX Report'

    def generate_xlsx_report(self, workbook, data, wizard):
        data_by_bank = data.get('data_by_bank', {})
        rules = data.get('rules', [])
        
        # Always create first sheet with ALL banks
        sheet = workbook.add_worksheet(data.get('report_type_label', 'Rapport'))
        self._populate_sheet(sheet, workbook, data, wizard, data_by_bank, rules, is_summary_sheet=True)
        
        # If multiple banks, create additional per-bank sheets
        if len(data_by_bank) > 1:
            for bank_name, bank_data in data_by_bank.items():
                self._create_bank_sheet(workbook, data, wizard, bank_name, bank_data, rules)

    def _create_bank_sheet(self, workbook, data, wizard, bank_name, bank_data, rules):
        # Clean bank name for sheet title (Excel has sheet name restrictions)
        clean_bank_name = bank_name.replace('/', '-').replace('\\', '-').replace('*', '').replace('?', '').replace('[', '').replace(']', '')[:31]
        sheet = workbook.add_worksheet(clean_bank_name)
        
        # Create single-bank data structure for this sheet
        single_bank_data = {bank_name: bank_data}
        modified_data = dict(data)
        modified_data['data_by_bank'] = single_bank_data
        
        self._populate_sheet(sheet, workbook, modified_data, wizard, single_bank_data, rules, is_summary_sheet=False, bank_name=bank_name)

    def _populate_sheet(self, sheet, workbook, data, wizard, data_by_bank, rules, is_summary_sheet=True, bank_name=None):
        
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

        headers = ['Nom et Prénom', 'Matricule', 'Numéro de compte'] + [r['name'] for r in rules]
        
        row_idx = 0
        
        # Add company logo if available
        try:
            company_obj = wizard.company_id
            if company_obj and company_obj.logo:
                import base64
                import io
                logo_data = base64.b64decode(company_obj.logo)
                logo_stream = io.BytesIO(logo_data)
                sheet.set_row(row_idx, 60)
                sheet.insert_image(row_idx, 0, 'logo.png', {
                    'image_data': logo_stream,
                    'x_scale': 0.3,
                    'y_scale': 0.3
                })
        except:
            pass
        
        row_idx += 2
        
        # Title with month/year in French - centered
        report_title = data.get('report_type_label', 'Employee Structure Report')
        period = data.get('period', {})
        month_year = period.get('month_year', '')
        if month_year:
            # Convert to French month names
            import datetime
            if wizard.date_from:
                date_obj = wizard.date_from
                french_months = {
                    1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril',
                    5: 'Mai', 6: 'Juin', 7: 'Juillet', 8: 'Août',
                    9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
                }
                french_month_year = f"{french_months[date_obj.month]} {date_obj.year}"
                report_title = f"{report_title} - {french_month_year}"
            elif wizard.payslip_run_id and wizard.payslip_run_id.date_start:
                date_obj = wizard.payslip_run_id.date_start
                french_months = {
                    1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril',
                    5: 'Mai', 6: 'Juin', 7: 'Juillet', 8: 'Août',
                    9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
                }
                french_month_year = f"{french_months[date_obj.month]} {date_obj.year}"
                report_title = f"{report_title} - {french_month_year}"
        
        # Different headers for credit/retenue/credit_interne, contribution reports, and salary listing reports
        is_contribution_report = any(contrib in report_title.upper() for contrib in ['LISTING INSS', 'LISTING IPR', 'LISTING IRE', 'LISTING MUTUELLE', 'LISTING ONPR', 'LISTING SPECIAL CONTRIBUTION'])
        is_salary_listing = 'LISTE DE PAIE' in report_title
        if 'CRÉDITS' in report_title or 'RETENUES' in report_title:
            headers = ['Nom et Prénom', 'Matricule'] + [r['name'] for r in rules]
        elif is_contribution_report or is_salary_listing:
            headers = ['Nom et Prénom', 'Matricule'] + [r['name'] for r in rules]
        else:
            headers = ['Nom et Prénom', 'Matricule', 'Numéro de compte'] + [r['name'] for r in rules]
        sheet.merge_range(row_idx, 0, row_idx, len(headers) - 1, report_title, title_format)
        row_idx += 1
        
        # Add bank name and underline for per-bank sheets
        if not is_summary_sheet and bank_name:
            bank_title_format = workbook.add_format({
                'bold': True,
                'font_size': 14,
                'underline': True,
                'align': 'center'
            })
            sheet.merge_range(row_idx, 0, row_idx, len(headers) - 1, bank_name.upper(), bank_title_format)
            row_idx += 1
        
        row_idx += 1
        
        grand_totals = {rule['code']: 0.0 for rule in rules}

        # Check if this is a credit/retenue report with nested structure
        is_credit_retenue = 'CRÉDITS' in report_title or 'RETENUES' in report_title
        
        # Create flattened data structure for template compatibility
        flattened_data = {}
        if is_credit_retenue:
            # Credit/Retenue: Flatten Bank -> Retenue Type -> Records to "Bank - RetenueName" -> Records
            for bank_name, bank_info in data_by_bank.items():
                for retenue_name, retenue_data in bank_info.get('retenues', {}).items():
                    section_name = f"{bank_name} - {retenue_name}"
                    flattened_data[section_name] = retenue_data
        else:
            flattened_data = data_by_bank

        for current_bank_name, bank_data in flattened_data.items():
            # Bank name as simple header (show if multiple sections on summary sheet, or always for contribution reports, but not for salary listing)
            if ((is_summary_sheet and len(flattened_data) > 1) or is_contribution_report) and not is_salary_listing and current_bank_name.strip():
                sheet.merge_range(row_idx, 0, row_idx, len(headers) - 1, current_bank_name.upper(), bank_header_format)
                row_idx += 1
            
            # Headers for this bank section
            for i, header in enumerate(headers):
                sheet.write(row_idx, i, header, header_format)
            row_idx += 1
            
            bank_totals = {rule['code']: 0.0 for rule in rules}
            for record in bank_data.get('records', []):
                col_idx = 0
                sheet.write(row_idx, col_idx, record.get('employee_name') or '', cell_format); col_idx += 1
                sheet.write(row_idx, col_idx, record.get('employee_matricule') or '', cell_format); col_idx += 1
                
                # Only show N° COMPTE column for non-credit/retenue, non-contribution, and non-salary listing reports
                if not ('CRÉDITS' in report_title or 'RETENUES' in report_title) and not is_contribution_report and not is_salary_listing:
                    sheet.write(row_idx, col_idx, record.get('bank_account') or '', cell_format)
                    col_idx += 1
                
                for rule in rules:
                    # Handle different data sources for credit/retenue vs regular reports
                    if 'CRÉDITS' in report_title or 'RETENUES' in report_title:
                        if rule['code'] == 'DATE_DEBUT':
                            value = record.get('date_debut', '')
                            sheet.write(row_idx, col_idx, value, cell_format)
                        elif rule['code'] == 'DATE_FIN':
                            value = record.get('date_fin', '')
                            sheet.write(row_idx, col_idx, value, cell_format)
                        elif rule['code'] == 'MENSUALITE':
                            value = record.get('mensualite', 0.0)
                            sheet.write(row_idx, col_idx, value, money_format)
                            grand_totals[rule['code']] += value
                            bank_totals[rule['code']] += value
                        elif rule['code'] == 'REFERENCE':
                            value = record.get('reference', '')
                            sheet.write(row_idx, col_idx, value, cell_format)
                        else:
                            sheet.write(row_idx, col_idx, 0, money_format)
                    else:
                        # Regular report logic
                        amount = record.get('amounts', {}).get(rule['code'], 0.0)
                        sheet.write(row_idx, col_idx, amount, money_format)
                        grand_totals[rule['code']] += amount
                        bank_totals[rule['code']] += amount
                    
                    col_idx += 1
                row_idx += 1
            
            # Bank subtotals (only show if multiple sections on summary sheet)
            if is_summary_sheet and len(flattened_data) > 1:
                sheet.write(row_idx, 0, '', cell_format)
                sheet.write(row_idx, 1, '', cell_format)
                
                # Handle different column structures
                col_idx = 2
                if not ('CRÉDITS' in report_title or 'RETENUES' in report_title) and not is_contribution_report and not is_salary_listing:
                    # Regular reports: show employee count in N° COMPTE column
                    employee_count = len(bank_data.get('records', []))
                    sheet.write(row_idx, col_idx, f'{employee_count} Employés', header_format)
                    col_idx += 1
                elif is_salary_listing:
                    # Salary listing reports: no N° COMPTE column, show employee count in first rule column
                    pass  # Will be handled in the rule loop
                
                for rule_idx, rule in enumerate(rules):
                    if 'CRÉDITS' in report_title or 'RETENUES' in report_title:
                        if rule['code'] == 'MENSUALITE':
                            sheet.write(row_idx, col_idx, bank_totals[rule['code']], total_format)
                        elif rule['code'] == 'DATE_DEBUT':
                            # Show employee count in first date column
                            employee_count = len(bank_data.get('records', []))
                            sheet.write(row_idx, col_idx, f'{employee_count} Employés', header_format)
                        else:
                            # Empty for other credit/retenue columns
                            sheet.write(row_idx, col_idx, '', cell_format)
                    elif is_salary_listing:
                        # Salary listing reports: employee count in first rule column, totals in others
                        if rule_idx == 0:
                            employee_count = len(bank_data.get('records', []))
                            sheet.write(row_idx, col_idx, f'{employee_count} Employés', header_format)
                        else:
                            sheet.write(row_idx, col_idx, bank_totals[rule['code']], total_format)
                    else:
                        # Regular reports: show all totals
                        sheet.write(row_idx, col_idx, bank_totals[rule['code']], total_format)
                    col_idx += 1
                row_idx += 2
        
        # Grand Total (only show if multiple sections or rules exist)
        if len(flattened_data) > 1 or len(rules) > 0:
            sheet.write(row_idx, 0, '', cell_format)
            sheet.write(row_idx, 1, '', cell_format)
            
            col_idx = 2
            if not ('CRÉDITS' in report_title or 'RETENUES' in report_title) and not is_contribution_report and not is_salary_listing:
                # Regular reports: show total employee count in N° COMPTE column
                total_employees = sum(len(bd.get('records', [])) for bd in flattened_data.values())
                sheet.write(row_idx, col_idx, f'{total_employees} Employés', header_format)
                col_idx += 1
            
            for rule_idx, rule in enumerate(rules):
                if 'CRÉDITS' in report_title or 'RETENUES' in report_title:
                    if rule['code'] == 'MENSUALITE':
                        sheet.write(row_idx, col_idx, grand_totals[rule['code']], total_format)
                    elif rule['code'] == 'DATE_DEBUT':
                        # Show total employee count in first date column
                        total_employees = sum(len(bd.get('records', [])) for bd in flattened_data.values())
                        sheet.write(row_idx, col_idx, f'{total_employees} Employés', header_format)
                    else:
                        # Empty for other credit/retenue columns
                        sheet.write(row_idx, col_idx, '', cell_format)
                elif is_salary_listing:
                    # Salary listing reports: employee count in first rule column, totals in others
                    if rule_idx == 0:
                        total_employees = sum(len(bd.get('records', [])) for bd in flattened_data.values())
                        sheet.write(row_idx, col_idx, f'{total_employees} Employés', header_format)
                    else:
                        sheet.write(row_idx, col_idx, grand_totals[rule['code']], total_format)
                else:
                    # Regular reports: show all totals
                    sheet.write(row_idx, col_idx, grand_totals[rule['code']], total_format)
                col_idx += 1
        
        # Auto-adjust column widths
        sheet.set_column(0, 0, 25)  # Nom de l'Employé
        sheet.set_column(1, 1, 12)  # Matricule
        sheet.set_column(2, 2, 20)  # Numéro de compte
        for i, rule in enumerate(rules):
            sheet.set_column(3 + i, 3 + i, 15)  # Rule columns
