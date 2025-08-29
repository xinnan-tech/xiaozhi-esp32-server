#!/usr/bin/env python3
"""
Script to check system parameters table for mem0.api_key
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

def check_system_params(connection):
    """Check system parameters table for mem0.api_key"""
    try:
        with connection.cursor() as cursor:
            # First, let's see what tables exist
            print_info("Checking available tables...")
            cursor.execute("SHOW TABLES LIKE '%param%'")
            param_tables = cursor.fetchall()
            
            if param_tables:
                print_success(f"Found parameter-related tables:")
                for table in param_tables:
                    print(f"  - {table[0]}")
            
            # Try different possible table names
            possible_tables = [
                'sys_params',
                'system_params', 
                'sys_parameters',
                'system_parameters',
                'config_params',
                'application_params'
            ]
            
            found_table = None
            for table_name in possible_tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    found_table = table_name
                    print_success(f"Found system parameters table: {table_name}")
                    break
                except pymysql.err.ProgrammingError:
                    continue
            
            if found_table:
                # First, check the table structure
                cursor.execute(f"DESCRIBE {found_table}")
                columns = cursor.fetchall()
                print_info(f"Table structure for {found_table}:")
                for col in columns:
                    print(f"  {col[0]} ({col[1]})")
                
                # Show all parameters for context
                cursor.execute(f"SELECT * FROM {found_table} LIMIT 10")
                all_params = cursor.fetchall()
                print_info(f"\nFirst 10 parameters in {found_table}:")
                for row in all_params:
                    print(f"  Row: {row}")
                
                # Try to find mem0 parameter based on actual column structure
                if columns:
                    # Assume first column is key, second is value
                    key_col = columns[0][0]
                    
                    query = f"SELECT * FROM {found_table} WHERE {key_col} = %s OR {key_col} LIKE %s"
                    cursor.execute(query, ('mem0.api_key', '%mem0%'))
                    results = cursor.fetchall()
                    
                    if results:
                        print_success("Found mem0-related parameters:")
                        for row in results:
                            print(f"  Row: {row}")
                    else:
                        print_warning("No mem0.api_key parameter found in system parameters")
                    
            else:
                print_warning("No system parameters table found")
                print_info("Available tables:")
                cursor.execute("SHOW TABLES")
                all_tables = cursor.fetchall()
                for table in all_tables:
                    print(f"  - {table[0]}")
                
    except Exception as e:
        print_error(f"Failed to check system parameters: {str(e)}")

def main():
    """Main function"""
    print_header("System Parameters Check Script")
    print_info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Connect to database
    connection = connect_to_database()
    if not connection:
        print_error("Cannot proceed without database connection")
        return 1
    
    try:
        check_system_params(connection)
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