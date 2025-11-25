# Generated migration for enabling pg_stat_statements extension

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('adbms_demo', '0003_create_materialized_view'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            -- Enable pg_stat_statements extension for query performance tracking
            CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
            """,
            reverse_sql="""
            -- Note: We don't drop the extension on reverse to preserve existing statistics
            -- DROP EXTENSION IF EXISTS pg_stat_statements;
            """
        )
    ]
