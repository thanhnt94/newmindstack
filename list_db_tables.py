"""
Script to list all database tables and their structure.
"""
import sqlite3

db_path = r'C:\Code\MindStack\database\mindstack_new.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

output = []
output.append('# DATABASE SCHEMA REVIEW')
output.append(f'Total: {len(tables)} tables\n')

for table in tables:
    table_name = table[0]
    cursor.execute(f'PRAGMA table_info({table_name})')
    columns = cursor.fetchall()
    
    # Count rows
    cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
    row_count = cursor.fetchone()[0]
    
    output.append(f'## {table_name} ({row_count} rows)')
    output.append('| Column | Type | Constraints |')
    output.append('|--------|------|-------------|')
    for col in columns:
        col_id, name, dtype, notnull, default, pk = col
        constraints = []
        if pk:
            constraints.append('PK')
        if notnull:
            constraints.append('NOT NULL')
        if default:
            constraints.append(f'DEFAULT {default}')
        output.append(f'| {name} | {dtype} | {", ".join(constraints) if constraints else "-"} |')
    output.append('')

conn.close()

# Write to file
with open('db_schema_review.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print(f'Schema written to db_schema_review.md')
print(f'Total tables: {len(tables)}')
