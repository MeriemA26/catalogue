# sync_to_sql.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'catalogue_project.settings')
django.setup()

from catalogue_app.sql_sync import SQLServerSync

def main():
    sql_sync = SQLServerSync()
    sql_sync.sync_all()

if __name__ == '__main__':
    main()