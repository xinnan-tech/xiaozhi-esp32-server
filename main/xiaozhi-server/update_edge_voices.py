#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pymysql
import sys

# Set UTF-8 encoding for output
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

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
        # First check the column size
        cursor.execute("""
        SELECT COLUMN_NAME, CHARACTER_MAXIMUM_LENGTH 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = 'railway' 
        AND TABLE_NAME = 'ai_tts_voice' 
        AND COLUMN_NAME = 'name'
        """)
        
        col_info = cursor.fetchone()
        if col_info:
            print(f"Column 'name' max length: {col_info[1]} characters")
        
        # Find EdgeTTS model
        cursor.execute("""
        SELECT id, model_name 
        FROM ai_model_config 
        WHERE model_name LIKE '%Edge%' AND model_type = 'tts'
        """)
        edge_model = cursor.fetchone()
        
        if edge_model:
            print(f"\nEdgeTTS Model: {edge_model[1]} (ID: {edge_model[0]})")
            
            # Get all EdgeTTS voices
            cursor.execute("""
            SELECT id, name, tts_voice 
            FROM ai_tts_voice 
            WHERE tts_model_id = %s
            ORDER BY name
            """, (edge_model[0],))
            
            voices = cursor.fetchall()
            
            print(f"\n" + "=" * 60)
            print("Updating EdgeTTS Voice Names (keeping them short):")
            print("=" * 60)
            
            # Shorter translations to fit within 20 characters
            voice_translations = [
                # Female voices - keep under 20 chars
                ("EdgeTTS女声-晓晓", "Xiaoxiao"),
                ("EdgeTTS女声-晓伊", "Xiaoyi"),
                ("EdgeTTS女声-晓双", "Xiaoshuang"),
                ("EdgeTTS女声-晓萱", "Xiaoxuan"),
                ("EdgeTTS女声-晓颜", "Xiaoyan"),
                ("EdgeTTS女声-晓悠", "Xiaoyou"),
                ("EdgeTTS女声-云夏", "Yunxia"),
                ("EdgeTTS女声-云燕", "Yunyan"),
                ("EdgeTTS女声-辽宁小贝", "Liaoning Xiaobei"),
                ("EdgeTTS女声-陕西小妮", "Shaanxi Xiaoni"),
                ("EdgeTTS女声-香港海佳", "HK HiuGaai"),
                ("EdgeTTS女声-香港海曼", "HK HiuMaan"),
                
                # Male voices - keep under 20 chars
                ("EdgeTTS男声-云健", "Yunjian"),
                ("EdgeTTS男声-云泽", "Yunze"),
                ("EdgeTTS男声-云希", "Yunxi"),
                ("EdgeTTS男声-云扬", "Yunyang"),
                ("EdgeTTS男声-云夏", "Yunxia"),
                ("EdgeTTS男声-晓辰", "Xiaochen"),
                ("EdgeTTS男声-香港万龙", "HK WanLung"),
                
                # English voices
                ("EdgeTTS女声-Jenny", "Jenny"),
                ("EdgeTTS女声-Aria", "Aria"),
                ("EdgeTTS男声-Guy", "Guy"),
                ("EdgeTTS男声-Davis", "Davis"),
            ]
            
            updated_count = 0
            for old_name, new_name in voice_translations:
                # Make sure new name is not too long
                if len(new_name) <= 20:
                    cursor.execute("""
                    UPDATE ai_tts_voice 
                    SET name = %s 
                    WHERE name = %s AND tts_model_id = %s
                    """, (new_name, old_name, edge_model[0]))
                    
                    if cursor.rowcount > 0:
                        print(f"✓ Updated: '{old_name}' → '{new_name}'")
                        updated_count += cursor.rowcount
                else:
                    print(f"⚠️ Skipped (too long): '{new_name}' ({len(new_name)} chars)")
            
            connection.commit()
            
            if updated_count > 0:
                print(f"\n✅ Successfully updated {updated_count} voice names!")
            else:
                print("\n⚠️ No voice names needed updating.")
            
            # Show final results
            print("\n" + "=" * 60)
            print("Updated EdgeTTS Voices:")
            print("=" * 60)
            
            cursor.execute("""
            SELECT name, tts_voice, languages
            FROM ai_tts_voice 
            WHERE tts_model_id = %s
            ORDER BY name
            """, (edge_model[0],))
            
            print(f"{'Name':<20} {'Voice ID':<30} {'Languages':<20}")
            print("-" * 70)
            for voice in cursor.fetchall():
                print(f"{voice[0]:<20} {voice[1]:<30} {voice[2] or 'N/A':<20}")
        else:
            print("EdgeTTS model not found in database!")
            
finally:
    connection.close()