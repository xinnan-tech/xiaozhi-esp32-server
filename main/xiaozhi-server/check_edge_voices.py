#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pymysql
import json
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
        # Check EdgeTTS voices
        print("=" * 60)
        print("Current EdgeTTS Voices in Database:")
        print("=" * 60)
        
        # First, find the EdgeTTS model ID
        cursor.execute("""
        SELECT id, model_name 
        FROM ai_model_config 
        WHERE model_name LIKE '%Edge%' AND model_type = 'tts'
        """)
        edge_model = cursor.fetchone()
        
        if edge_model:
            print(f"EdgeTTS Model: {edge_model[1]} (ID: {edge_model[0]})")
            
            # Now get all voices for EdgeTTS
            cursor.execute("""
            SELECT id, name, tts_voice, languages, remark
            FROM ai_tts_voice 
            WHERE tts_model_id = %s
            ORDER BY name
            """, (edge_model[0],))
            
            voices = cursor.fetchall()
            
            print(f"\nFound {len(voices)} EdgeTTS voices:")
            print("-" * 60)
            
            for voice in voices:
                print(f"ID: {voice[0]}")
                print(f"  Name: {voice[1]}")
                print(f"  TTS Voice: {voice[2]}")
                print(f"  Languages: {voice[3]}")
                if voice[4]:
                    print(f"  Remark: {voice[4]}")
                print()
            
            # Translate Chinese voice names to English
            print("=" * 60)
            print("Translating Chinese voice names to English...")
            print("=" * 60)
            
            # Common EdgeTTS voice translations (preserving the actual voice IDs)
            voice_translations = [
                # Female voices
                ("EdgeTTS女声-晓晓", "EdgeTTS Female - Xiaoxiao"),
                ("EdgeTTS女声-晓伊", "EdgeTTS Female - Xiaoyi"),
                ("EdgeTTS女声-晓双", "EdgeTTS Female - Xiaoshuang"),
                ("EdgeTTS女声-晓萱", "EdgeTTS Female - Xiaoxuan"),
                ("EdgeTTS女声-晓颜", "EdgeTTS Female - Xiaoyan"),
                ("EdgeTTS女声-晓悠", "EdgeTTS Female - Xiaoyou"),
                ("EdgeTTS女声-云夏", "EdgeTTS Female - Yunxia"),
                ("EdgeTTS女声-云燕", "EdgeTTS Female - Yunyan"),
                
                # Male voices
                ("EdgeTTS男声-云健", "EdgeTTS Male - Yunjian"),
                ("EdgeTTS男声-云泽", "EdgeTTS Male - Yunze"),
                ("EdgeTTS男声-云希", "EdgeTTS Male - Yunxi"),
                ("EdgeTTS男声-云扬", "EdgeTTS Male - Yunyang"),
                ("EdgeTTS男声-晓辰", "EdgeTTS Male - Xiaochen"),
                
                # English voices (if any have Chinese labels)
                ("EdgeTTS女声-Jenny", "EdgeTTS Female - Jenny"),
                ("EdgeTTS女声-Aria", "EdgeTTS Female - Aria"),
                ("EdgeTTS男声-Guy", "EdgeTTS Male - Guy"),
                ("EdgeTTS男声-Davis", "EdgeTTS Male - Davis"),
                
                # Generic translations
                ("女声", "Female"),
                ("男声", "Male"),
                ("儿童声", "Child"),
                ("中文", "Chinese"),
                ("英文", "English"),
            ]
            
            updated_count = 0
            for old_name, new_name in voice_translations:
                cursor.execute("""
                UPDATE ai_tts_voice 
                SET name = %s 
                WHERE name = %s AND tts_model_id = %s
                """, (new_name, old_name, edge_model[0]))
                
                if cursor.rowcount > 0:
                    print(f"✓ Updated: '{old_name}' → '{new_name}'")
                    updated_count += cursor.rowcount
            
            # Also update any remaining Chinese characters in voice names
            cursor.execute("""
            SELECT id, name 
            FROM ai_tts_voice 
            WHERE tts_model_id = %s 
            AND (name LIKE '%女%' OR name LIKE '%男%' OR name LIKE '%声%' OR name LIKE '%中文%' OR name LIKE '%英文%')
            """, (edge_model[0],))
            
            remaining_chinese = cursor.fetchall()
            if remaining_chinese:
                print("\nUpdating remaining Chinese characters in voice names:")
                for voice_id, voice_name in remaining_chinese:
                    new_name = voice_name
                    new_name = new_name.replace("女声", "Female")
                    new_name = new_name.replace("男声", "Male")
                    new_name = new_name.replace("儿童声", "Child")
                    new_name = new_name.replace("中文", "Chinese")
                    new_name = new_name.replace("英文", "English")
                    new_name = new_name.replace("语音", "Voice")
                    
                    if new_name != voice_name:
                        cursor.execute("""
                        UPDATE ai_tts_voice 
                        SET name = %s 
                        WHERE id = %s
                        """, (new_name, voice_id))
                        print(f"✓ Updated: '{voice_name}' → '{new_name}'")
                        updated_count += 1
            
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
            SELECT id, name, tts_voice, languages
            FROM ai_tts_voice 
            WHERE tts_model_id = %s
            ORDER BY name
            """, (edge_model[0],))
            
            for voice in cursor.fetchall():
                print(f"Name: {voice[1]} | Voice ID: {voice[2]} | Lang: {voice[3]}")
        else:
            print("EdgeTTS model not found in database!")
            
finally:
    connection.close()