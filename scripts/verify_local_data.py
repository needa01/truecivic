"""Verify local SQLite database has data."""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'parliament_explorer_local.db'

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Count bills
cursor.execute('SELECT COUNT(*) FROM bills')
total_bills = cursor.fetchone()[0]
print(f'📊 Total bills: {total_bills}')

# Sample bills
cursor.execute('SELECT number, title_en FROM bills LIMIT 5')
print('\n📋 Sample bills:')
for row in cursor.fetchall():
    print(f'  • {row[0]}: {row[1][:80]}...')

# Count politicians
cursor.execute('SELECT COUNT(*) FROM politicians')
total_politicians = cursor.fetchone()[0]
print(f'\n👥 Total politicians: {total_politicians}')

# Count other entities
for table in ['votes', 'debates', 'committees']:
    cursor.execute(f'SELECT COUNT(*) FROM {table}')
    count = cursor.fetchone()[0]
    print(f'📁 Total {table}: {count}')

conn.close()
