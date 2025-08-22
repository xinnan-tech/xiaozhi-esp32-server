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
        print("=" * 60)
        print("Fixing Groq Model ID:")
        print("=" * 60)
        
        # First check current status
        cursor.execute("""
        SELECT id, model_name, model_type 
        FROM ai_model_config 
        WHERE id = 'GroqLLM' OR id = 'Groq LLM' OR model_name LIKE '%Groq%'
        """)
        
        current_model = cursor.fetchall()
        print("Current Groq Model:")
        for model in current_model:
            print(f"  ID: {model[0]}, Name: {model[1]}, Type: {model[2]}")
        
        # Update the model ID from GroqLLM to Groq LLM
        print("\nUpdating model ID from 'GroqLLM' to 'Groq LLM'...")
        
        cursor.execute("""
        UPDATE ai_model_config 
        SET id = 'Groq LLM'
        WHERE id = 'GroqLLM'
        """)
        
        if cursor.rowcount > 0:
            print(f"✓ Updated model ID: 'GroqLLM' → 'Groq LLM'")
        
        # Also update any agent references
        cursor.execute("""
        UPDATE ai_agent 
        SET llm_model_id = 'Groq LLM'
        WHERE llm_model_id = 'GroqLLM'
        """)
        
        if cursor.rowcount > 0:
            print(f"✓ Updated {cursor.rowcount} agent references: 'GroqLLM' → 'Groq LLM'")
        
        connection.commit()
        
        # Verify the changes
        print("\n" + "=" * 60)
        print("Verification:")
        print("=" * 60)
        
        cursor.execute("""
        SELECT id, model_name, model_type 
        FROM ai_model_config 
        WHERE id = 'Groq LLM' OR model_name LIKE '%Groq%'
        """)
        
        updated_model = cursor.fetchall()
        print("Updated Groq Model:")
        for model in updated_model:
            print(f"  ID: {model[0]}, Name: {model[1]}, Type: {model[2]}")
        
        # Check agents using this model
        cursor.execute("""
        SELECT agent_name, llm_model_id
        FROM ai_agent
        WHERE llm_model_id = 'Groq LLM'
        """)
        
        agents = cursor.fetchall()
        if agents:
            print(f"\nAgents using Groq LLM ({len(agents)} total):")
            for agent in agents:
                print(f"  - {agent[0]}: {agent[1]}")
        
        print("\n✅ Model ID successfully changed to 'Groq LLM'")
        print("✅ The Manager API should now work without errors")
            
finally:
    connection.close()