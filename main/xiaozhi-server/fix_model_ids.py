#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pymysql
import sys
import json

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
        print("=" * 60)
        print("Checking Model ID Issues:")
        print("=" * 60)
        
        # First, check the GroqLLM model
        cursor.execute("""
        SELECT id, model_name, model_type 
        FROM ai_model_config 
        WHERE id = 'GroqLLM' OR model_name = 'Groq LLM' OR model_name = 'GroqLLM'
        """)
        
        groq_model = cursor.fetchall()
        print("Groq Model Status:")
        for model in groq_model:
            print(f"  ID: {model[0]}, Name: {model[1]}, Type: {model[2]}")
        
        # Check agents that might be using wrong model IDs
        print("\n" + "=" * 60)
        print("Checking Agent Configurations:")
        print("=" * 60)
        
        cursor.execute("""
        SELECT id, agent_name, llm_model_id, tts_model_id, asr_model_id
        FROM ai_agent
        WHERE llm_model_id = 'Groq LLM' 
           OR llm_model_id = 'GroqLLM'
           OR llm_model_id LIKE '%Groq%'
        """)
        
        agents = cursor.fetchall()
        if agents:
            print(f"Found {len(agents)} agents with Groq LLM:")
            for agent in agents:
                print(f"  Agent: {agent[1]} (ID: {agent[0]})")
                print(f"    LLM Model ID: {agent[2]}")
        
        # Fix the issue - update agents with wrong model IDs
        print("\n" + "=" * 60)
        print("Fixing Model ID References:")
        print("=" * 60)
        
        # Update agents that have "Groq LLM" as model ID to use "GroqLLM"
        cursor.execute("""
        UPDATE ai_agent 
        SET llm_model_id = 'GroqLLM'
        WHERE llm_model_id = 'Groq LLM'
        """)
        
        if cursor.rowcount > 0:
            print(f"✓ Fixed {cursor.rowcount} agents with incorrect LLM model ID")
        
        # Also check and fix any other model ID mismatches
        model_id_fixes = [
            ('Groq LLM', 'GroqLLM'),
            ('EdgeTTS', 'TTS_EdgeTTS'),
            ('Deepgram Speech Recognition', 'Deepgram'),
            # Add more mappings if needed
        ]
        
        for old_id, new_id in model_id_fixes:
            # Fix LLM model IDs
            cursor.execute("""
            UPDATE ai_agent 
            SET llm_model_id = %s
            WHERE llm_model_id = %s
            """, (new_id, old_id))
            
            if cursor.rowcount > 0:
                print(f"✓ Fixed {cursor.rowcount} agents: LLM '{old_id}' → '{new_id}'")
            
            # Fix TTS model IDs
            cursor.execute("""
            UPDATE ai_agent 
            SET tts_model_id = %s
            WHERE tts_model_id = %s
            """, (new_id, old_id))
            
            if cursor.rowcount > 0:
                print(f"✓ Fixed {cursor.rowcount} agents: TTS '{old_id}' → '{new_id}'")
            
            # Fix ASR model IDs
            cursor.execute("""
            UPDATE ai_agent 
            SET asr_model_id = %s
            WHERE asr_model_id = %s
            """, (new_id, old_id))
            
            if cursor.rowcount > 0:
                print(f"✓ Fixed {cursor.rowcount} agents: ASR '{old_id}' → '{new_id}'")
        
        connection.commit()
        
        # Verify the fix
        print("\n" + "=" * 60)
        print("Verification - Agents using Groq:")
        print("=" * 60)
        
        cursor.execute("""
        SELECT a.agent_name, a.llm_model_id, m.model_name
        FROM ai_agent a
        LEFT JOIN ai_model_config m ON a.llm_model_id = m.id
        WHERE a.llm_model_id LIKE '%Groq%' OR m.model_name LIKE '%Groq%'
        """)
        
        results = cursor.fetchall()
        if results:
            for result in results:
                print(f"Agent: {result[0]}")
                print(f"  LLM Model ID: {result[1]}")
                print(f"  Model Name: {result[2] or 'NOT FOUND'}")
        else:
            print("No agents using Groq models found.")
        
        # Check all model configs to ensure IDs match
        print("\n" + "=" * 60)
        print("All Model Configurations:")
        print("=" * 60)
        
        cursor.execute("""
        SELECT id, model_name, model_type
        FROM ai_model_config
        WHERE model_type = 'LLM'
        ORDER BY model_name
        """)
        
        print(f"{'ID':<30} {'Name':<30} {'Type':<10}")
        print("-" * 70)
        for model in cursor.fetchall():
            print(f"{model[0]:<30} {model[1]:<30} {model[2]:<10}")
            
finally:
    connection.close()