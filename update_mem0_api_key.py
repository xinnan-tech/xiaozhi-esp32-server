#!/usr/bin/env python3
"""
Script to update mem0 API key directly in the database
This bypasses the masking issue by directly updating the database
"""

import pymysql
import json
import sys
from datetime import datetime

# Database configuration - from application-dev.yml
DB_CONFIG = {
    'host': 'nozomi.proxy.rlwy.net',     # Railway MySQL host
    'port': 25037,                       # Railway MySQL port
    'user': 'root',                      # Database username
    'password': 'OcaVNLKcwNdyElfaeUPqvvfYZiiEHgdm',  # Database password
    'database': 'railway',               # Database name
    'charset': 'utf8mb4',
    'connect_timeout': 30,               # Connection timeout in seconds
    'read_timeout': 30,
    'write_timeout': 30,
    'autocommit': False,
    'ssl': {'ssl_disabled': False}      # Enable SSL as per JDBC config
}

# The actual mem0 API key
MEM0_API_KEY = "m0-WNBvGhsBGZU1NDKDF42ecLNAgMk0GRaToaKLT0wN"

# Colors for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Print a formatted header"""
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}")

def print_success(text):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def connect_to_database():
    """Connect to the MySQL database with retry logic"""
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(1, max_retries + 1):
        try:
            print_info(f"Connecting to database... (Attempt {attempt}/{max_retries})")
            print_info(f"Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
            
            connection = pymysql.connect(**DB_CONFIG)
            
            # Test the connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            print_success("Successfully connected to database")
            return connection
            
        except pymysql.err.OperationalError as e:
            error_code = e.args[0] if e.args else None
            error_msg = e.args[1] if len(e.args) > 1 else str(e)
            
            if error_code == 2013:
                print_warning(f"Connection lost during query. This might be a network issue.")
            elif error_code == 1045:
                print_error(f"Access denied. Check your username and password.")
                return None
            else:
                print_warning(f"Connection error: {error_msg}")
            
            if attempt < max_retries:
                print_info(f"Retrying in {retry_delay} seconds...")
                import time
                time.sleep(retry_delay)
            else:
                print_error(f"Failed to connect after {max_retries} attempts")
                
        except Exception as e:
            print_error(f"Unexpected error: {str(e)}")
            if attempt < max_retries:
                print_info(f"Retrying in {retry_delay} seconds...")
                import time
                time.sleep(retry_delay)
            else:
                return None
    
    return None

def find_mem0_configs(connection):
    """Find all mem0ai configurations in the database"""
    try:
        with connection.cursor() as cursor:
            # Query to find mem0ai configurations
            query = """
                SELECT id, model_name, config_json 
                FROM ai_model_config 
                WHERE model_type = 'Memory' 
                AND JSON_EXTRACT(config_json, '$.type') = 'mem0ai'
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            if results:
                print_success(f"Found {len(results)} mem0ai configuration(s)")
                for row in results:
                    config_id, model_name, config_json_str = row
                    config_json = json.loads(config_json_str) if config_json_str else {}
                    current_api_key = config_json.get('api_key', '')
                    
                    print_info(f"\nConfiguration ID: {config_id}")
                    print_info(f"Model Name: {model_name}")
                    
                    if current_api_key == "***":
                        print_warning(f"Current API key: {current_api_key} (MASKED)")
                    elif current_api_key == MEM0_API_KEY:
                        print_success(f"Current API key: {current_api_key[:10]}...{current_api_key[-10:]} (Already correct)")
                    elif current_api_key:
                        print_warning(f"Current API key: {current_api_key[:10]}...{current_api_key[-10:] if len(current_api_key) > 20 else current_api_key}")
                    else:
                        print_warning("Current API key: (empty)")
                
                return results
            else:
                print_warning("No mem0ai configurations found")
                return []
                
    except Exception as e:
        print_error(f"Failed to query database: {str(e)}")
        return []

def update_api_keys(connection, configs):
    """Update the API keys for mem0ai configurations"""
    if not configs:
        print_warning("No configurations to update")
        return False
    
    try:
        with connection.cursor() as cursor:
            updated_count = 0
            
            for config_id, model_name, config_json_str in configs:
                config_json = json.loads(config_json_str) if config_json_str else {}
                current_api_key = config_json.get('api_key', '')
                
                # Only update if the API key is different
                if current_api_key != MEM0_API_KEY:
                    print_info(f"\nUpdating configuration: {config_id} ({model_name})")
                    
                    # Update the API key in the JSON
                    config_json['api_key'] = MEM0_API_KEY
                    updated_json = json.dumps(config_json)
                    
                    # Update query
                    update_query = """
                        UPDATE ai_model_config 
                        SET config_json = %s,
                            update_date = NOW()
                        WHERE id = %s
                    """
                    
                    cursor.execute(update_query, (updated_json, config_id))
                    updated_count += 1
                    print_success(f"Updated API key for {model_name}")
                else:
                    print_info(f"\nSkipping {model_name} - API key already correct")
            
            if updated_count > 0:
                connection.commit()
                print_success(f"\n{updated_count} configuration(s) updated successfully")
                return True
            else:
                print_info("\nNo configurations needed updating")
                return True
                
    except Exception as e:
        connection.rollback()
        print_error(f"Failed to update database: {str(e)}")
        return False

def verify_update(connection):
    """Verify that the update was successful"""
    try:
        with connection.cursor() as cursor:
            query = """
                SELECT id, model_name, JSON_EXTRACT(config_json, '$.api_key') as api_key
                FROM ai_model_config 
                WHERE model_type = 'Memory' 
                AND JSON_EXTRACT(config_json, '$.type') = 'mem0ai'
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            print_header("Verification Results")
            all_correct = True
            
            for config_id, model_name, api_key in results:
                # Remove quotes from JSON extracted value
                api_key = api_key.strip('"') if api_key else ''
                
                if api_key == MEM0_API_KEY:
                    print_success(f"{model_name}: API key is correct")
                else:
                    print_error(f"{model_name}: API key is incorrect ({api_key})")
                    all_correct = False
            
            return all_correct
            
    except Exception as e:
        print_error(f"Failed to verify update: {str(e)}")
        return False

def main():
    """Main function"""
    print_header("Mem0 API Key Update Script")
    print_info(f"Target API Key: {MEM0_API_KEY[:10]}...{MEM0_API_KEY[-10:]}")
    print_info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Connect to database
    connection = connect_to_database()
    if not connection:
        print_error("Cannot proceed without database connection")
        return 1
    
    try:
        # Find mem0 configurations
        configs = find_mem0_configs(connection)
        
        if configs:
            # Ask for confirmation
            print_warning("\nThis will update the API key in the database.")
            response = input(f"{Colors.WARNING}Do you want to proceed? (yes/no): {Colors.ENDC}").lower()
            
            if response in ['yes', 'y']:
                # Update API keys
                if update_api_keys(connection, configs):
                    # Verify the update
                    if verify_update(connection):
                        print_success("\n✅ All API keys updated successfully!")
                        print_info("\nNext steps:")
                        print_info("1. Clear Redis cache if you're using it")
                        print_info("2. Restart the manager-api service")
                        print_info("3. Restart the xiaozhi-server")
                        return 0
                    else:
                        print_error("\n❌ Verification failed - some keys may not be updated correctly")
                        return 1
                else:
                    print_error("\n❌ Update failed")
                    return 1
            else:
                print_info("Update cancelled by user")
                return 0
        else:
            print_warning("\nNo mem0ai configurations found to update")
            print_info("Make sure you have configured mem0ai in the Model Configuration")
            return 0
            
    finally:
        connection.close()
        print_info("\nDatabase connection closed")

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nScript interrupted by user")
        sys.exit(0)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        sys.exit(1)