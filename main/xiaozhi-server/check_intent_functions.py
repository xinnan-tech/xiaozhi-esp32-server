#!/usr/bin/env python3
"""
Check how Intent function_call gets its functions list from manager-api
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

def check_intent_function_call_config(connection):
    """Check the Intent function_call configuration"""
    cursor = connection.cursor()
    
    print("=== INTENT FUNCTION_CALL CONFIGURATION ===\n")
    
    # Check the Intent_function_call config
    cursor.execute("""
    SELECT id, model_name, config_json, remark
    FROM ai_model_config 
    WHERE id = 'Intent_function_call'
    """)
    result = cursor.fetchone()
    
    if result:
        config_id, model_name, config_json, remark = result
        print(f"Configuration ID: {config_id}")
        print(f"Model Name: {model_name}")
        
        try:
            config = json.loads(config_json) if config_json else {}
            print(f"Current Config:")
            print(json.dumps(config, indent=2))
            
            # Check if functions are defined in config
            if 'functions' in config:
                functions = config['functions']
                print(f"\nFunctions in config: {functions}")
            else:
                print("\nNo 'functions' key found in Intent config - uses plugin mappings instead")
                
        except json.JSONDecodeError as e:
            print(f"Error parsing config JSON: {e}")
            print(f"Raw config: {config_json}")
            
        if remark:
            print(f"\nRemark: {remark}")
    else:
        print("Intent_function_call configuration not found!")
        return False
    
    cursor.close()
    return True

def check_how_functions_are_loaded(connection):
    """Check how functions are loaded for agents"""
    cursor = connection.cursor()
    
    print("\n=== HOW FUNCTIONS ARE LOADED FOR AGENTS ===\n")
    
    # Check a specific agent and its plugin mappings
    cursor.execute("""
    SELECT a.id, a.agent_name, a.intent_model_id
    FROM ai_agent a
    WHERE a.agent_name LIKE '%Cheeko%'
    LIMIT 1
    """)
    agent_result = cursor.fetchone()
    
    if not agent_result:
        print("No Cheeko agent found")
        return
    
    agent_id, agent_name, intent_model = agent_result
    print(f"Checking agent: {agent_name} ({agent_id})")
    print(f"Intent model: {intent_model}")
    
    # Get plugins for this agent
    print(f"\nPlugins mapped to this agent:")
    cursor.execute("""
    SELECT p.id, p.provider_code, p.name, m.param_info
    FROM ai_agent_plugin_mapping m
    JOIN ai_model_provider p ON p.id = m.plugin_id
    WHERE m.agent_id = %s AND p.model_type = 'Plugin'
    ORDER BY p.provider_code
    """, (agent_id,))
    
    plugins = cursor.fetchall()
    
    if plugins:
        available_functions = []
        for plugin in plugins:
            provider_id, provider_code, provider_name, param_info = plugin
            available_functions.append(provider_code)
            print(f"  - {provider_code} ({provider_name})")
        
        print(f"\nAvailable functions for this agent: {available_functions}")
        
        # Check specifically for our functions
        expected_functions = ['play_music', 'play_story', 'get_weather', 'get_indian_news_api', 'get_news_from_newsnow']
        missing_functions = []
        present_functions = []
        
        for func in expected_functions:
            if func in available_functions:
                present_functions.append(func)
            else:
                missing_functions.append(func)
        
        print(f"\nFunction Status:")
        print(f"  Present: {present_functions}")
        print(f"  Missing: {missing_functions}")
        
        if missing_functions:
            print(f"\n[WARNING] Missing functions: {missing_functions}")
            print("These functions won't be available when using manager-api config")
        else:
            print(f"\n[OK] All expected functions are available!")
            
    else:
        print("No plugin mappings found for this agent")
    
    cursor.close()

def check_server_config_generation(connection):
    """Check how server config is generated"""
    cursor = connection.cursor()
    
    print("\n=== SERVER CONFIG GENERATION LOGIC ===\n")
    
    # This is what the server likely does when generating config
    print("The server config generation likely works as follows:")
    print("1. Gets basic Intent configuration from ai_model_config")
    print("2. For each agent request, gets plugins from ai_agent_plugin_mapping")
    print("3. Dynamically builds the functions list based on agent's plugins")
    print("")
    print("This means the 'functions' are not in the Intent config itself,")
    print("but are loaded per-agent from the plugin mappings.")
    
    cursor.close()

def main():
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        # Check Intent configuration
        if check_intent_function_call_config(connection):
            # Check how functions are loaded for agents
            check_how_functions_are_loaded(connection)
            # Explain server config generation
            check_server_config_generation(connection)
        
    finally:
        if connection.is_connected():
            connection.close()

if __name__ == "__main__":
    main()