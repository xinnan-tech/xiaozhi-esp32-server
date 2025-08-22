import pymysql
import json

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
        # Check TTS models
        print("=" * 60)
        print("TTS Models in Database:")
        print("=" * 60)
        
        sql = """
        SELECT id, model_name, model_type, config_json 
        FROM model_config 
        WHERE model_type = 'tts' OR model_name LIKE '%Edge%' OR model_name LIKE '%语音%'
        ORDER BY model_name
        """
        cursor.execute(sql)
        results = cursor.fetchall()
        
        for row in results:
            print(f"\nID: {row[0]}")
            print(f"Model Name: {row[1]}")
            print(f"Model Type: {row[2]}")
            if row[3]:
                config = json.loads(row[3])
                print(f"Config Type: {config.get('type', 'N/A')}")
        
        # Update the Chinese text to English
        print("\n" + "=" * 60)
        print("Updating Chinese model names to English...")
        print("=" * 60)
        
        updates = [
            ("Edge语音合成", "Edge TTS"),
            ("百度语音合成", "Baidu TTS"),
            ("阿里语音合成", "Ali TTS"),
            ("腾讯语音合成", "Tencent TTS"),
            ("科大讯飞语音合成", "iFlytek TTS")
        ]
        
        for old_name, new_name in updates:
            sql = "UPDATE model_config SET model_name = %s WHERE model_name = %s"
            cursor.execute(sql, (new_name, old_name))
            if cursor.rowcount > 0:
                print(f"✓ Updated: '{old_name}' → '{new_name}'")
        
        connection.commit()
        print("\n✅ All TTS model names have been updated to English!")
        
        # Verify the changes
        print("\n" + "=" * 60)
        print("Updated TTS Models:")
        print("=" * 60)
        
        cursor.execute("""
        SELECT id, model_name 
        FROM model_config 
        WHERE model_type = 'tts'
        ORDER BY model_name
        """)
        
        for row in cursor.fetchall():
            print(f"ID: {row[0]}, Name: {row[1]}")
            
finally:
    connection.close()