#!/usr/bin/env python3
"""
Script to check agent templates and functions structure, and fix Story Playback function placement
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

def get_all_tables(connection):
    """Get all tables in the database"""
    cursor = connection.cursor()
    try:
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        print(f"\nAll tables in the database:")
        for table in tables:
            print(f"  - {table[0]}")
        
        return [table[0] for table in tables]
        
    except Error as e:
        print(f"Error getting tables: {e}")
        return None
    finally:
        cursor.close()

def search_agent_related_tables(connection):
    """Search for agent-related tables"""
    cursor = connection.cursor()
    try:
        cursor.execute("SHOW TABLES LIKE '%agent%'")
        agent_tables = cursor.fetchall()
        
        cursor.execute("SHOW TABLES LIKE '%template%'")
        template_tables = cursor.fetchall()
        
        cursor.execute("SHOW TABLES LIKE '%function%'")
        function_tables = cursor.fetchall()
        
        print(f"\nAgent-related tables:")
        for table in agent_tables:
            print(f"  - {table[0]}")
            
        print(f"\nTemplate-related tables:")
        for table in template_tables:
            print(f"  - {table[0]}")
            
        print(f"\nFunction-related tables:")
        for table in function_tables:
            print(f"  - {table[0]}")
        
        return agent_tables + template_tables + function_tables
        
    except Error as e:
        print(f"Error searching agent tables: {e}")
        return None
    finally:
        cursor.close()

def examine_table_structure(connection, table_name):
    """Get detailed structure of a table"""
    cursor = connection.cursor()
    try:
        print(f"\n{'='*60}")
        print(f"Structure of table '{table_name}':")
        print('='*60)
        
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()
        
        headers = ["Field", "Type", "Null", "Key", "Default", "Extra"]
        print(tabulate(columns, headers=headers, tablefmt="grid"))
        
        # Get sample data
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
        sample_data = cursor.fetchall()
        
        if sample_data:
            print(f"\nSample data from '{table_name}':")
            column_names = [desc[0] for desc in cursor.description]
            print(tabulate(sample_data, headers=column_names, tablefmt="grid"))
        
        return columns
        
    except Error as e:
        print(f"Error examining table {table_name}: {e}")
        return None
    finally:
        cursor.close()

def search_story_playback(connection):
    """Search for Story Playback function references"""
    cursor = connection.cursor()
    try:
        print(f"\n{'='*60}")
        print("Searching for 'Story Playback' references in the database...")
        print('='*60)
        
        # Get all tables
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        
        found_references = []
        
        for table in tables:
            try:
                # Get column names for this table
                cursor.execute(f"DESCRIBE {table}")
                columns = cursor.fetchall()
                text_columns = [col[0] for col in columns if 'text' in col[1].lower() or 'varchar' in col[1].lower() or 'json' in col[1].lower()]
                
                if text_columns:
                    # Search in each text column
                    for column in text_columns:
                        search_query = f"SELECT * FROM {table} WHERE {column} LIKE '%Story Playback%' OR {column} LIKE '%story_playback%' OR {column} LIKE '%storyplayback%'"
                        cursor.execute(search_query)
                        results = cursor.fetchall()
                        
                        if results:
                            found_references.append({
                                'table': table,
                                'column': column,
                                'results': results
                            })
                            print(f"\nFound 'Story Playback' in {table}.{column}:")
                            column_names = [desc[0] for desc in cursor.description]
                            print(tabulate(results, headers=column_names, tablefmt="grid"))
                            
            except Error as e:
                # Skip tables that might cause errors
                continue
        
        return found_references
        
    except Error as e:
        print(f"Error searching for Story Playback: {e}")
        return None
    finally:
        cursor.close()

def check_agent_templates(connection):
    """Check agent templates and their configurations"""
    cursor = connection.cursor()
    try:
        print(f"\n{'='*60}")
        print("Checking agent templates...")
        print('='*60)
        
        # Look for agent template related tables
        possible_tables = ['agent_template', 'agent_templates', 'toy', 'agent_config', 'agent_configuration']
        
        for table_name in possible_tables:
            try:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                results = cursor.fetchall()
                
                if results:
                    print(f"\nFound data in table '{table_name}':")
                    column_names = [desc[0] for desc in cursor.description]
                    print(tabulate(results, headers=column_names, tablefmt="grid"))
                    
                    # Check if any columns contain JSON that might have function configurations
                    for i, row in enumerate(results[:1]):  # Check first row only
                        for j, cell in enumerate(row):
                            if isinstance(cell, str) and (cell.strip().startswith('{') or cell.strip().startswith('[')):
                                try:
                                    json_data = json.loads(cell)
                                    print(f"\nJSON data in {table_name}.{column_names[j]} (row {i+1}):")
                                    print(json.dumps(json_data, indent=2))
                                except:
                                    pass
                    
            except Error:
                continue
                
    except Error as e:
        print(f"Error checking agent templates: {e}")
    finally:
        cursor.close()

def fix_story_playback_function(connection):
    """Fix Story Playback function to be in Selected Functions for all agent templates"""
    cursor = connection.cursor()
    try:
        print(f"\n{'='*60}")
        print("Attempting to fix Story Playback function placement...")
        print('='*60)
        
        # First, let's find where the functions are stored
        # Look for common table names that might store agent configurations
        possible_tables = ['toy', 'agent_template', 'agent_config']
        
        for table_name in possible_tables:
            try:
                # Get all records from the table
                cursor.execute(f"SELECT * FROM {table_name}")
                results = cursor.fetchall()
                column_names = [desc[0] for desc in cursor.description]
                
                if results:
                    print(f"\nChecking table '{table_name}' for function configurations...")
                    
                    for i, row in enumerate(results):
                        row_dict = dict(zip(column_names, row))
                        
                        # Look for JSON fields that might contain function configurations
                        for col_name, cell_value in row_dict.items():
                            if isinstance(cell_value, str) and cell_value.strip().startswith('{'):
                                try:
                                    json_data = json.loads(cell_value)
                                    
                                    # Look for function-related keys
                                    if any(key in json_data for key in ['selected_functions', 'unselected_functions', 'functions', 'selectedFunctions', 'unselectedFunctions']):
                                        print(f"\nFound function configuration in {table_name}, row {i+1}, column '{col_name}':")
                                        print(f"Record ID/identifier: {row_dict.get('id', row_dict.get('template_id', 'Unknown'))}")
                                        
                                        # Check if Story Playback is in unselected functions
                                        needs_update = False
                                        updated_data = json_data.copy()
                                        
                                        # Handle different possible key names
                                        unselected_key = None
                                        selected_key = None
                                        
                                        for key in ['unselected_functions', 'unselectedFunctions']:
                                            if key in json_data:
                                                unselected_key = key
                                                break
                                        
                                        for key in ['selected_functions', 'selectedFunctions']:
                                            if key in json_data:
                                                selected_key = key
                                                break
                                        
                                        if unselected_key and selected_key:
                                            unselected_functions = json_data.get(unselected_key, [])
                                            selected_functions = json_data.get(selected_key, [])
                                            
                                            # Look for Story Playback in unselected functions
                                            story_playback_item = None
                                            for func in unselected_functions:
                                                if isinstance(func, dict) and 'Story Playback' in str(func):
                                                    story_playback_item = func
                                                    break
                                                elif isinstance(func, str) and 'Story Playback' in func:
                                                    story_playback_item = func
                                                    break
                                            
                                            if story_playback_item:
                                                print(f"Found Story Playback in unselected functions: {story_playback_item}")
                                                
                                                # Move it to selected functions
                                                updated_data[unselected_key] = [f for f in unselected_functions if f != story_playback_item]
                                                updated_data[selected_key] = selected_functions + [story_playback_item]
                                                
                                                # Update the database
                                                update_query = f"UPDATE {table_name} SET {col_name} = %s WHERE "
                                                if 'id' in row_dict:
                                                    update_query += "id = %s"
                                                    update_params = [json.dumps(updated_data), row_dict['id']]
                                                else:
                                                    # Use the first column as identifier
                                                    first_col = column_names[0]
                                                    update_query += f"{first_col} = %s"
                                                    update_params = [json.dumps(updated_data), row_dict[first_col]]
                                                
                                                print(f"Executing update query: {update_query}")
                                                print(f"Parameters: {update_params[1]} (ID), [JSON data]")
                                                
                                                cursor.execute(update_query, update_params)
                                                connection.commit()
                                                
                                                print(f"✓ Successfully moved Story Playback to selected functions for record {row_dict.get('id', row_dict[column_names[0]])}")
                                                needs_update = True
                                            else:
                                                print(f"Story Playback not found in unselected functions for this record")
                                        
                                        # Print the current function configuration
                                        print(f"Current function configuration:")
                                        print(json.dumps(json_data, indent=2))
                                        
                                except json.JSONDecodeError:
                                    continue
                                    
            except Error as e:
                print(f"Error processing table {table_name}: {e}")
                continue
        
        print(f"\nFunction placement fix completed!")
        
    except Error as e:
        print(f"Error fixing Story Playback function: {e}")
    finally:
        cursor.close()

def main():
    print("Checking xiaozhi database for agent templates and Story Playback function")
    print("=" * 80)
    
    # Connect to database
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        # Get all tables
        print("\n" + "="*60)
        tables = get_all_tables(connection)
        
        # Search for agent-related tables
        print("\n" + "="*60)
        agent_tables = search_agent_related_tables(connection)
        
        # Examine key tables
        key_tables = ['toy']  # Start with 'toy' as it's likely the main agent config table
        for table in key_tables:
            if table in tables:
                examine_table_structure(connection, table)
        
        # Search for Story Playback references
        search_story_playback(connection)
        
        # Check agent templates
        check_agent_templates(connection)
        
        # Fix Story Playback function placement
        fix_story_playback_function(connection)
        
    finally:
        if connection.is_connected():
            connection.close()
            print(f"\nMySQL connection closed")

if __name__ == "__main__":
    main()