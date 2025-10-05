# -*- coding: utf-8 -*-

from odoo import models, api
from odoo.exceptions import UserError
import io
import base64
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        """Override to generate custom PDF for caisse summary report"""
        # Check if this is our custom report
        if isinstance(report_ref, str):
            report_name = report_ref
        else:
            report_name = report_ref.report_name if hasattr(report_ref, 'report_name') else str(report_ref)

        # Check for our custom report
        if 'report_caisse_summary' in report_name or report_name == 'caisse_management.report_caisse_summary':
            return self._render_caisse_summary_pdf(res_ids, data)

        # Otherwise use standard rendering
        return super()._render_qweb_pdf(report_ref, res_ids, data)

    def _render_caisse_summary_pdf(self, res_ids, data):
        """Generate PDF using ReportLab for caisse summary"""
        if not res_ids:
            raise UserError("No records to print")

        # Get the caisse config record
        configs = self.env['caisse.config'].browse(res_ids)

        # Create PDF in memory
        buffer = io.BytesIO()

        # Generate PDF for each config
        for config in configs:
            self._generate_caisse_pdf(buffer, config, data)

        pdf_content = buffer.getvalue()
        buffer.close()

        return pdf_content, 'pdf'

    def _generate_caisse_pdf(self, buffer, config, data):
        """Generate the actual PDF content using ReportLab"""
        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm,
        )

        # Container for the 'Flowable' objects
        elements = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.black,
            alignment=TA_CENTER,
            spaceAfter=12,
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.black,
            spaceAfter=6,
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.black,
        )

        center_style = ParagraphStyle(
            'CustomCenter',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            alignment=TA_CENTER,
        )

        # Add logo at top left if available
        if config.company_id.logo:
            try:
                logo_data = base64.b64decode(config.company_id.logo)
                logo_buffer = io.BytesIO(logo_data)
                logo = Image(logo_buffer, width=60*mm, height=20*mm, kind='proportional')
                logo.hAlign = 'LEFT'
                elements.append(logo)
                elements.append(Spacer(1, 5*mm))
            except Exception as e:
                pass  # Skip logo if there's an error

        # Skip company info - just spacing
        elements.append(Spacer(1, 5*mm))

        # Report title
        title = Paragraph("Rapport Résumé de Caisse", title_style)
        elements.append(title)

        # Date generated
        date_str = datetime.now().strftime('%d/%m/%Y')
        date_para = Paragraph(f"Généré le {date_str}", center_style)
        elements.append(date_para)
        elements.append(Spacer(1, 10*mm))

        # Configuration details - single clean table with responsive formatting
        # Format amounts without currency symbol (add it in header instead)
        currency = config.company_id.currency_id.name

        config_data = [
            ['Journal:', config.journal_id.name, f'Solde ({currency}):', f"{config.current_balance:,.0f}"],
            ['Limite Jour.:', f"{config.daily_disbursement_limit:,.0f}", f'Disponible ({currency}):', f"{config.daily_available_balance:,.0f}"],
        ]

        # Use slightly smaller font and adjusted column widths for better fit
        config_table = Table(config_data, colWidths=[35*mm, 50*mm, 38*mm, 47*mm])
        config_table.setStyle(TableStyle([
            # Grid - thin lines
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),

            # Font
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),  # Labels in bold
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),  # Labels in bold
            ('FONTSIZE', (0, 0), (-1, -1), 9),

            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),

            # Alignment
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),  # Right align amounts

            # Light background for label columns
            ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
            ('BACKGROUND', (2, 0), (2, -1), colors.Color(0.95, 0.95, 0.95)),
        ]))

        elements.append(config_table)
        elements.append(Spacer(1, 8*mm))

        # Get date range from context
        ctx = self.env.context
        date_from_str = ctx.get('date_from')
        date_to_str = ctx.get('date_to')

        if date_from_str and date_to_str:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
        else:
            date_to = datetime.now().date()
            date_from = date_to - timedelta(days=30)

        # Activity section header - simple and clean
        period_text = f"Activité pour la période: {date_from.strftime('%d/%m/%Y')} au {date_to.strftime('%d/%m/%Y')}"
        period_para = Paragraph(f"<b>{period_text}</b>", heading_style)
        elements.append(period_para)
        elements.append(Spacer(1, 3*mm))

        # Get recent requests
        recent_requests = self.env['caisse.request'].search([
            ('company_id', '=', config.company_id.id),
            ('request_date', '>=', date_from),
            ('request_date', '<=', date_to)
        ], order='request_date desc')

        if recent_requests:
            # Activity table header with currency in column name
            activity_data = [
                ['Date', 'Employé', 'Type', f'Montant ({currency})', 'Statut']
            ]

            # State translations
            state_trans = {
                'draft': 'Brouillon',
                'submitted': 'Soumis',
                'manager_approved': 'Approuvé',
                'disbursed': 'Décaissé',
                'rejected': 'Rejeté',
                'cancelled': 'Annulé',
            }

            total_amount = 0
            for req in recent_requests:
                # Get request type name (truncate if too long)
                request_type_name = req.request_type_id.name if req.request_type_id else 'N/A'
                if len(request_type_name) > 18:
                    request_type_name = request_type_name[:15] + '...'

                # Get employee name (truncate if too long)
                employee_name = req.employee_id.name or ''
                if len(employee_name) > 25:
                    employee_name = employee_name[:22] + '...'

                activity_data.append([
                    req.request_date.strftime('%d/%m/%Y') if req.request_date else '',
                    employee_name,
                    request_type_name,
                    f"{req.amount:,.0f}",  # No decimals to save space
                    state_trans.get(req.state, req.state),
                ])
                total_amount += req.amount or 0

            # Add total row
            activity_data.append([
                '', '', 'Total:', f"{total_amount:,.0f}", ''
            ])

            # Adjusted column widths for better fit
            activity_table = Table(activity_data, colWidths=[23*mm, 42*mm, 32*mm, 35*mm, 28*mm])
            activity_table.setStyle(TableStyle([
                # Header with lighter grey
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.9)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 0), (-1, 0), 6),

                # Data rows - thin grey lines, smaller font
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -2), 8),  # Smaller font for data
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),

                # Amount column right aligned
                ('ALIGN', (3, 0), (3, -1), 'RIGHT'),

                # Total row - lighter background
                ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.9, 0.9, 0.9)),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 9),
                ('ALIGN', (2, -1), (2, -1), 'RIGHT'),
                ('ALIGN', (3, -1), (3, -1), 'RIGHT'),
            ]))

            elements.append(activity_table)
        else:
            # No activity message
            no_activity = Paragraph(
                "<b>Aucune activité récente.</b> Il n'y a eu aucune demande dans la période sélectionnée.",
                normal_style
            )
            no_activity_table = Table([[no_activity]], colWidths=[170*mm])
            no_activity_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ]))
            elements.append(no_activity_table)

        # Build PDF
        doc.build(elements)
