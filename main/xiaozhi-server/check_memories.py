import sqlite3

conn = sqlite3.connect('data/xiaozhi_memory.db')
cursor = conn.cursor()

# Get column names
cursor.execute('PRAGMA table_info(memories)')
cols = [c[1] for c in cursor.fetchall()]

# Get all records
cursor.execute('SELECT * FROM memories')
rows = cursor.fetchall()

print(f'Total records: {len(rows)}')
print()

if rows:
    for row in rows:
        print(dict(zip(cols, row)))
        print('-' * 50)
else:
    print('No memories found. Database is empty.')
    print()
    print('Memories will be saved after the first conversation ends.')

conn.close()
