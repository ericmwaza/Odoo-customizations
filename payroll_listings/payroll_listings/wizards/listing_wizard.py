# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PayrollListingWizard(models.TransientModel):
    _name = 'payroll.listing.wizard'
    _description = 'Payroll Listing Wizard'

    report_type = fields.Selection(
        selection=[
            ('salaire_depute', 'LISTE DE PAIE POUR DÉPUTÉS'),
            ('salaire_cadre_superieur', 'LISTE DE PAIE POUR CADRES SUPÉRIEURS'),
            ('salaire_sous_statut', 'LISTE DE PAIE POUR SOUS STATUT'),
            ('salaire_mb', 'LISTE DE PAIE POUR MB'),
            ('inss_deputes', 'LISTING INSS DÉPUTÉS'),
            ('inss_cadres_superieurs', 'LISTING INSS CADRES SUPÉRIEURS'),
            ('inss_sous_statut', 'LISTING INSS DES SOUS STATUTS'),
            ('inss_mb', 'LISTING INSS DES MB'),
            ('ire_cadres_superieurs', 'LISTING IPR CADRES SUPÉRIEURS'),
            ('ire_deputes', 'LISTING IPR DÉPUTÉ'),
            ('ire_sous_statuts', 'LISTING IPR SOUS STATUT'),
            ('ire_mb', 'LISTING IPR POUR MB'),
            ('mfp_cadres_superieurs', 'LISTING MUTUELLE POUR LES CADRES SUPÉRIEURS'),
            ('mfp_deputes', 'LISTING MUTUELLE POUR LES DÉPUTÉS'),
            ('mfp_sous_statuts', 'LISTING MUTUELLE POUR LES SS'),
            ('mfp_mb', 'LISTING MUTUELLE POUR LES MB'),
            ('onpr_sous_statuts', 'LISTING ONPR SOUS STATUTS'),
            ('onpr_deputes', 'LISTING ONPR DÉPUTÉS'),
            ('onpr_cadres_superieurs', 'LISTING ONPR CADRES SUPÉRIEURS'),
            ('onpr_mb', 'LISTING ONPR DES MB'),
            ('ire_general', 'LISTING IPR(IRE) GÉNÉRAL'),
            ('mutuelle_general', 'LISTING MUTUELLE'),
            ('deputes', 'VIREMENT BANCAIRE DÉPUTÉ'),
            ('cadres_superieurs', 'VIREMENT BANCAIRE CADRE SUPÉRIEUR'),
            ('sous_statut', 'VIREMENT BANCAIRE SOUS STATUT'),
            ('mb', 'VIREMENT BANCAIRE MB'),
            ('pension_deputes', 'PENSION COMPLÉMENTAIRE DÉPUTÉS'),
            ('pension_cadres_superieurs', 'PENSION COMPLÉMENTAIRE CADRES SUPÉRIEURS'),
            ('pension_sous_statut', 'PENSION COMPLÉMENTAIRE SOUS STATUT'),
            ('credits_deputes', 'LISTING DES CRÉDITS DÉPUTÉS'),
            ('credits_cadres_superieurs', 'LISTING DES CRÉDITS CADRES SUPÉRIEURS'),
            ('credits_sous_statut', 'LISTING DES CRÉDITS SOUS STATUT'),
            ('retenues_deputes', 'LISTING DES RETENUES DÉPUTÉS'),
            ('retenues_cadres_superieurs', 'LISTING DES RETENUES CADRES SUPÉRIEURS'),
            ('retenues_sous_statut', 'LISTING DES RETENUES SOUS STATUT'),
            ('credits_internes_deputes', 'LISTING DES CRÉDITS INTERNES DÉPUTÉS'),
            ('credits_internes_cadres_superieurs', 'LISTING DES CRÉDITS INTERNES CADRES SUPÉRIEURS'),
            ('credits_internes_sous_statut', 'LISTING DES CRÉDITS INTERNES SOUS STATUT'),
            ('special_contribution_deputes', 'SPECIAL CONTRIBUTION DÉPUTÉS'),
            ('special_contribution_cadres_superieurs', 'SPECIAL CONTRIBUTION CADRES SUPÉRIEURS'),
        ],
        string='Type de rapport',
        required=True,
        default='salaire_depute',
    )
    payslip_run_id = fields.Many2one(
        comodel_name='hr.payslip.run',
        string='Lot de paie',
    )
    date_from = fields.Date(
        string='Date de début',
    )
    date_to = fields.Date(
        string='Date de fin',
    )
    output_type = fields.Selection(
        selection=[
            ('pdf', 'PDF'),
            ('xlsx', 'Excel'),
        ],
        string='Type de sortie',
        default='pdf',
        required=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    def _get_payslips(self):
        if self.payslip_run_id:
            return self.payslip_run_id.slip_ids
        elif self.date_from and self.date_to:
            return self.env['hr.payslip'].search([
                ('date_from', '>=', self.date_from),
                ('date_to', '<=', self.date_to),
                ('state', 'in', ['done', 'paid']),
            ])
        return self.env['hr.payslip']

    def _parse_mixed_date(self, date_value):
        """Parse date that can be actual date or text like 'AOÛT 2025'"""
        if not date_value:
            return None
            
        # If it's already a date object, return it
        if hasattr(date_value, 'year'):
            return date_value
            
        # If it's a string, try to parse it
        if isinstance(date_value, str):
            # French month mapping
            french_months = {
                'JANVIER': 1, 'FÉVRIER': 2, 'MARS': 3, 'AVRIL': 4, 'MAI': 5, 'JUIN': 6,
                'JUILLET': 7, 'AOÛT': 8, 'SEPTEMBRE': 9, 'OCTOBRE': 10, 'NOVEMBRE': 11, 'DÉCEMBRE': 12,
                'JAN': 1, 'FÉV': 2, 'MAR': 3, 'AVR': 4, 'JUI': 6, 'JUL': 7, 'AOU': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DÉC': 12
            }
            
            # Try to extract month and year from text like "AOÛT 2025"
            parts = date_value.upper().strip().split()
            if len(parts) >= 2:
                month_text = parts[0]
                try:
                    year = int(parts[1])
                    month = french_months.get(month_text, 1)
                    from datetime import date
                    return date(year, month, 1)
                except (ValueError, IndexError):
                    pass
        
        return None

    def _calculate_months_info(self, start_date, end_date):
        """Calculate months info from start and end dates"""
        start_parsed = self._parse_mixed_date(start_date)
        end_parsed = self._parse_mixed_date(end_date)
        
        if not start_parsed or not end_parsed:
            return {
                'mois': '',
                'annee': '',
                'mois_total': 0,
                'mois_restant': 0
            }
        
        from datetime import date
        today = date.today()
        
        # Calculate total months between start and end
        total_months = (end_parsed.year - start_parsed.year) * 12 + (end_parsed.month - start_parsed.month) + 1
        
        # Calculate remaining months from today
        if today < start_parsed:
            remaining_months = total_months
        elif today > end_parsed:
            remaining_months = 0
        else:
            remaining_months = (end_parsed.year - today.year) * 12 + (end_parsed.month - today.month) + 1
            
        french_months = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 
                        'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
        
        return {
            'mois': french_months[today.month],
            'annee': str(today.year),
            'mois_total': total_months,
            'mois_restant': max(0, remaining_months)
        }

    def _gather_credit_retenue_dataset(self):
        """Gather data for CREDIT/RETENUE reports from x_odoo model"""
        # Determine employee category filter
        category_map = {
            'credits_deputes': 'DEPUTES',
            'credits_cadres_superieurs': 'cadres',
            'credits_sous_statut': 'sous statut',
            'retenues_deputes': 'DEPUTES',
            'retenues_cadres_superieurs': 'cadres', 
            'retenues_sous_statut': 'sous statut',
            'credits_internes_deputes': 'DEPUTES',
            'credits_internes_cadres_superieurs': 'cadres',
            'credits_internes_sous_statut': 'sous statut'
        }
        
        category = category_map.get(self.report_type, 'DEPUTES')
        is_credit = self.report_type.startswith('credits_') and not self.report_type.startswith('credits_internes_')
        is_credit_interne = self.report_type.startswith('credits_internes_')
        
        # Get contracts for the category to filter employees
        if category == 'DEPUTES':
            contracts_domain = [('structure_type_id.name', '=', 'DEPUTES')]
        elif category == 'cadres':
            contracts_domain = [('structure_type_id.name', 'ilike', 'cadres')]
        else:  # sous statut
            contracts_domain = [('structure_type_id.name', '=', 'sous statut')]
            
        contracts = self.env['hr.contract'].search(contracts_domain)
        employee_ids = contracts.mapped('employee_id.id')
        
        # Search x_odoo records with priority logic
        if is_credit_interne:
            x_odoo_domain = [
                ('x_studio_credit_interne', '=', True),
                ('x_studio_employe', 'in', employee_ids)
            ]
        elif is_credit:
            x_odoo_domain = [
                ('x_studio_credit_interne', '=', False),
                ('x_studio_credit', '=', True),
                ('x_studio_employe', 'in', employee_ids)
            ]
        else:  # retenue
            x_odoo_domain = [
                ('x_studio_credit_interne', '=', False),
                ('x_studio_credit', '=', False),
                ('x_studio_employe', 'in', employee_ids)
            ]
        
        x_odoo_records = self.env['x_odoo'].search(x_odoo_domain)
        
        if not x_odoo_records:
            raise UserError(_(f"Aucun enregistrement trouvé pour {self.report_type}."))
        
        # Group by bank first, then by retenue type (x_name)
        data_by_group = {}
        
        for record in x_odoo_records:
            # First level: group by bank
            bank_name = record.x_studio_banque.name if record.x_studio_banque else 'Sans Banque'
            retenue_name = record.x_name or 'Sans Groupe'
            
            # Create nested structure: bank_name -> retenue_type -> records
            if bank_name not in data_by_group:
                data_by_group[bank_name] = {'retenues': {}, 'records': []}
            
            if retenue_name not in data_by_group[bank_name]['retenues']:
                data_by_group[bank_name]['retenues'][retenue_name] = {'records': []}
            
            # Format reference without bank prefix (just the reference value)
            reference_value = record.x_studio_reference or ''
            
            # Build record data
            record_data = {
                'employee_name': record.x_studio_employe.name if record.x_studio_employe else '',
                'employee_matricule': record.x_studio_employe.x_studio_matricule if record.x_studio_employe else '',
                'mensualite': record.x_studio_mensualite or 0.0,
                'reference': reference_value,  # Just the reference without bank prefix
            }
            
            # Add date fields for credit reports
            if is_credit:
                # Format dates for display
                date_debut = ''
                date_fin = ''
                
                if record.x_studio_date_de_debut_2:
                    if hasattr(record.x_studio_date_de_debut_2, 'strftime'):
                        date_debut = record.x_studio_date_de_debut_2.strftime('%d/%m/%Y')
                    else:
                        date_debut = str(record.x_studio_date_de_debut_2)
                
                if record.x_studio_date_de_fin_2:
                    if hasattr(record.x_studio_date_de_fin_2, 'strftime'):
                        date_fin = record.x_studio_date_de_fin_2.strftime('%d/%m/%Y')
                    else:
                        date_fin = str(record.x_studio_date_de_fin_2)
                
                record_data.update({
                    'date_debut': date_debut,
                    'date_fin': date_fin,
                })
            
            # Add to nested structure: bank -> retenue type -> records
            data_by_group[bank_name]['retenues'][retenue_name]['records'].append(record_data)
        
        # Build rules based on report type
        if is_credit:
            rules = [
                {'code': 'DATE_DEBUT', 'name': 'DATE DE DÉBUT'},
                {'code': 'DATE_FIN', 'name': 'DATE DE FIN'},
                {'code': 'MENSUALITE', 'name': 'MONTANT'},
                {'code': 'REFERENCE', 'name': 'NUMÉRO DE COMPTE'},
            ]
        else:  # retenue or credit_interne
            rules = [
                {'code': 'MENSUALITE', 'name': 'MONTANT'},
                {'code': 'REFERENCE', 'name': 'NUMÉRO DE COMPTE'},
            ]
        
        # French month names for date formatting
        french_months = {
            'January': 'Janvier', 'February': 'Février', 'March': 'Mars', 'April': 'Avril',
            'May': 'Mai', 'June': 'Juin', 'July': 'Juillet', 'August': 'Août',
            'September': 'Septembre', 'October': 'Octobre', 'November': 'Novembre', 'December': 'Décembre'
        }
        
        month_year = ''
        if self.date_from:
            english_month_year = self.date_from.strftime('%B %Y')
            for eng, fr in french_months.items():
                month_year = english_month_year.replace(eng, fr)
                if month_year != english_month_year:
                    break
        elif self.payslip_run_id and self.payslip_run_id.date_start:
            english_month_year = self.payslip_run_id.date_start.strftime('%B %Y')
            for eng, fr in french_months.items():
                month_year = english_month_year.replace(eng, fr)
                if month_year != english_month_year:
                    break

        period_data = {
            'run': self.payslip_run_id.name if self.payslip_run_id else None,
            'date_from': self.date_from.strftime('%d/%m/%Y') if self.date_from else '',
            'date_to': self.date_to.strftime('%d/%m/%Y') if self.date_to else '',
            'month_year': month_year,
        }
        
        # Get report type label
        report_type_label = dict(self._fields['report_type'].selection).get(self.report_type)
        
        return {
            'doc_ids': self.ids,
            'doc_model': 'payroll.listing.wizard',
            'docs': self,
            'data_by_bank': data_by_group,  # Reuse same structure as bank reports
            'rules': rules,
            'company': self.company_id,
            'period': period_data,
            'report_type_label': report_type_label,
        }

    def _gather_dataset(self):
        # Handle CREDIT/RETENUE/CREDIT_INTERNE reports differently - they use x_odoo model
        if self.report_type.startswith('credits_') or self.report_type.startswith('retenues_') or self.report_type.startswith('credits_internes_'):
            return self._gather_credit_retenue_dataset()
            
        # Define contract filtering criteria based on report type
        contracts_domain = []
        
        if self.report_type in ['salaire_depute', 'deputes']:
            contracts_domain = [('structure_type_id.name', '=', 'DEPUTES')]
        elif self.report_type == 'pension_deputes':
            contracts_domain = [('structure_type_id.name', '=', 'DEPUTES')]
        elif self.report_type == 'pension_cadres_superieurs':
            contracts_domain = [('structure_type_id.name', 'ilike', 'cadres')]
        elif self.report_type == 'pension_sous_statut':
            contracts_domain = [('structure_type_id.name', '=', 'sous statut')]
        elif self.report_type == 'special_contribution_deputes':
            contracts_domain = [('structure_type_id.name', '=', 'DEPUTES')]
        elif self.report_type == 'special_contribution_cadres_superieurs':
            contracts_domain = [('structure_type_id.name', 'ilike', 'cadres')]
        elif self.report_type == 'mb':
            contracts_domain = [('structure_type_id.name', '=', 'DEPUTES'), ('x_studio_membre_du_bureau', '=', True)]
        elif self.report_type in ['salaire_cadre_superieur', 'cadres_superieurs']:
            contracts_domain = [('structure_type_id.name', 'ilike', 'cadres')]
        elif self.report_type in ['salaire_sous_statut', 'sous_statut']:
            contracts_domain = [('structure_type_id.name', '=', 'sous statut')]
        elif self.report_type == 'salaire_mb':
            contracts_domain = [('structure_type_id.name', '=', 'DEPUTES'), ('x_studio_membre_du_bureau', '=', True)]
        elif self.report_type == 'inss_deputes':
            contracts_domain = [('x_studio_salary_category', '=', 'Deputies'), ('x_studio_many2one_field_1j2_1isvo5tbe.x_name', '=', 'INSS')]
        elif self.report_type == 'inss_cadres_superieurs':
            contracts_domain = [('x_studio_salary_category', 'ilike', 'cadres'), ('x_studio_many2one_field_1j2_1isvo5tbe.x_name', '=', 'INSS')]
        elif self.report_type == 'inss_sous_statut':
            contracts_domain = [('x_studio_salary_category', '=', 'sous statut'), ('x_studio_many2one_field_1j2_1isvo5tbe.x_name', '=', 'INSS')]
        elif self.report_type == 'inss_mb':
            contracts_domain = [('x_studio_salary_category', '=', 'Deputies'), ('x_studio_many2one_field_1j2_1isvo5tbe.x_name', '=', 'INSS'), ('x_studio_membre_du_bureau', '=', True)]
        elif self.report_type == 'ire_cadres_superieurs':
            contracts_domain = [('x_studio_salary_category', 'ilike', 'cadres')]
        elif self.report_type == 'ire_deputes':
            contracts_domain = [('x_studio_salary_category', '=', 'Deputies')]
        elif self.report_type == 'ire_sous_statuts':
            contracts_domain = [('x_studio_salary_category', '=', 'sous statut')]
        elif self.report_type == 'ire_mb':
            contracts_domain = [('x_studio_salary_category', '=', 'Deputies'), ('x_studio_membre_du_bureau', '=', True)]
        elif self.report_type == 'mfp_cadres_superieurs':
            contracts_domain = [('x_studio_salary_category', 'ilike', 'cadres')]
        elif self.report_type == 'mfp_deputes':
            contracts_domain = [('x_studio_salary_category', '=', 'Deputies')]
        elif self.report_type == 'mfp_sous_statuts':
            contracts_domain = [('x_studio_salary_category', '=', 'sous statut')]
        elif self.report_type == 'mfp_mb':
            contracts_domain = [('x_studio_salary_category', '=', 'Deputies'), ('x_studio_membre_du_bureau', '=', True)]
        elif self.report_type == 'onpr_sous_statuts':
            contracts_domain = [('x_studio_salary_category', '=', 'sous statut'), ('x_studio_many2one_field_1j2_1isvo5tbe.x_name', '=', 'ONPR')]
        elif self.report_type == 'onpr_deputes':
            contracts_domain = [('x_studio_salary_category', '=', 'Deputies'), ('x_studio_many2one_field_1j2_1isvo5tbe.x_name', '=', 'ONPR')]
        elif self.report_type == 'onpr_cadres_superieurs':
            contracts_domain = [('x_studio_salary_category', 'ilike', 'cadres'), ('x_studio_many2one_field_1j2_1isvo5tbe.x_name', 'in', ['ONPR', 'PENIE'])]
        elif self.report_type == 'onpr_mb':
            contracts_domain = [('x_studio_salary_category', '=', 'Deputies'), ('x_studio_many2one_field_1j2_1isvo5tbe.x_name', '=', 'ONPR'), ('x_studio_membre_du_bureau', '=', True)]
        elif self.report_type == 'ire_general':
            contracts_domain = ['|', '|', ('x_studio_salary_category', '=', 'Deputies'), ('x_studio_salary_category', '=', 'sous statut'), ('x_studio_salary_category', 'ilike', 'cadres')]
        elif self.report_type == 'mutuelle_general':
            contracts_domain = ['|', '|', ('x_studio_salary_category', '=', 'Deputies'), ('x_studio_salary_category', '=', 'sous statut'), ('x_studio_salary_category', 'ilike', 'cadres')]
        
        # Get contracts matching criteria
        contracts = self.env['hr.contract'].search(contracts_domain)
        
        # Debug output for MB reports
        if 'mb' in self.report_type:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.info(f"MB Report {self.report_type}: Found {len(contracts)} contracts with domain {contracts_domain}")
            if contracts:
                _logger.info(f"Contract IDs: {contracts.ids}")
                for contract in contracts[:3]:  # Log first 3
                    _logger.info(f"Contract {contract.id}: employee={contract.employee_id.name}, MB={getattr(contract, 'x_studio_membre_du_bureau', 'FIELD_NOT_FOUND')}")
        
        if not contracts:
            raise UserError(_("Aucun contrat trouvé pour les critères sélectionnés."))
        
        # Get payslips for these contracts within date range
        payslip_domain = [
            ('contract_id', 'in', contracts.ids),
            ('state', 'in', ['done', 'paid']),
        ]
        
        if self.payslip_run_id:
            payslip_domain.append(('payslip_run_id', '=', self.payslip_run_id.id))
        elif self.date_from and self.date_to:
            payslip_domain.extend([
                ('date_from', '>=', self.date_from),
                ('date_to', '<=', self.date_to),
            ])
        
        filtered_payslips = self.env['hr.payslip'].search(payslip_domain)
        if not filtered_payslips:
            raise UserError(_("Aucun bulletin de paie trouvé pour les critères sélectionnés."))

        data_by_bank = {}
        all_rules = set()
        employees_processed = set()

        for payslip in filtered_payslips:
            employee_id = payslip.employee_id.id
            
            # Determine bank and account based on report type
            if self.report_type in ['salaire_depute', 'salaire_cadre_superieur', 'salaire_sous_statut', 'salaire_mb']:
                # Salary listing reports: no bank grouping, no account numbers, no headers
                bank_name = ''  # No group header - leave blank
                account_number = ''  # No account numbers shown
            elif self.report_type in ['pension_deputes', 'pension_cadres_superieurs', 'pension_sous_statut']:
                # Pension reports use contract's pension bank
                pension_bank_account = payslip.contract_id.x_studio_banque_pension_complementaire
                if pension_bank_account and pension_bank_account.bank_id:
                    bank_name = pension_bank_account.bank_id.name
                    account_number = pension_bank_account.acc_number or ''
                else:
                    bank_name = 'Sans Banque Pension'
                    account_number = ''
            elif self.report_type.startswith(('inss_', 'ire_', 'mfp_', 'onpr_', 'special_contribution_')) or self.report_type.endswith('_deputes'):
                # Contribution reports use configured banks - all employees use same bank+account
                if not payslip.contract_id or not payslip.contract_id.structure_type_id:
                    bank_name = 'Sans Banque Configurée - Contrat Manquant'
                    account_number = ''
                else:
                    contribution_type_map = {
                        'inss_': 'inss',
                        'ire_': 'ipr', 
                        'mfp_': 'mutuelle',
                        'onpr_': 'onpr',
                        'special_contribution_': 'special_contribution'
                    }
                    
                    contribution_type = None
                    # Check for prefix-based contribution types
                    for prefix, contrib_type in contribution_type_map.items():
                        if self.report_type.startswith(prefix):
                            contribution_type = contrib_type
                            break
                    
                    # Check for DEPUTES suffix-based contribution types
                    if not contribution_type and self.report_type.endswith('_deputes'):
                        if 'inss_' in self.report_type:
                            contribution_type = 'inss'
                        elif 'ire_' in self.report_type:
                            contribution_type = 'ipr'
                        elif 'mfp_' in self.report_type:
                            contribution_type = 'mutuelle'
                        elif 'onpr_' in self.report_type:
                            contribution_type = 'onpr'
                        elif 'special_contribution_' in self.report_type:
                            contribution_type = 'special_contribution'
                    
                    if contribution_type:
                        # All employees use same configured bank+account for this contribution type
                        bank_name = self.env['contribution.bank.config'].get_bank_for_contribution(
                            contribution_type
                        )
                        # Debug: Add report type to bank name to verify logic is working
                        if bank_name == 'Sans Banque Configurée':
                            bank_name = f'Sans Banque Configurée - {contribution_type.upper()}'
                        account_number = ''  # Individual account numbers not shown for contribution reports
                    else:
                        bank_name = 'Sans Banque Configurée - Type Non Trouvé'
                        account_number = ''
            else:
                # Salary and VIREMENT BANCAIRE reports use employee's bank
                bank_name = payslip.employee_id.bank_account_id.bank_id.name or 'Sans Banque'
                account_number = payslip.employee_id.bank_account_id.acc_number
            
            # Skip if employee already processed for this bank
            employee_bank_key = (employee_id, bank_name)
            if employee_bank_key in employees_processed:
                continue
            employees_processed.add(employee_bank_key)
            
            if bank_name not in data_by_bank:
                data_by_bank[bank_name] = {'records': []}

            all_rules.update(payslip.line_ids.salary_rule_id)
            record = {
                'employee_name': payslip.employee_id.name,
                'employee_identification': payslip.employee_id.identification_id,
                'employee_matricule': payslip.employee_id.x_studio_matricule,
                'bank_account': account_number,
                'net_wage': payslip.line_ids.filtered(lambda line: line.code == 'NET').amount,
                'amounts': {line.code: line.amount for line in payslip.line_ids},
            }
            data_by_bank[bank_name]['records'].append(record)

        unique_rules = sorted(list(all_rules), key=lambda r: r.code)
        rules_to_pass = []

        if self.report_type in ['deputes', 'cadres_superieurs', 'sous_statut', 'mb']:
            net_rule = next((r for r in unique_rules if r.code == 'NET'), None)
            if net_rule:
                rules_to_pass.append({'code': 'NET', 'name': 'NET'})

        elif self.report_type in ['pension_deputes', 'pension_cadres_superieurs', 'pension_sous_statut']:
            pc_rule = next((r for r in unique_rules if r.code == 'PC'), None)
            if pc_rule:
                rules_to_pass.append({'code': 'PC', 'name': 'PC'})

        elif self.report_type in ['special_contribution_deputes', 'special_contribution_cadres_superieurs']:
            sls_rule = next((r for r in unique_rules if r.code == 'sls'), None)
            if sls_rule:
                rules_to_pass.append({'code': 'sls', 'name': 'MONTANT'})

        elif self.report_type == 'inss_deputes':
            specific_codes = ['BASIC', 'HOU', 'IDF', 'INON', 'INONP', 'RS', 'TL']
            for code in specific_codes:
                rule_record = next((r for r in unique_rules if r.code == code), None)
                if rule_record:
                    display_name = 'Base' if code == 'BASIC' else rule_record.name
                    rules_to_pass.append({'code': rule_record.code, 'name': display_name})
        
        elif self.report_type == 'inss_cadres_superieurs':
            specific_codes = ['BASIC', 'HOU', 'FDEE', 'FDR', 'PDR', 'INON', 'INONP', 'RS', 'TL']
            for code in specific_codes:
                rule_record = next((r for r in unique_rules if r.code == code), None)
                if rule_record:
                    display_name = 'Base' if code == 'BASIC' else rule_record.name
                    rules_to_pass.append({'code': rule_record.code, 'name': display_name})
        
        elif self.report_type == 'inss_sous_statut':
            specific_codes = ['BASIC', 'HOU', 'PM', 'IDFF', 'PDF', 'PDR', 'INON', 'INONP', 'RS', 'TL']
            for code in specific_codes:
                rule_record = next((r for r in unique_rules if r.code == code), None)
                if rule_record:
                    display_name = 'Base' if code == 'BASIC' else rule_record.name
                    rules_to_pass.append({'code': rule_record.code, 'name': display_name})
        
        elif self.report_type == 'ire_cadres_superieurs':
            specific_codes = ['BASIC', 'HOU', 'FDR', 'PDR', 'PC', 'INON', 'MFP', 'TASY', 'IREL', 'IREU', 'IRE']
            for code in specific_codes:
                rule_record = next((r for r in unique_rules if r.code == code), None)
                if rule_record:
                    display_name = 'Base' if code == 'BASIC' else rule_record.name
                    rules_to_pass.append({'code': rule_record.code, 'name': display_name})
        
        elif self.report_type == 'ire_deputes':
            specific_codes = ['BASIC', 'HOU', 'IDS', 'IDF', 'PC', 'INON', 'MFP', 'TASY', 'IREL', 'IREU', 'IRE']
            for code in specific_codes:
                rule_record = next((r for r in unique_rules if r.code == code), None)
                if rule_record:
                    display_name = 'Base' if code == 'BASIC' else rule_record.name
                    rules_to_pass.append({'code': rule_record.code, 'name': display_name})
        
        elif self.report_type == 'ire_sous_statuts':
            specific_codes = ['BASIC', 'HOU', 'PM', 'AF', 'PC', 'INON', 'MFP', 'TASY', 'IREL', 'IREU', 'IRE']
            for code in specific_codes:
                rule_record = next((r for r in unique_rules if r.code == code), None)
                if rule_record:
                    display_name = 'Base' if code == 'BASIC' else rule_record.name
                    rules_to_pass.append({'code': rule_record.code, 'name': display_name})
        
        elif self.report_type == 'ire_mb':
            specific_codes = ['BASIC', 'HOU', 'IDS', 'IDF', 'PC', 'INON', 'MFP', 'TASY', 'IREL', 'IREU', 'IRE']
            for code in specific_codes:
                rule_record = next((r for r in unique_rules if r.code == code), None)
                if rule_record:
                    display_name = 'Base' if code == 'BASIC' else rule_record.name
                    rules_to_pass.append({'code': rule_record.code, 'name': display_name})
        
        elif self.report_type == 'mfp_cadres_superieurs':
            specific_codes = ['BASIC', 'FDR', 'PDR', 'MFP', 'MFPP', 'TMFP']
            for code in specific_codes:
                rule_record = next((r for r in unique_rules if r.code == code), None)
                if rule_record:
                    display_name = 'Base' if code == 'BASIC' else rule_record.name
                    rules_to_pass.append({'code': rule_record.code, 'name': display_name})
        
        elif self.report_type == 'mfp_deputes':
            specific_codes = ['BASIC', 'IDS', 'IDF', 'FDD', 'MFP', 'MFPP', 'TMFP']
            for code in specific_codes:
                rule_record = next((r for r in unique_rules if r.code == code), None)
                if rule_record:
                    display_name = 'Base' if code == 'BASIC' else rule_record.name
                    rules_to_pass.append({'code': rule_record.code, 'name': display_name})
        
        elif self.report_type == 'mfp_sous_statuts':
            specific_codes = ['BASIC', 'PM', 'IDCA', 'IDFF', 'PDF', 'PDR', 'MFP', 'MFPP', 'TMFP']
            for code in specific_codes:
                rule_record = next((r for r in unique_rules if r.code == code), None)
                if rule_record:
                    display_name = 'Base' if code == 'BASIC' else rule_record.name
                    rules_to_pass.append({'code': rule_record.code, 'name': display_name})
        
        elif self.report_type == 'onpr_sous_statuts':
            specific_codes = ['BASIC', 'HOU', 'PM', 'INON', 'INONP', 'RS', 'PSDG', 'TL']
            for code in specific_codes:
                rule_record = next((r for r in unique_rules if r.code == code), None)
                if rule_record:
                    display_name = 'Base' if code == 'BASIC' else rule_record.name
                    rules_to_pass.append({'code': rule_record.code, 'name': display_name})
        
        elif self.report_type == 'onpr_deputes':
            specific_codes = ['BASIC', 'HOU', 'INON', 'INONP', 'RS', 'PSDG', 'TL']
            for code in specific_codes:
                rule_record = next((r for r in unique_rules if r.code == code), None)
                if rule_record:
                    display_name = 'Base' if code == 'BASIC' else rule_record.name
                    rules_to_pass.append({'code': rule_record.code, 'name': display_name})
        
        elif self.report_type == 'onpr_cadres_superieurs':
            specific_codes = ['BASIC', 'HOU', 'FDEE', 'FDR', 'PDR', 'INON', 'INONP', 'RS', 'TL']
            for code in specific_codes:
                rule_record = next((r for r in unique_rules if r.code == code), None)
                if rule_record:
                    display_name = 'Base' if code == 'BASIC' else rule_record.name
                    rules_to_pass.append({'code': rule_record.code, 'name': display_name})
        
        elif self.report_type == 'inss_mb':
            specific_codes = ['BASIC', 'HOU', 'IDF', 'INON', 'INONP', 'RS', 'TL']
            for code in specific_codes:
                rule_record = next((r for r in unique_rules if r.code == code), None)
                if rule_record:
                    display_name = 'Base' if code == 'BASIC' else rule_record.name
                    rules_to_pass.append({'code': rule_record.code, 'name': display_name})
        
        elif self.report_type == 'mfp_mb':
            specific_codes = ['BASIC', 'IDS', 'IDF', 'FDD', 'MFP', 'MFPP', 'TMFP']
            for code in specific_codes:
                rule_record = next((r for r in unique_rules if r.code == code), None)
                if rule_record:
                    display_name = 'Base' if code == 'BASIC' else rule_record.name
                    rules_to_pass.append({'code': rule_record.code, 'name': display_name})
        
        elif self.report_type == 'onpr_mb':
            specific_codes = ['BASIC', 'HOU', 'INON', 'INONP', 'RS', 'PSDG', 'TL']
            for code in specific_codes:
                rule_record = next((r for r in unique_rules if r.code == code), None)
                if rule_record:
                    display_name = 'Base' if code == 'BASIC' else rule_record.name
                    rules_to_pass.append({'code': rule_record.code, 'name': display_name})
        
        elif self.report_type == 'ire_general':
            # Merge all IPR codes from deputes, cadres_superieurs, and sous_statuts
            specific_codes = ['BASIC', 'HOU', 'IDS', 'IDF', 'FDEE', 'FDR', 'PM', 'AF', 'PC', 'PDR', 'INON', 'MFP', 'TASY', 'IREL', 'IREU', 'IRE']
            for code in specific_codes:
                rule_record = next((r for r in unique_rules if r.code == code), None)
                if rule_record:
                    display_name = 'Base' if code == 'BASIC' else rule_record.name
                    rules_to_pass.append({'code': rule_record.code, 'name': display_name})
        
        elif self.report_type == 'mutuelle_general':
            # Merge all Mutuelle codes from deputes, cadres_superieurs, and sous_statuts
            specific_codes = ['BASIC', 'HOU', 'IDS', 'IDF', 'FDD', 'FDEE', 'FDR', 'PM', 'IDCA', 'IDFF', 'PDF', 'PDR', 'MFP', 'MFPP', 'TMFP']
            for code in specific_codes:
                rule_record = next((r for r in unique_rules if r.code == code), None)
                if rule_record:
                    display_name = 'Base' if code == 'BASIC' else rule_record.name
                    rules_to_pass.append({'code': rule_record.code, 'name': display_name})

        elif self.report_type in ['salaire_depute', 'salaire_cadre_superieur', 'salaire_sous_statut', 'salaire_mb']:
            structure_rules = self.env['hr.salary.rule']
            structure_name_map = {
                'salaire_depute': 'DEPUTES',
                'salaire_cadre_superieur': 'Cadres supérieurs', 
                'salaire_sous_statut': 'sous statut',
                'salaire_mb': 'DEPUTES'
            }
            structure_name = structure_name_map.get(self.report_type)
            structure_type = self.env['hr.payroll.structure.type'].search([('name', '=', structure_name)], limit=1)
            if structure_type:
                structures = self.env['hr.payroll.structure'].search([('type_id', '=', structure_type.id)])
                structure_rules = structures.mapped('rule_ids')

            exclude_keywords = ['PATRON', 'IRE', 'TEST', 'Taxable Salary']
            for r in structure_rules:
                if r.appears_on_payslip and r.code != 'NET' and not any(keyword in r.name for keyword in exclude_keywords):
                    rules_to_pass.append({'code': r.code, 'name': r.name})
            
            rules_to_pass = sorted(rules_to_pass, key=lambda x: x['code'])
            
            # Always add NET rule as the last column for salary reports
            net_rule = self.env['hr.salary.rule'].search([('code', '=', 'NET')], limit=1)
            if net_rule:
                rules_to_pass.append({'code': 'NET', 'name': 'Salaire Net'})


        # Get base report type label
        report_type_label = dict(self._fields['report_type'].selection).get(self.report_type)
        
        # Override titles for Mutuelle reports only
        if self.report_type == 'mfp_cadres_superieurs':
            report_type_label = 'COTISATION DES CADRES SUPERIEURS A LA MUTUELLE DE LA FONCTION PUBLIQUE'
        elif self.report_type == 'mfp_sous_statuts':
            report_type_label = 'COTISATION DES SOUS STATUTS A LA MUTUELLE DE LA FONCTION PUBLIQUE'
        elif self.report_type == 'mfp_deputes':
            report_type_label = 'COTISATION DES DEPUTES A LA MUTUELLE DE LA FONCTION PUBLIQUE'
        
        # French month names for date formatting
        french_months = {
            'January': 'Janvier', 'February': 'Février', 'March': 'Mars', 'April': 'Avril',
            'May': 'Mai', 'June': 'Juin', 'July': 'Juillet', 'August': 'Août',
            'September': 'Septembre', 'October': 'Octobre', 'November': 'Novembre', 'December': 'Décembre'
        }
        
        month_year = ''
        if self.date_from:
            english_month_year = self.date_from.strftime('%B %Y')
            for eng, fr in french_months.items():
                month_year = english_month_year.replace(eng, fr)
                if month_year != english_month_year:
                    break
        elif self.payslip_run_id and self.payslip_run_id.date_start:
            english_month_year = self.payslip_run_id.date_start.strftime('%B %Y')
            for eng, fr in french_months.items():
                month_year = english_month_year.replace(eng, fr)
                if month_year != english_month_year:
                    break

        period_data = {
            'run': self.payslip_run_id.name if self.payslip_run_id else None,
            'date_from': self.date_from.strftime('%d/%m/%Y') if self.date_from else '',
            'date_to': self.date_to.strftime('%d/%m/%Y') if self.date_to else '',
            'month_year': month_year,
        }

        return {
            'doc_ids': self.ids,
            'doc_model': 'payroll.listing.wizard',
            'docs': self,
            'data_by_bank': data_by_bank,
            'rules': rules_to_pass,
            'company': self.company_id,
            'period': period_data,
            'report_type_label': report_type_label,
        }

    def action_generate(self):
        dataset = self._gather_dataset()
        if self.output_type == 'pdf':
            # Use custom ReportLab PDF generation for TRUE landscape
            return {
                'type': 'ir.actions.act_url',
                'url': f'/payroll/pdf/generate?wizard_id={self.id}',
                'target': 'self',
            }
        else:
            return self.env.ref('payroll_listings.action_xlsx_employee_structure').report_action(self, data=dataset)
