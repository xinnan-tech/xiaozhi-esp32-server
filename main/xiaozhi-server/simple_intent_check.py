#!/usr/bin/env python3
"""
Simple check of Intent function_call and agent plugin mappings
"""
import mysql.connector
import json
from mysql.connector import Error

# Database configuration
DB_CONFIG = {
    'host': 'nozomi.proxy.rlwy.net',
    'port': 25037,
    'database': 'railway',
    'user': 'root',
    'password': 'OcaVNLKcwNdyElfaeUPqvvfYZiiEHgdm',
    'ssl_disabled': True,
    'use_unicode': True,
    'charset': 'utf8mb4'
}

def connect_to_database():
    """Connect to the Railway MySQL database"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            print("Connected to database")
            return connection
    except Error as e:
        print(f"Connection error: {e}")
        return None

def main():
    connection = connect_to_database()
    if not connection:
        return
    
    cursor = connection.cursor()
    
    try:
        print("=== INTENT CONFIGURATION ===")
        
        # Check Intent_function_call config
        cursor.execute("SELECT config_json FROM ai_model_config WHERE id = 'Intent_function_call'")
        result = cursor.fetchone()
        
        if result:
            config = json.loads(result[0])
            print(f"Intent config: {config}")
            
            if 'functions' in config:
                print(f"Functions in config: {config['functions']}")
            else:
                print("No functions in Intent config - uses plugin mappings")
        
        print("\n=== AGENT PLUGIN MAPPINGS ===")
        
        # Get a Cheeko agent
        cursor.execute("SELECT id, agent_name FROM ai_agent WHERE agent_name LIKE '%Cheeko%' LIMIT 1")
        agent = cursor.fetchone()
        
        if agent:
            agent_id, agent_name = agent
            print(f"Agent: {agent_name} ({agent_id})")
            
            # Get plugins for this agent
            cursor.execute("""
            SELECT p.provider_code
            FROM ai_agent_plugin_mapping m
            JOIN ai_model_provider p ON p.id = m.plugin_id
            WHERE m.agent_id = %s AND p.model_type = 'Plugin'
            ORDER BY p.provider_code
            """, (agent_id,))
            
            plugins = cursor.fetchall()
            available_functions = [plugin[0] for plugin in plugins]
            print(f"Available functions: {available_functions}")
            
            # Check specific functions
            expected = ['play_music', 'play_story', 'get_weather', 'get_indian_news_api', 'get_news_from_newsnow']
            
            print(f"\nFunction Status:")
            for func in expected:
                status = "OK" if func in available_functions else "MISSING"
                print(f"  {func}: {status}")
            
            missing = [f for f in expected if f not in available_functions]
            if missing:
                print(f"\nMissing functions: {missing}")
                print("These need to be added as plugin mappings to the agent")
            else:
                print(f"\nAll functions are available via plugin mappings!")
        
        print("\n=== EXPLANATION ===")
        print("Server config shows: {'type': 'function_call'}")
        print("Local config shows: functions list")
        print("")
        print("The new architecture:")
        print("1. Intent config only has 'type': 'function_call'")
        print("2. Functions come from ai_agent_plugin_mapping per agent")
        print("3. Server dynamically builds function list for each agent")
        print("4. This allows different agents to have different functions")
        
    finally:
        if connection.is_connected():
            connection.close()

if __name__ == "__main__":
    main()