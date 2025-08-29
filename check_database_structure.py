#!/usr/bin/env python3
"""
Script to check the ai_model_provider table structure and existing ASR services
"""

import mysql.connector
from mysql.connector import Error
import json
from tabulate import tabulate

def connect_to_database():
    """Connect to the Railway MySQL database"""
    try:
        connection = mysql.connector.connect(
            host='nozomi.proxy.rlwy.net',
            port=25037,
            database='railway',
            user='root',
            password='OcaVNLKcwNdyElfaeUPqvvfYZiiEHgdm',
            charset='utf8mb4',
            use_unicode=True,
            ssl_disabled=True
        )
        
        if connection.is_connected():
            print("Successfully connected to Railway MySQL database")
            return connection
            
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def get_table_structure(connection, table_name):
    """Get the structure of a table"""
    cursor = connection.cursor()
    try:
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()
        
        print(f"\nStructure of table '{table_name}':")
        headers = ["Field", "Type", "Null", "Key", "Default", "Extra"]
        print(tabulate(columns, headers=headers, tablefmt="grid"))
        
        return columns
        
    except Error as e:
        print(f"Error getting table structure: {e}")
        return None
    finally:
        cursor.close()

def get_existing_asr_providers(connection):
    """Get all existing ASR providers"""
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT id, model_type, provider_code, name, LENGTH(id) as id_length
            FROM ai_model_provider 
            WHERE model_type = 'ASR' 
            ORDER BY id
        """)
        providers = cursor.fetchall()
        
        print(f"\nExisting ASR providers:")
        headers = ["ID", "Model Type", "Provider Code", "Name", "ID Length"]
        print(tabulate(providers, headers=headers, tablefmt="grid"))
        
        return providers
        
    except Error as e:
        print(f"Error getting ASR providers: {e}")
        return None
    finally:
        cursor.close()

def get_existing_asr_configs(connection):
    """Get all existing ASR model configurations"""
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT id, model_type, model_code, model_name, LENGTH(id) as id_length
            FROM ai_model_config 
            WHERE model_type = 'ASR' 
            ORDER BY id
        """)
        configs = cursor.fetchall()
        
        print(f"\nExisting ASR model configurations:")
        headers = ["ID", "Model Type", "Model Code", "Model Name", "ID Length"]
        print(tabulate(configs, headers=headers, tablefmt="grid"))
        
        return configs
        
    except Error as e:
        print(f"Error getting ASR configs: {e}")
        return None
    finally:
        cursor.close()

def analyze_id_constraints(providers, configs):
    """Analyze ID length constraints"""
    print(f"\nID Length Analysis:")
    
    if providers:
        provider_lengths = [row[4] for row in providers]  # ID length is 5th column
        print(f"Provider ID lengths: {provider_lengths}")
        print(f"Max provider ID length: {max(provider_lengths)}")
        print(f"Min provider ID length: {min(provider_lengths)}")
        
    if configs:
        config_lengths = [row[4] for row in configs]  # ID length is 5th column  
        print(f"Config ID lengths: {config_lengths}")
        print(f"Max config ID length: {max(config_lengths)}")
        print(f"Min config ID length: {min(config_lengths)}")
        
    # Check our proposed ID
    proposed_provider_id = "SYSTEM_ASR_AmazonTranscribeStreaming"
    proposed_config_id = "ASR_AmazonTranscribeStreaming"
    
    print(f"\nOur proposed IDs:")
    print(f"Provider ID: '{proposed_provider_id}' (length: {len(proposed_provider_id)})")
    print(f"Config ID: '{proposed_config_id}' (length: {len(proposed_config_id)})")
    
    if providers and len(proposed_provider_id) > max(provider_lengths):
        print(f"WARNING: Proposed provider ID is longer than existing max ({max(provider_lengths)})")
        
    if configs and len(proposed_config_id) > max(config_lengths):
        print(f"WARNING: Proposed config ID is longer than existing max ({max(config_lengths)})")

def suggest_shorter_ids():
    """Suggest shorter ID alternatives"""
    print(f"\nSuggested shorter IDs:")
    
    alternatives = [
        ("SYSTEM_ASR_AmazonTS", "ASR_AmazonTS"),
        ("SYSTEM_ASR_AwsTranscribe", "ASR_AwsTranscribe"), 
        ("SYSTEM_ASR_AmazonStream", "ASR_AmazonStream"),
        ("SYSTEM_ASR_AWSStream", "ASR_AWSStream"),
    ]
    
    headers = ["Provider ID", "Config ID", "Provider Length", "Config Length"]
    rows = []
    for provider_id, config_id in alternatives:
        rows.append([provider_id, config_id, len(provider_id), len(config_id)])
    
    print(tabulate(rows, headers=headers, tablefmt="grid"))

def main():
    print("Checking xiaozhi database structure for Amazon Transcribe integration")
    print("=" * 70)
    
    # Connect to database
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        # Get table structures
        print("\n" + "="*50)
        provider_structure = get_table_structure(connection, "ai_model_provider")
        
        print("\n" + "="*50) 
        config_structure = get_table_structure(connection, "ai_model_config")
        
        # Get existing ASR services
        print("\n" + "="*50)
        providers = get_existing_asr_providers(connection)
        
        print("\n" + "="*50)
        configs = get_existing_asr_configs(connection)
        
        # Analyze constraints
        print("\n" + "="*50)
        analyze_id_constraints(providers, configs)
        
        # Suggest alternatives
        print("\n" + "="*50)
        suggest_shorter_ids()
        
    finally:
        if connection.is_connected():
            connection.close()
            print(f"\nMySQL connection closed")

if __name__ == "__main__":
    main()