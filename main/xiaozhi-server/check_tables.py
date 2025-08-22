import pymysql

# Database connection
connection = pymysql.connect(
    host='nozomi.proxy.rlwy.net',
    port=25037,
    user='root',
    password='OcaVNLKcwNdyElfaeUPqvvfYZiiEHgdm',
    database='railway',
    charset='utf8mb4'
)

try:
    with connection.cursor() as cursor:
        # Show all tables
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        print("=" * 60)
        print("Tables in Railway database:")
        print("=" * 60)
        for table in tables:
            print(f"- {table[0]}")
        
        # Check for model-related tables
        print("\n" + "=" * 60)
        print("Checking model/config related tables:")
        print("=" * 60)
        
        for table in tables:
            table_name = table[0]
            if 'model' in table_name.lower() or 'config' in table_name.lower() or 'tts' in table_name.lower():
                cursor.execute(f"DESCRIBE {table_name}")
                columns = cursor.fetchall()
                print(f"\nTable: {table_name}")
                print("Columns:")
                for col in columns:
                    print(f"  - {col[0]} ({col[1]})")
                    
finally:
    connection.close()