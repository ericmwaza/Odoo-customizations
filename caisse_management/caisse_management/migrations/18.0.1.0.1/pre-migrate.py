# -*- coding: utf-8 -*-

def migrate(cr, version):
    """Pre-migration script to handle request_type field change"""

    # Check if the old request_type column exists
    cr.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name='caisse_request'
        AND column_name='request_type'
        AND data_type='character varying'
    """)

    if cr.fetchone():
        # Temporarily rename the old column to preserve data
        cr.execute("""
            ALTER TABLE caisse_request
            RENAME COLUMN request_type TO request_type_old
        """)
