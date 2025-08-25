#!/usr/bin/env python3
"""
Script to add mem0.api_key system parameter
This will bypass the API key masking issue
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
    print(f"{Colors.OKGREEN}[OK] {text}{Colors.ENDC}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.FAIL}[ERROR] {text}{Colors.ENDC}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.OKCYAN}[INFO] {text}{Colors.ENDC}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.WARNING}[WARNING] {text}{Colors.ENDC}")

def connect_to_database():
    """Connect to the MySQL database"""
    try:
        print_info("Connecting to database...")
        connection = pymysql.connect(**DB_CONFIG)
        
        # Test the connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        print_success("Successfully connected to database")
        return connection
        
    except Exception as e:
        print_error(f"Failed to connect to database: {str(e)}")
        return None

def add_system_parameter(connection):
    """Add mem0.api_key system parameter"""
    try:
        with connection.cursor() as cursor:
            # Check if parameter already exists
            cursor.execute("SELECT * FROM sys_params WHERE param_code = %s", ('mem0.api_key',))
            existing = cursor.fetchone()
            
            if existing:
                print_warning("Parameter mem0.api_key already exists:")
                print(f"  Current value: {existing[2][:10]}...{existing[2][-10:] if len(existing[2]) > 20 else existing[2]}")
                
                response = input(f"{Colors.WARNING}Do you want to update it? (yes/no): {Colors.ENDC}").lower()
                if response not in ['yes', 'y']:
                    print_info("Skipping update")
                    return True
                
                # Update existing parameter
                update_query = """
                    UPDATE sys_params 
                    SET param_value = %s, 
                        update_date = NOW(),
                        updater = 1
                    WHERE param_code = %s
                """
                cursor.execute(update_query, (MEM0_API_KEY, 'mem0.api_key'))
                connection.commit()
                print_success("Updated existing mem0.api_key parameter")
                
            else:
                # Get the next ID
                cursor.execute("SELECT MAX(id) FROM sys_params")
                max_id = cursor.fetchone()[0]
                next_id = (max_id or 0) + 1
                
                # Insert new parameter
                insert_query = """
                    INSERT INTO sys_params (id, param_code, param_value, value_type, param_type, remark, create_date, creator)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
                """
                
                cursor.execute(insert_query, (
                    next_id,
                    'mem0.api_key',
                    MEM0_API_KEY,
                    'string',
                    1,  # param_type: 1 for system parameters
                    'Mem0 AI API key for memory management',
                    1   # creator: admin user
                ))
                
                connection.commit()
                print_success("Added new mem0.api_key system parameter")
            
            return True
            
    except Exception as e:
        connection.rollback()
        print_error(f"Failed to add system parameter: {str(e)}")
        return False

def verify_parameter(connection):
    """Verify the parameter was added correctly"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM sys_params WHERE param_code = %s", ('mem0.api_key',))
            result = cursor.fetchone()
            
            if result:
                print_success("Parameter verification successful:")
                print(f"  ID: {result[0]}")
                print(f"  Code: {result[1]}")
                print(f"  Value: {result[2][:10]}...{result[2][-10:]}")
                print(f"  Type: {result[3]}")
                print(f"  Remark: {result[5]}")
                return True
            else:
                print_error("Parameter not found after insertion")
                return False
                
    except Exception as e:
        print_error(f"Failed to verify parameter: {str(e)}")
        return False

def main():
    """Main function"""
    print_header("Add Mem0 API Key System Parameter")
    print_info(f"Target API Key: {MEM0_API_KEY[:10]}...{MEM0_API_KEY[-10:]}")
    print_info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Connect to database
    connection = connect_to_database()
    if not connection:
        print_error("Cannot proceed without database connection")
        return 1
    
    try:
        # Add system parameter
        if add_system_parameter(connection):
            # Verify the parameter
            if verify_parameter(connection):
                print_success("\n✅ System parameter added successfully!")
                print_info("\nNext steps:")
                print_info("1. Restart the manager-api service to load the new parameter")
                print_info("2. Test device connection again")
                print_info("3. Check that mem0 authentication now works")
                return 0
            else:
                return 1
        else:
            return 1
            
    finally:
        connection.close()
        print_info("Database connection closed")

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nScript interrupted by user")
        sys.exit(0)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        sys.exit(1)