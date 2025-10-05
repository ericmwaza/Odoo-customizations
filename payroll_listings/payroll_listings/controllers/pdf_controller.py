# -*- coding: utf-8 -*-

import base64
import io
from reportlab.lib.pagesizes import A3, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from odoo import http
from odoo.http import request


class PayrollPDFController(http.Controller):
    
    @http.route('/payroll/pdf/generate', type='http', auth='user', methods=['GET', 'POST'])
    def generate_pdf_report(self, **kwargs):
        """Generate custom PDF report using ReportLab with ORIGINAL table structure"""
        
        # Get wizard data
        wizard_id = kwargs.get('wizard_id')
        if not wizard_id:
            return request.not_found()
            
        wizard = request.env['payroll.listing.wizard'].browse(int(wizard_id))
        if not wizard.exists():
            return request.not_found()
            
        # Generate dataset using existing logic
        dataset = wizard._gather_dataset()
        
        # Create PDF with error handling
        try:
            pdf_buffer = io.BytesIO()
            self._create_pdf(pdf_buffer, dataset, wizard)
            pdf_buffer.seek(0)
            
            # Return PDF response
            filename = f"{dataset.get('report_type_label', 'Payroll Report')}.pdf"
            response = request.make_response(
                pdf_buffer.getvalue(),
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="{filename}"')
                ]
            )
            pdf_buffer.close()
            return response
        except Exception as e:
            # Return error details for debugging
            error_msg = f"PDF Generation Error: {str(e)}"
            return request.make_response(
                error_msg,
                headers=[('Content-Type', 'text/plain')],
                status=500
            )
        
    def _create_pdf(self, buffer, dataset, wizard):
        """Create PDF using ReportLab with TRUE landscape and ORIGINAL table structure"""
        
        # Setup TRUE landscape A3 document with balanced margins
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A3),  # 420mm x 297mm - TRUE landscape
            leftMargin=15*mm,   # Balanced left margin
            rightMargin=15*mm,  # Balanced right margin  
            topMargin=15*mm,    # Top space
            bottomMargin=15*mm  # Bottom space
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # Title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=15,
            alignment=TA_CENTER,
            textColor=colors.black,
            fontName='Helvetica-Bold'
        )
        
        bank_header_style = ParagraphStyle(
            'BankHeader',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=10,
            spaceBefore=15,
            alignment=TA_CENTER,
            textColor=colors.black,
            fontName='Helvetica-Bold',
            backColor=colors.lightgrey
        )
        
        # Add logo in top-left corner if available
        if wizard.company_id and wizard.company_id.logo:
            try:
                logo_data = base64.b64decode(wizard.company_id.logo)
                logo_buffer = io.BytesIO(logo_data)
                logo_img = Image(logo_buffer)
                logo_img.drawHeight = 30*mm  # Slightly larger
                logo_img.drawWidth = 60*mm   # Slightly larger
                logo_img.hAlign = 'LEFT'     # Left alignment
                
                story.append(logo_img)
                story.append(Spacer(1, 10*mm))  # More space after logo
            except Exception:
                pass
        
        # Title with French date and custom titles for salary listings
        original_report_title = dataset.get('report_type_label', 'PAYROLL REPORT')
        period = dataset.get('period', {})
        month_year = period.get('month_year', '')
        
        # Custom titles for specific salary listing reports
        if 'LISTE DE PAIE' in original_report_title:
            if 'SOUS STATUT' in original_report_title:
                report_title = 'SALAIRE DU PERSONNEL SOUS STATUT'
            elif 'CADRES SUPÉRIEURS' in original_report_title:
                report_title = 'SALAIRE DU PERSONNEL CADRES SUPÉRIEURS'
            elif 'DÉPUTÉ' in original_report_title:
                report_title = 'INDEMNITÉS DES DÉPUTÉS'
            elif 'MB' in original_report_title:
                report_title = 'INDEMNITÉS DES MEMBRES DU BUREAU'
            else:
                report_title = original_report_title
        else:
            report_title = original_report_title
        
        if month_year:
            title_text = f"{report_title} - {month_year}"
        else:
            title_text = report_title
            
        # Create underlined title using HTML-like markup
        underlined_title = f"<u>{title_text.upper()}</u>"
        story.append(Paragraph(underlined_title, title_style))
        story.append(Spacer(1, 5*mm))
        
        # Get data - USING ORIGINAL STRUCTURE
        data_by_bank = dataset.get('data_by_bank', {})
        rules = dataset.get('rules', [])
        report_type_label = dataset.get('report_type_label', '')
        
        # ORIGINAL logic for determining report types
        is_contribution_report = any(contrib in report_type_label.upper() for contrib in [
            'LISTING INSS', 'LISTING IPR', 'LISTING IRE', 'LISTING MUTUELLE', 
            'LISTING ONPR', 'LISTING SPECIAL CONTRIBUTION'
        ])
        is_salary_listing = 'LISTE DE PAIE' in report_type_label
        is_credit_retenue = 'CRÉDITS' in report_type_label or 'RETENUES' in report_type_label
        
        # SMART header abbreviation based on column count
        def make_header_readable(header, col_count):
            """Make headers readable with aggressive abbreviations for many columns"""
            
            # Progressive abbreviation based on column density
            if col_count <= 8:
                # Few columns: minimal abbreviation
                abbrev = header
                abbrev = abbrev.replace('INDEMNITÉ', 'IND.')
                abbrev = abbrev.replace('ALLOCATION', 'ALLOC.')
                abbrev = abbrev.replace('CONTRIBUTION', 'CONTRIB.')
                return abbrev if len(abbrev) <= 15 else abbrev[:15] + '.'
                
            elif col_count <= 12:
                # Medium columns: moderate abbreviation
                abbrev = header
                abbrev = abbrev.replace('INDEMNITÉ', 'IND')
                abbrev = abbrev.replace('ALLOCATION', 'ALL')
                abbrev = abbrev.replace('CONTRIBUTION', 'CTB')
                abbrev = abbrev.replace('COTISATION', 'COT')
                abbrev = abbrev.replace('COMPLÉMENTAIRE', 'CP')
                abbrev = abbrev.replace('FONCTION', 'FCT')
                abbrev = abbrev.replace('REPRÉSENTATION', 'REP')
                abbrev = abbrev.replace('LOGEMENT', 'LOG')
                abbrev = abbrev.replace('TRANSPORT', 'TRP')
                abbrev = abbrev.replace('FAMILIALE', 'FAM')
                return abbrev if len(abbrev) <= 12 else abbrev[:12]
                
            else:
                # Many columns: aggressive abbreviation  
                abbrev = header
                abbrev = abbrev.replace('INDEMNITÉ', 'I')
                abbrev = abbrev.replace('ALLOCATION', 'A')
                abbrev = abbrev.replace('CONTRIBUTION', 'C')
                abbrev = abbrev.replace('COTISATION', 'C')
                abbrev = abbrev.replace('COMPLÉMENTAIRE', 'CP')
                abbrev = abbrev.replace('FONCTION', 'F')
                abbrev = abbrev.replace('REPRÉSENTATION', 'R')
                abbrev = abbrev.replace('LOGEMENT', 'L')
                abbrev = abbrev.replace('TRANSPORT', 'T')
                abbrev = abbrev.replace('FAMILIALE', 'F')
                abbrev = abbrev.replace('SALAIRE', 'S')
                abbrev = abbrev.replace('MONTANT', 'M')
                # Ultra-short: just first 8 characters
                return abbrev[:8] if len(abbrev) > 8 else abbrev
        
        # Calculate column count FIRST for all subsequent logic
        base_cols = 3 if not (is_credit_retenue or is_contribution_report or is_salary_listing) else 2
        col_count = base_cols + len(rules)
        
        # Apply readable headers with column count context
        def get_salary_listing_column_name(rule_code, rule_name):
            """Get specific column names for LISTE DE PAIE POUR SOUS STATUS"""
            mapping = {
                'BASIC': 'Base',
                'IDFF': 'I.Fonc', 
                'PDR': 'I.CHG',
                'PM': 'PRIME',
                'IDCA': 'I.CAISSE',
                'HOU': 'I.LOG',
                'AF': 'AF/EF',
                'PDRR': 'Prim.Re.',
                'BRUT': 'Brut',
                'INE': 'InssPers',
                'MFP': 'MfpPers',
                'IPR': 'IPR',
                'RT': 'Retenues',
                'NET': 'Net a payer'
            }
            return mapping.get(rule_code, make_header_readable(rule_name, col_count))
        
        # Apply specific mappings for salary listing or general abbreviations
        if is_salary_listing and 'SOUS STATUT' in report_type_label:
            # Update SOUS STATUT mappings with correct rule codes and add TOTE
            def get_sous_statut_column_name(rule_code, rule_name):
                mapping = {
                    'BASIC': 'Base',
                    'IDFF': 'I.Fonc', 
                    'PDR': 'I.CHG S',
                    'PM': 'PRIME',
                    'IDCA': 'I.CAISSE',
                    'HOU': 'I.LOG',
                    'AF': 'AF',
                    'PDRR': 'Prim.Re',
                    'Brut': 'Brut',
                    'INE': 'InssPers',
                    'MFP': 'MfpPers',
                    'IPR': 'IPR',
                    'TOTE': 'Retenues',
                    'NET': 'Net a payer'
                }
                return mapping.get(rule_code, make_header_readable(rule_name, col_count))
            
            # Create rules in the correct order for SOUS STATUT
            sous_statut_rule_order = ['BASIC', 'IDFF', 'PDR', 'PM', 'IDCA', 'HOU', 'AF', 'PDRR', 'Brut', 'INE', 'MFP', 'IPR', 'TOTE', 'NET']
            filtered_rules = []
            for code in sous_statut_rule_order:
                rule = next((r for r in rules if r['code'] == code), None)
                if rule:
                    filtered_rules.append(rule)
                else:
                    # Create rule manually if it doesn't exist
                    filtered_rules.append({'code': code, 'name': code})
            
            rules = filtered_rules
            col_count = base_cols + len(rules)
            readable_rules = [{'name': get_sous_statut_column_name(r['code'], r['name']), 'code': r['code']} for r in rules]
        elif is_salary_listing and 'CADRES SUPÉRIEURS' in report_type_label:
            # Specific mappings for CADRE SUPERIEUR with correct order
            def get_cadre_superieur_column_name(rule_code, rule_name):
                mapping = {
                    'BASIC': 'Base',
                    'PDR': 'I.CHG SPEC',
                    'PM': 'PRIME',
                    'IDCA': 'I.CAISSE',
                    'HOU': 'I.LOG',
                    'FDR': 'I.REPR',
                    'INE': 'InssPers',
                    'FDEE': 'F/EQUIP',
                    'Brut': 'Brut',
                    'MFP': 'MfpPers',
                    'IPR': 'IPR',
                    'TOTE': 'Retenues',
                    'NET': 'Net a payer'
                }
                return mapping.get(rule_code, make_header_readable(rule_name, col_count))
            
            # Create rules in the exact order specified
            cadre_rule_order = ['BASIC', 'PDR', 'PM', 'IDCA', 'HOU', 'FDR', 'INE', 'FDEE', 'Brut', 'MFP', 'IPR', 'TOTE', 'NET']
            filtered_rules = []
            for code in cadre_rule_order:
                rule = next((r for r in rules if r['code'] == code), None)
                if rule:
                    filtered_rules.append(rule)
                else:
                    # Create rule manually if it doesn't exist (like we did for CREDIT_R)
                    filtered_rules.append({'code': code, 'name': code})
            
            rules = filtered_rules
            col_count = base_cols + len(rules)
            readable_rules = [{'name': get_cadre_superieur_column_name(r['code'], r['name']), 'code': r['code']} for r in rules]
        elif is_salary_listing and ('DÉPUTÉ' in report_type_label or 'MB' in report_type_label):
            # Create combined rules for DEPUTE and MB
            def get_depute_mb_column_name(rule_code, rule_name):
                mapping = {
                    'BASIC': 'INDEMN',
                    'FDR': 'Frais.Repr',
                    'HOU': 'Ind.Log',
                    'FDC': 'Frais.com',
                    'FDD': 'Frais.Depl',
                    'IDS': 'Ind.Suj',
                    'BRUT': 'Brut',
                    'MFP+INE': 'MFP+INSS',  # Special combined column
                    'IPR': 'IPR',
                    'CREDIT_R': 'Autr.C+AFEP',  # Shortened to fit better
                    'NET': 'Net a payer'
                }
                return mapping.get(rule_code, make_header_readable(rule_name, col_count))
            
            # Create custom rules list with MFP+INE as a combined rule
            filtered_rules = []
            available_rule_codes = [r['code'] for r in rules]
            
            # Add rules in the correct order for DÉPUTÉ/MB
            rule_order = ['BASIC', 'FDR', 'HOU', 'FDC', 'FDD', 'IDS', 'BRUT']
            
            # Add individual rules first
            for code in rule_order:
                rule = next((r for r in rules if r['code'] == code), None)
                if rule:
                    filtered_rules.append(rule)
            
            # Add combined MFP+INE rule between IDS and IPR (if both MFP and INE exist)
            if 'MFP' in available_rule_codes and 'INE' in available_rule_codes:
                filtered_rules.append({'code': 'MFP+INE', 'name': 'MFP+INE Combined'})
            
            # Add IPR
            ipr_rule = next((r for r in rules if r['code'] == 'IPR'), None)
            if ipr_rule:
                filtered_rules.append(ipr_rule)
            
            # Force add CREDIT_R (even if appears_on_payslip is False)
            credit_r_rule = next((r for r in rules if r['code'] == 'CREDIT_R'), None)
            if credit_r_rule:
                filtered_rules.append(credit_r_rule)
            else:
                # Create CREDIT_R rule manually if it doesn't exist in the filtered rules
                # Look in the original full rules list from the wizard
                filtered_rules.append({'code': 'CREDIT_R', 'name': 'CREDIT_R'})
            
            # Add NET
            net_rule = next((r for r in rules if r['code'] == 'NET'), None)
            if net_rule:
                filtered_rules.append(net_rule)
            
            rules = filtered_rules
            col_count = base_cols + len(rules)
            readable_rules = [{'name': get_depute_mb_column_name(r['code'], r['name']), 'code': r['code']} for r in rules]
        # INSS Reports mappings
        elif is_contribution_report and 'LISTING INSS' in report_type_label and 'CADRES SUPÉRIEURS' in report_type_label:
            # INSS CADRES SUPÉRIEURS mappings
            def get_inss_cadres_column_name(rule_code, rule_name):
                mapping = {
                    'BASIC': 'Base',
                    'HOU': 'Logement',
                    'PDR': 'Ind.Charg Spe',
                    'FDR': 'Repr',
                    'FDEE': 'Frais Equip',
                    'BasePension': 'BasePension',
                    'BaseRisque': 'BaseRisque',
                    'INE': 'InssPers',
                    'INONP': 'InssPatr',
                    'RS': 'InssPatrRisp',
                    'TL': 'Total Inss'
                }
                return mapping.get(rule_code, make_header_readable(rule_name, col_count))
            
            # Create rules in order with default values for BasePension and BaseRisque
            inss_cadres_rule_order = ['BASIC', 'HOU', 'PDR', 'FDR', 'FDEE', 'BasePension', 'BaseRisque', 'INE', 'INONP', 'RS', 'TL']
            filtered_rules = []
            for code in inss_cadres_rule_order:
                rule = next((r for r in rules if r['code'] == code), None)
                if rule:
                    filtered_rules.append(rule)
                else:
                    # Create rule manually with default values
                    if code == 'BasePension':
                        filtered_rules.append({'code': code, 'name': code, 'default_value': 450000})
                    elif code == 'BaseRisque':
                        filtered_rules.append({'code': code, 'name': code, 'default_value': 80000})
                    else:
                        filtered_rules.append({'code': code, 'name': code})
            
            rules = filtered_rules
            col_count = base_cols + len(rules)
            readable_rules = [{'name': get_inss_cadres_column_name(r['code'], r['name']), 'code': r['code']} for r in rules]
        elif is_contribution_report and 'LISTING INSS' in report_type_label and 'SOUS STATUT' in report_type_label:
            # INSS SOUS STATUT mappings
            def get_inss_sous_statut_column_name(rule_code, rule_name):
                mapping = {
                    'BASIC': 'Base',
                    'HOU': 'Logement',
                    'IDCA': 'Ind.Caisse',
                    'IDFF': 'Ind.Fonct',
                    'PM': 'Prime',
                    'BaseInssPen': 'BaseInssPen',
                    'BaseRisque': 'BaseRisque',
                    'INE': 'InssPers',
                    'INONP': 'InssPatr',
                    'RS': 'InssPatrRisp',
                    'TL': 'Total Inss'
                }
                return mapping.get(rule_code, make_header_readable(rule_name, col_count))
            
            inss_sous_statut_rule_order = ['BASIC', 'HOU', 'IDCA', 'IDFF', 'PM', 'BaseInssPen', 'BaseRisque', 'INE', 'INONP', 'RS', 'TL']
            filtered_rules = []
            for code in inss_sous_statut_rule_order:
                rule = next((r for r in rules if r['code'] == code), None)
                if rule:
                    filtered_rules.append(rule)
                else:
                    if code in ['BaseInssPen', 'BaseRisque']:
                        filtered_rules.append({'code': code, 'name': code, 'default_value': 450000 if code == 'BaseInssPen' else 80000})
                    else:
                        filtered_rules.append({'code': code, 'name': code})
            
            rules = filtered_rules
            col_count = base_cols + len(rules)
            readable_rules = [{'name': get_inss_sous_statut_column_name(r['code'], r['name']), 'code': r['code']} for r in rules]
        elif is_contribution_report and 'LISTING INSS' in report_type_label and ('DÉPUTÉ' in report_type_label or 'MB' in report_type_label):
            # INSS DÉPUTÉ AND MB mappings (same as CADRES SUPÉRIEURS)
            def get_inss_depute_mb_column_name(rule_code, rule_name):
                mapping = {
                    'BASIC': 'Base',
                    'HOU': 'Logement',
                    'PDR': 'Ind.Charg Spe',
                    'FDR': 'Repr',
                    'FDEE': 'Frais Equip',
                    'BasePension': 'BasePension',
                    'BaseRisque': 'BaseRisque',
                    'INE': 'InssPers',
                    'INONP': 'InssPatr',
                    'RS': 'InssPatrRisp',
                    'TL': 'Total Inss'
                }
                return mapping.get(rule_code, make_header_readable(rule_name, col_count))
            
            inss_depute_mb_rule_order = ['BASIC', 'HOU', 'PDR', 'FDR', 'FDEE', 'BasePension', 'BaseRisque', 'INE', 'INONP', 'RS', 'TL']
            filtered_rules = []
            for code in inss_depute_mb_rule_order:
                rule = next((r for r in rules if r['code'] == code), None)
                if rule:
                    filtered_rules.append(rule)
                else:
                    if code == 'BasePension':
                        filtered_rules.append({'code': code, 'name': code, 'default_value': 450000})
                    elif code == 'BaseRisque':
                        filtered_rules.append({'code': code, 'name': code, 'default_value': 80000})
                    else:
                        filtered_rules.append({'code': code, 'name': code})
            
            rules = filtered_rules
            col_count = base_cols + len(rules)
            readable_rules = [{'name': get_inss_depute_mb_column_name(r['code'], r['name']), 'code': r['code']} for r in rules]
        else:
            readable_rules = [{'name': make_header_readable(r['name'], col_count), 'code': r['code']} for r in rules]
        
        # Set standard headers - with special handling for salary listing reports
        if is_salary_listing and ('SOUS STATUT' in report_type_label or 'CADRES SUPÉRIEURS' in report_type_label or 'DÉPUTÉ' in report_type_label or 'MB' in report_type_label):
            # Special headers for all salary listing reports
            name_header = 'Nom et Prénom'
            matricule_header = 'Matr.'
            account_header = 'Numéro de compte'
        elif col_count > 12:
            name_header = 'NOM'
            matricule_header = 'MAT'
            account_header = 'COMPTE'
        elif col_count > 8:
            name_header = 'NOM ET PRÉNOM'
            matricule_header = 'MATRICULE'
            account_header = 'N° COMPTE'
        else:
            name_header = 'Nom et Prénom'
            matricule_header = 'Matricule'
            account_header = 'Numéro de compte'
        
        if is_credit_retenue:
            headers = [name_header, matricule_header] + [r['name'] for r in readable_rules]
        elif is_contribution_report or is_salary_listing:
            headers = [name_header, matricule_header] + [r['name'] for r in readable_rules]
        else:
            headers = [name_header, matricule_header, account_header] + [r['name'] for r in readable_rules]
        
        grand_totals = {rule['code']: 0.0 for rule in rules}
        
        # Define number formatting functions
        def format_number_with_spaces(value, decimals=2):
            """Format number with space separators instead of commas"""
            if decimals == 0:
                formatted = f"{value:,.0f}"
            else:
                formatted = f"{value:,.{decimals}f}"
            # Replace commas with spaces
            return formatted.replace(',', ' ')
        
        def format_total(value, col_count):
            """Format totals with full numbers using space separators, no decimals"""
            return format_number_with_spaces(value, 0)  # Always 0 decimals
        
        # ORIGINAL flattening logic for credit/retenue reports
        if is_credit_retenue:
            flattened_data = {}
            for bank_name, bank_info in data_by_bank.items():
                for retenue_name, retenue_data in bank_info.get('retenues', {}).items():
                    section_name = f"{bank_name} - {retenue_name}"
                    flattened_data[section_name] = retenue_data
        else:
            flattened_data = data_by_bank
        
        # Process each bank/section - ORIGINAL GROUPING LOGIC
        for bank_name, bank_data in flattened_data.items():
            # Bank header - ORIGINAL logic (show if multiple sections on summary, or always for contribution, but not for salary listing)
            if bank_name.strip() and not is_salary_listing:
                if len(flattened_data) > 1 or is_contribution_report:
                    story.append(Paragraph(bank_name.upper(), bank_header_style))
                    story.append(Spacer(1, 3*mm))
            
            # ORIGINAL table data structure
            table_data = [headers]  # Header row
            bank_totals = {rule['code']: 0.0 for rule in rules}
            
            # Data rows with smart text truncation based on column count
            def truncate_text(text, col_count):
                """Truncate text based on column density"""
                if col_count <= 8:
                    return str(text)  # No truncation
                elif col_count <= 12:
                    return str(text)[:20] if len(str(text)) > 20 else str(text)
                else:
                    return str(text)[:15] if len(str(text)) > 15 else str(text)
            
            for record in bank_data.get('records', []):
                row_data = [
                    truncate_text(record.get('employee_name', ''), col_count),
                    truncate_text(record.get('employee_matricule', ''), col_count)
                ]
                
                # Add account number - ORIGINAL logic with truncation
                if not (is_credit_retenue or is_contribution_report or is_salary_listing):
                    row_data.append(truncate_text(record.get('bank_account', ''), col_count))
                
                # Add rule columns - ORIGINAL logic
                for rule in rules:
                    if is_credit_retenue:
                        if rule['code'] == 'DATE_DEBUT':
                            value = record.get('date_debut', '')
                        elif rule['code'] == 'DATE_FIN':
                            value = record.get('date_fin', '')
                        elif rule['code'] == 'MENSUALITE':
                            value = record.get('mensualite', 0.0)
                            bank_totals[rule['code']] += value
                            grand_totals[rule['code']] += value
                        elif rule['code'] == 'REFERENCE':
                            value = record.get('reference', '')
                        else:
                            value = 0
                    elif rule['code'] == 'MFP+INE':
                        # Special handling for combined MFP+INE column
                        mfp_value = record.get('amounts', {}).get('MFP', 0.0)
                        ine_value = record.get('amounts', {}).get('INE', 0.0)
                        value = mfp_value + ine_value
                        bank_totals[rule['code']] += value
                        grand_totals[rule['code']] += value
                    elif rule['code'] in ['BasePension', 'BaseInssPen', 'BaseRisque']:
                        # Special handling for default value columns
                        if hasattr(rule, 'default_value') or 'default_value' in rule:
                            value = rule.get('default_value', 0.0)
                        else:
                            # Fallback default values
                            if rule['code'] in ['BasePension', 'BaseInssPen']:
                                value = 450000.0
                            elif rule['code'] == 'BaseRisque':
                                value = 80000.0
                            else:
                                value = 0.0
                        bank_totals[rule['code']] += value
                        grand_totals[rule['code']] += value
                    else:
                        value = record.get('amounts', {}).get(rule['code'], 0.0)
                        bank_totals[rule['code']] += value
                        grand_totals[rule['code']] += value
                    
                    # Format value for display - always full numbers with space separators, no decimals
                    if isinstance(value, (int, float)) and rule['code'] not in ['DATE_DEBUT', 'DATE_FIN', 'REFERENCE']:
                        # Always use whole numbers (no decimal places)
                        formatted_value = format_number_with_spaces(value, 0)
                        row_data.append(formatted_value)
                    else:
                        row_data.append(truncate_text(value, col_count))
                
                table_data.append(row_data)
            
            # No bank subtotals in individual sections - only show data rows
            
            # Create table with landscape-optimized widths
            table = Table(table_data)
            
            # Calculate available width with document margins only
            # Document: 15mm left + 15mm right = 30mm total
            available_width = landscape(A3)[0] - 30*mm  # 390mm for table content
            # col_count already calculated above
            
            # DESIGN PRINCIPLE: Establish minimum readable column widths (never go below these)
            MIN_NAME_WIDTH = 50*mm      # Names need space - never smaller
            MIN_MATRICULE_WIDTH = 18*mm # Matricule is typically short
            MIN_ACCOUNT_WIDTH = 25*mm   # Account numbers need space
            MIN_RULE_WIDTH = 25*mm      # Rule columns need to be readable
            
            # Distribute columns to fit ALL content in 390mm width
            if col_count <= 5:
                # Few columns - generous spacing
                name_width = 90*mm
                matricule_width = 25*mm
                account_width = 40*mm if not (is_credit_retenue or is_contribution_report or is_salary_listing) else 0
                remaining_width = available_width - name_width - matricule_width - account_width
                rule_width = remaining_width / len(rules) if rules else 40*mm
                header_font = 12
                data_font = 11
                cell_padding = 6
            elif col_count <= 8:
                # Medium columns - balanced
                name_width = 75*mm
                matricule_width = 22*mm
                account_width = 35*mm if not (is_credit_retenue or is_contribution_report or is_salary_listing) else 0
                remaining_width = available_width - name_width - matricule_width - account_width
                rule_width = remaining_width / len(rules) if rules else 30*mm
                header_font = 11
                data_font = 10
                cell_padding = 5
            elif col_count <= 12:
                # Many columns - fit everything
                name_width = 65*mm
                matricule_width = 20*mm
                account_width = 30*mm if not (is_credit_retenue or is_contribution_report or is_salary_listing) else 0
                remaining_width = available_width - name_width - matricule_width - account_width
                rule_width = remaining_width / len(rules) if rules else 25*mm
                header_font = 10
                data_font = 9
                cell_padding = 4
            else:
                # Very many columns - force fit with smaller fonts
                name_width = 55*mm
                matricule_width = 18*mm
                account_width = 25*mm if not (is_credit_retenue or is_contribution_report or is_salary_listing) else 0
                remaining_width = available_width - name_width - matricule_width - account_width
                rule_width = remaining_width / len(rules) if rules else 20*mm
                header_font = 9
                data_font = 8
                cell_padding = 3
            
            # Build column widths with error checking
            try:
                col_widths = [name_width, matricule_width]
                if not (is_credit_retenue or is_contribution_report or is_salary_listing):
                    col_widths.append(account_width)
                col_widths.extend([rule_width] * len(rules))
                
                # Ensure we have the right number of column widths
                if len(col_widths) == len(headers):
                    table._argW = col_widths
                else:
                    # Fallback: equal width columns
                    equal_width = available_width / len(headers)
                    table._argW = [equal_width] * len(headers)
            except Exception:
                # Emergency fallback: simple equal widths
                equal_width = available_width / len(headers) if headers else 30*mm
                table._argW = [equal_width] * len(headers)
            
            # DESIGN PRINCIPLE: Use the calculated fonts and padding from above
            # Table styling with proper design principles
            table.setStyle(TableStyle([
                # Header row
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.7, 0.7, 0.7)),  # Light charcoal
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), header_font),
                ('TOPPADDING', (0, 0), (-1, 0), cell_padding + 4),
                ('BOTTOMPADDING', (0, 0), (-1, 0), cell_padding + 4),
                
                # Data rows
                ('ALIGN', (0, 1), (1, -1), 'LEFT'),  # Name and matricule left-aligned
                ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),  # Numbers right-aligned
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), data_font),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                
                # Borders
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), cell_padding),
                ('RIGHTPADDING', (0, 0), (-1, -1), cell_padding),
                ('TOPPADDING', (0, 0), (-1, -1), cell_padding),
                ('BOTTOMPADDING', (0, 0), (-1, -1), cell_padding),
            ]))
            
            # Simple spacing with document margins providing the left/right space
            story.append(Spacer(1, 3*mm))
            story.append(table)
            story.append(Spacer(1, 8*mm))
        
        # Grand total - Match Excel logic (show if multiple sections OR rules exist)
        if len(flattened_data) > 1 or len(rules) > 0:
            total_employees = sum(len(bd.get('records', [])) for bd in flattened_data.values())
            
            grand_total_row = ['', '']  # Start with empty cells instead of 'TOTAL GÉNÉRAL'
            
            if not (is_credit_retenue or is_contribution_report or is_salary_listing):
                grand_total_row.append(f'{total_employees} Employés')
            
            for rule_idx, rule in enumerate(rules):
                if is_credit_retenue:
                    if rule['code'] == 'MENSUALITE':
                        grand_total_row.append(format_total(grand_totals[rule['code']], col_count))
                    elif rule['code'] == 'DATE_DEBUT':
                        grand_total_row.append(f'{total_employees} Employés')
                    else:
                        grand_total_row.append('')
                elif is_salary_listing:
                    if rule_idx == 0:
                        grand_total_row.append(f'{total_employees} Employés')
                    else:
                        grand_total_row.append(format_total(grand_totals[rule['code']], col_count))
                else:
                    grand_total_row.append(format_total(grand_totals[rule['code']], col_count))
            
            grand_total_table = Table([grand_total_row])
            grand_total_table._argW = col_widths
            
            grand_total_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.7, 0.7, 0.7)),  # Light charcoal (same as headers)
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                # No GRID - removes all table lines/borders
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, 0), 4),
                ('RIGHTPADDING', (0, 0), (-1, 0), 4),
                ('TOPPADDING', (0, 0), (-1, 0), 6),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ]))
            
            story.append(grand_total_table)
        
        # Add "Prepare par:" and "Verifie par:" section at the end
        story.append(Spacer(1, 15*mm))  # Add some space before signature section
        
        # Create signature table with two columns
        signature_data = [['Préparé par:', 'Vérifié par:']]
        signature_table = Table(signature_data, colWidths=[190*mm, 190*mm])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),   # "Prepare par:" aligned left
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),  # "Verifie par:" aligned right
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            # No borders for clean appearance
        ]))
        
        story.append(signature_table)
        
        # Build PDF
        doc.build(story)
        return buffer