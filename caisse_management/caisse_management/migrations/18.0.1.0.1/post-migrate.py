# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID

def migrate(cr, version):
    """Post-migration script to migrate data from old to new request_type field"""

    # Check if we have the old column
    cr.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name='caisse_request'
        AND column_name='request_type_old'
    """)

    if cr.fetchone():
        # Use Odoo ORM to create request types (handles JSON/translate fields properly)
        env = api.Environment(cr, SUPERUSER_ID, {})

        # Map of old codes to new type names
        type_mapping = {
            'advance': 'Avance sur Salaire',
            'petty_cash': 'Petite Caisse',
            'expense': 'Autre Dépense',
            'emergency': "Fonds d'Urgence",
        }

        # Get or create company
        company = env['res.company'].search([], limit=1)
        company_id = company.id if company else None

        # Create request types using ORM
        RequestType = env['caisse.request.type']
        type_ids = {}
        sequence = 10

        for code, name in type_mapping.items():
            # Check if type already exists
            existing_type = RequestType.search([
                ('code', '=', code),
                '|', ('company_id', '=', company_id), ('company_id', '=', False)
            ], limit=1)

            if existing_type:
                type_ids[code] = existing_type.id
            else:
                # Create new type
                new_type = RequestType.create({
                    'name': name,
                    'code': code,
                    'sequence': sequence,
                    'active': True,
                    'company_id': company_id,
                })
                type_ids[code] = new_type.id

            sequence += 10

        # Migrate data from old field to new field using direct SQL
        for code, type_id in type_ids.items():
            cr.execute("""
                UPDATE caisse_request
                SET request_type_id = %s
                WHERE request_type_old = %s
            """, (type_id, code))

        # Drop the old column
        cr.execute("""
            ALTER TABLE caisse_request
            DROP COLUMN IF EXISTS request_type_old
        """)
