# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime


class BudgetReportWizard(models.TransientModel):
    _name = 'budget.report.wizard'
    _description = 'Assistant Rapport Budget'

    budget_id = fields.Many2one(
        'budget.analytic',
        string='Budget',
        required=True,
        help="Sélectionnez le budget"
    )

    date_from = fields.Date(
        string='Date de début',
        required=True,
        default=lambda self: fields.Date.today().replace(month=1, day=1)
    )

    date_to = fields.Date(
        string='Date de fin',
        required=True,
        default=fields.Date.today
    )

    report_type = fields.Selection([
        ('excel', 'Excel')
    ], string='Type de Document', default='excel', required=True)

    include_monthly_detail = fields.Boolean(
        string='Inclure le détail par mois',
        default=False,
        help="Ajouter une feuille avec le détail mensuel"
    )

    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company
    )

    def action_generate_report(self):
        """Generate the budget Excel report"""
        self.ensure_one()

        # Validate configuration
        if not self.company_id.budget_encaissement_plan_ids:
            raise UserError(_("Veuillez configurer les plans analytiques d'encaissement dans Paramètres → Comptabilité"))

        if not self.company_id.budget_execution_plan_ids:
            raise UserError(_("Veuillez configurer les plans analytiques d'exécution dans Paramètres → Comptabilité"))

        # Get report data
        data = self._get_report_data()

        return self._generate_excel_report(data)

    def _get_report_data(self):
        """Aggregate data for the report"""
        self.ensure_one()

        # Get all analytic accounts from encaissement plan
        encaissement_accounts = self.env['account.analytic.account'].search([
            ('plan_id', 'in', self.company_id.budget_encaissement_plan_ids.ids)
        ])

        # Create a mapping of account names (lowercase) to encaissement accounts
        enc_by_name = {acc.name.lower().strip(): acc for acc in encaissement_accounts}

        report_lines = []

        # Process each budget line (which has expense plan accounts)
        for line in self.budget_id.budget_line_ids:
            # Get the expense account from the budget line
            exec_account = None
            for field_name in line._fields.keys():
                if field_name.startswith('x_plan'):
                    field_value = line[field_name]
                    if field_value and hasattr(field_value, 'name'):
                        exec_account = field_value
                        break

            if not exec_account:
                continue

            # Check if an account with the same name exists in encaissement plan
            account_name_lower = exec_account.name.lower().strip()
            if account_name_lower not in enc_by_name:
                continue

            enc_account = enc_by_name[account_name_lower]

            # Budget amount from this line
            credit_annuel = line.budget_amount

            # Encaissement = sum of analytic lines from encaissement plan account
            # Search for analytic lines where the encaissement plan field matches enc_account
            encaissement = 0
            all_analytic_lines = self.env['account.analytic.line'].search([
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to)
            ])

            # Check each line to see if it has the enc_account in any x_plan field
            for al in all_analytic_lines:
                for field_name in al._fields.keys():
                    if field_name.startswith('x_plan'):
                        field_value = al[field_name]
                        if field_value and field_value.id == enc_account.id:
                            encaissement += al.amount
                            break

            # Exécution = committed amount from budget line
            execution = line.committed_amount

            # Calculations
            solde_theorique = credit_annuel - encaissement
            solde_reel = encaissement - execution
            taux_realisation = (execution / credit_annuel * 100) if credit_annuel else 0

            report_lines.append({
                'rubrique': exec_account.name,
                'credit_annuel': credit_annuel,
                'encaissement': encaissement,
                'execution': execution,
                'solde_theorique': solde_theorique,
                'solde_reel': solde_reel,
                'taux_realisation': taux_realisation,
            })

        result = {
            'budget_name': self.budget_id.name,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_name': self.company_id.name,
            'company_logo': self.company_id.logo if self.company_id.logo else False,
            'lines': report_lines,
            'total_credit': sum(l['credit_annuel'] for l in report_lines),
            'total_encaissement': sum(l['encaissement'] for l in report_lines),
            'total_execution': sum(l['execution'] for l in report_lines),
            'total_solde_theorique': sum(l['solde_theorique'] for l in report_lines),
            'total_solde_reel': sum(l['solde_reel'] for l in report_lines),
            'include_monthly_detail': self.include_monthly_detail,
        }

        # Add monthly breakdown if requested
        if self.include_monthly_detail:
            result['monthly_data'] = self._get_monthly_data(encaissement_accounts, enc_by_name)

        return result

    def _get_monthly_data(self, encaissement_accounts, enc_by_name):
        """Get detailed transaction data for each budget line"""
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta

        detailed_data = []

        # Process each budget line
        for budget_line in self.budget_id.budget_line_ids:
            exec_account = None
            for field_name in budget_line._fields.keys():
                if field_name.startswith('x_plan'):
                    field_value = budget_line[field_name]
                    if field_value and hasattr(field_value, 'name'):
                        exec_account = field_value
                        break

            if not exec_account:
                continue

            # Check if account exists in encaissement plan
            account_name_lower = exec_account.name.lower().strip()
            if account_name_lower not in enc_by_name:
                continue

            enc_account = enc_by_name[account_name_lower]

            # Get all transactions for this budget line grouped by month
            monthly_transactions = {}

            # Generate list of months in the date range
            current_date = self.date_from.replace(day=1)
            while current_date <= self.date_to:
                month_start = current_date
                month_end = (current_date + relativedelta(months=1)) - timedelta(days=1)
                if month_end > self.date_to:
                    month_end = self.date_to

                month_key = current_date.strftime('%B')
                monthly_transactions[month_key] = {
                    'encaissement': [],
                    'execution': []
                }

                # Get encaissement transactions for this month
                all_analytic_lines = self.env['account.analytic.line'].search([
                    ('date', '>=', month_start),
                    ('date', '<=', month_end)
                ])

                total_encaissement = 0
                for al in all_analytic_lines:
                    for field_name in al._fields.keys():
                        if field_name.startswith('x_plan'):
                            field_value = al[field_name]
                            if field_value and field_value.id == enc_account.id:
                                total_encaissement += al.amount
                                break

                if total_encaissement > 0:
                    monthly_transactions[month_key]['encaissement'].append({
                        'libelle': 'Encaissement',
                        'amount': total_encaissement
                    })

                # Get execution transactions for this month (from expense plan)
                exec_lines = self.env['account.analytic.line'].search([
                    ('date', '>=', month_start),
                    ('date', '<=', month_end)
                ])

                for al in exec_lines:
                    for field_name in al._fields.keys():
                        if field_name.startswith('x_plan'):
                            field_value = al[field_name]
                            if field_value and field_value.id == exec_account.id:
                                monthly_transactions[month_key]['execution'].append({
                                    'libelle': al.name or 'Sans libellé',
                                    'amount': abs(al.amount)
                                })
                                break

                current_date = current_date + relativedelta(months=1)

            # Add budget line detail
            detailed_data.append({
                'rubrique': exec_account.name,
                'credit_annuel': budget_line.budget_amount,
                'monthly_transactions': monthly_transactions
            })

        return detailed_data

    def _generate_excel_report(self, data):
        """Generate Excel report"""
        return self.env['budget.report.excel'].generate_excel_report(self, data)
