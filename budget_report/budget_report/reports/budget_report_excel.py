# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import UserError
import io
import base64
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class BudgetReportExcel(models.AbstractModel):
    _name = 'budget.report.excel'
    _description = 'Budget Report Excel Generator'

    def _add_monthly_sheet(self, workbook, data):
        """Add separate sheet for each month with transaction details"""
        # Define formats
        rubrique_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'align': 'center',
            'bg_color': '#D3D3D3'
        })

        credit_format = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'align': 'left',
            'bg_color': '#E8E8E8'
        })

        column_header_format = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'align': 'center',
            'bg_color': '#F0F0F0',
            'border': 1
        })

        cell_format = workbook.add_format({
            'font_size': 10,
            'border': 1,
            'align': 'right',
            'num_format': '#,##0'
        })

        cell_text_format = workbook.add_format({
            'font_size': 10,
            'border': 1,
            'align': 'left'
        })

        total_format = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'border': 1,
            'align': 'right',
            'bg_color': '#F0F0F0',
            'num_format': '#,##0'
        })

        total_text_format = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'border': 1,
            'align': 'left',
            'bg_color': '#F0F0F0'
        })

        # Get all unique months from the data
        all_months = set()
        for line_data in data['monthly_data']:
            for month_name in line_data['monthly_transactions'].keys():
                all_months.add(month_name)

        # Create a sheet for each month
        for month_name in sorted(all_months):
            # Check if this month has any transactions across all budget lines
            has_transactions = False
            for line_data in data['monthly_data']:
                transactions = line_data['monthly_transactions'].get(month_name, {})
                if transactions.get('encaissement') or transactions.get('execution'):
                    has_transactions = True
                    break

            # Skip this month if no transactions
            if not has_transactions:
                continue

            worksheet = workbook.add_worksheet(month_name)

            # Set column widths
            worksheet.set_column('A:A', 15)  # Mois
            worksheet.set_column('B:B', 40)  # LIBELLE
            worksheet.set_column('C:C', 18)  # ENCAISSEMENT
            worksheet.set_column('D:D', 18)  # EXECUTION
            worksheet.set_column('E:E', 18)  # SOLDE

            row = 0

            # Process each budget line for this month
            for line_data in data['monthly_data']:
                transactions = line_data['monthly_transactions'].get(month_name, {})

                # Skip if no transactions for this month
                if not transactions.get('encaissement') and not transactions.get('execution'):
                    continue

                # Rubrique header
                worksheet.merge_range(row, 0, row, 4, line_data['rubrique'], rubrique_format)
                row += 1

                # Credit annuel
                worksheet.merge_range(row, 0, row, 4,
                    f"CREDIT ANNUEL ACCORDE: {line_data['credit_annuel']:,.0f}",
                    credit_format)
                row += 2

                # Column headers
                worksheet.write(row, 0, 'Mois', column_header_format)
                worksheet.write(row, 1, 'LIBELLE', column_header_format)
                worksheet.write(row, 2, 'ENCAISSEMENT', column_header_format)
                worksheet.write(row, 3, 'EXECUTION', column_header_format)
                worksheet.write(row, 4, 'SOLDE', column_header_format)
                row += 1

                # Track totals and running balance
                total_encaissement = 0
                total_execution = 0
                solde = 0

                # Encaissement row
                for enc in transactions.get('encaissement', []):
                    worksheet.write(row, 0, month_name, cell_text_format)
                    worksheet.write(row, 1, enc['libelle'], cell_text_format)
                    worksheet.write(row, 2, enc['amount'], cell_format)
                    worksheet.write(row, 3, '', cell_text_format)
                    solde += enc['amount']
                    total_encaissement += enc['amount']
                    worksheet.write(row, 4, solde, cell_format)
                    row += 1

                # Execution rows
                for exec_line in transactions.get('execution', []):
                    worksheet.write(row, 0, '', cell_text_format)
                    worksheet.write(row, 1, exec_line['libelle'], cell_text_format)
                    worksheet.write(row, 2, '', cell_text_format)
                    worksheet.write(row, 3, exec_line['amount'], cell_format)
                    solde -= exec_line['amount']
                    total_execution += exec_line['amount']
                    worksheet.write(row, 4, solde, cell_format)
                    row += 1

                # Total row
                worksheet.write(row, 0, '', total_text_format)
                worksheet.write(row, 1, 'TOTAL', total_text_format)
                worksheet.write(row, 2, total_encaissement, total_format)
                worksheet.write(row, 3, total_execution, total_format)
                worksheet.write(row, 4, solde, total_format)
                row += 3  # Add spacing between budget lines

    def generate_excel_report(self, wizard, data):
        """Generate Excel report with xlsxwriter"""

        # Create workbook in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Rapport Budget')

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#D3D3D3',
            'border': 1
        })

        column_header_format = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#F0F0F0',
            'border': 1,
            'text_wrap': True
        })

        cell_format = workbook.add_format({
            'font_size': 10,
            'border': 1,
            'align': 'right',
            'num_format': '#,##0.00'
        })

        cell_text_format = workbook.add_format({
            'font_size': 10,
            'border': 1,
            'align': 'left'
        })

        percent_format = workbook.add_format({
            'font_size': 10,
            'border': 1,
            'align': 'right',
            'num_format': '0.00"%"'
        })

        total_format = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'border': 1,
            'align': 'right',
            'bg_color': '#F0F0F0',
            'num_format': '#,##0.00'
        })

        total_text_format = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'border': 1,
            'align': 'left',
            'bg_color': '#F0F0F0'
        })

        # Set column widths
        worksheet.set_column('A:A', 30)  # Rubriques
        worksheet.set_column('B:F', 18)  # Numeric columns
        worksheet.set_column('G:G', 15)  # Taux

        # Report title
        worksheet.merge_range('A1:G1', 'RAPPORT D\'EXÉCUTION BUDGÉTAIRE', header_format)
        worksheet.merge_range('A2:G2', data['budget_name'], header_format)

        # Period info
        period_text = f"Période: {data['date_from'].strftime('%d/%m/%Y')} au {data['date_to'].strftime('%d/%m/%Y')}"
        worksheet.merge_range('A3:G3', period_text, header_format)

        # Column headers (row 4, 0-indexed row 3)
        headers = [
            'Rubriques budgétaires',
            'Crédit annuel accordé',
            'Encaissement',
            'Exécution',
            'Solde Théorique annuel à engager',
            'Solde Réel',
            'Taux de réalisation'
        ]

        for col, header in enumerate(headers):
            worksheet.write(4, col, header, column_header_format)

        # Data rows
        row = 5
        for line in data['lines']:
            worksheet.write(row, 0, line['rubrique'], cell_text_format)
            worksheet.write(row, 1, line['credit_annuel'], cell_format)
            worksheet.write(row, 2, line['encaissement'], cell_format)
            worksheet.write(row, 3, line['execution'], cell_format)
            worksheet.write(row, 4, line['solde_theorique'], cell_format)
            worksheet.write(row, 5, line['solde_reel'], cell_format)
            worksheet.write(row, 6, line['taux_realisation'], percent_format)
            row += 1

        # Total row
        worksheet.write(row, 0, 'TOTAL', total_text_format)
        worksheet.write(row, 1, data['total_credit'], total_format)
        worksheet.write(row, 2, data['total_encaissement'], total_format)
        worksheet.write(row, 3, data['total_execution'], total_format)
        worksheet.write(row, 4, data['total_solde_theorique'], total_format)
        worksheet.write(row, 5, data['total_solde_reel'], total_format)
        worksheet.write(row, 6, '-', total_text_format)

        # Legend
        row += 2
        legend_format = workbook.add_format({'font_size': 9, 'italic': True})
        worksheet.write(row, 0, 'Légende:', workbook.add_format({'bold': True, 'font_size': 9}))
        row += 1
        worksheet.write(row, 0, '• Solde Théorique = Crédit annuel - Encaissement', legend_format)
        row += 1
        worksheet.write(row, 0, '• Solde Réel = Encaissement - Exécution', legend_format)
        row += 1
        worksheet.write(row, 0, '• Taux de réalisation = (Exécution ÷ Crédit annuel) × 100%', legend_format)

        # Add monthly detail sheet if requested
        if data.get('include_monthly_detail') and data.get('monthly_data'):
            self._add_monthly_sheet(workbook, data)

        # Close workbook
        workbook.close()

        # Get the Excel file content
        excel_file = output.getvalue()
        output.close()

        # Create attachment
        filename = f"Rapport_Budget_{data['budget_name']}_{data['date_from'].strftime('%Y%m%d')}.xlsx"

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(excel_file),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        # Return download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }
