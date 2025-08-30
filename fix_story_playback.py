#!/usr/bin/env python3
"""
Script to fix Story Playback function placement in agent templates
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

def examine_ai_agent_template(connection):
    """Examine the ai_agent_template table"""
    cursor = connection.cursor()
    try:
        print(f"\n{'='*60}")
        print("Structure of ai_agent_template table:")
        print('='*60)
        
        cursor.execute("DESCRIBE ai_agent_template")
        columns = cursor.fetchall()
        
        headers = ["Field", "Type", "Null", "Key", "Default", "Extra"]
        print(tabulate(columns, headers=headers, tablefmt="grid"))
        
        # Get all records
        cursor.execute("SELECT * FROM ai_agent_template")
        templates = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        
        print(f"\nFound {len(templates)} agent templates:")
        
        for i, template in enumerate(templates):
            template_dict = dict(zip(column_names, template))
            print(f"\n--- Template {i+1} ---")
            print(f"ID: {template_dict.get('id')}")
            print(f"Template Name: {template_dict.get('template_name', template_dict.get('name'))}")
            
            # Look for JSON fields that might contain function configurations
            for col_name, cell_value in template_dict.items():
                if isinstance(cell_value, str) and cell_value.strip().startswith('{'):
                    try:
                        json_data = json.loads(cell_value)
                        print(f"\nJSON field '{col_name}':")
                        
                        # Check if it contains function configurations
                        if any(key in json_data for key in ['selected_functions', 'unselected_functions', 'functions', 'selectedFunctions', 'unselectedFunctions', 'plugins']):
                            print(f"  Contains function/plugin configuration:")
                            print(json.dumps(json_data, indent=4))
                        else:
                            # Just show the structure
                            print(f"  Keys: {list(json_data.keys())}")
                            
                    except json.JSONDecodeError:
                        if len(str(cell_value)) > 100:
                            print(f"  {col_name}: [Long text content, first 100 chars]: {str(cell_value)[:100]}...")
                        else:
                            print(f"  {col_name}: {cell_value}")
                elif cell_value is not None:
                    if len(str(cell_value)) > 100:
                        print(f"  {col_name}: [Long content]: {str(cell_value)[:100]}...")
                    else:
                        print(f"  {col_name}: {cell_value}")
        
        return templates, column_names
        
    except Error as e:
        print(f"Error examining ai_agent_template: {e}")
        return None, None
    finally:
        cursor.close()

def check_ai_agent_plugin_mapping(connection):
    """Check the ai_agent_plugin_mapping table"""
    cursor = connection.cursor()
    try:
        print(f"\n{'='*60}")
        print("ai_agent_plugin_mapping table:")
        print('='*60)
        
        cursor.execute("DESCRIBE ai_agent_plugin_mapping")
        columns = cursor.fetchall()
        
        headers = ["Field", "Type", "Null", "Key", "Default", "Extra"]
        print(tabulate(columns, headers=headers, tablefmt="grid"))
        
        # Get all records
        cursor.execute("SELECT * FROM ai_agent_plugin_mapping")
        mappings = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        
        if mappings:
            print(f"\nPlugin mappings:")
            print(tabulate(mappings, headers=column_names, tablefmt="grid"))
        else:
            print("\nNo plugin mappings found")
        
        return mappings, column_names
        
    except Error as e:
        print(f"Error examining ai_agent_plugin_mapping: {e}")
        return None, None
    finally:
        cursor.close()

def fix_story_playback_in_templates(connection):
    """Fix Story Playback function to be in selected functions for all agent templates"""
    cursor = connection.cursor()
    try:
        print(f"\n{'='*60}")
        print("Fixing Story Playback function placement...")
        print('='*60)
        
        # Get all agent templates
        cursor.execute("SELECT * FROM ai_agent_template")
        templates = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        
        story_playback_plugin_id = "SYSTEM_PLUGIN_STORY"
        updates_made = 0
        
        for template in templates:
            template_dict = dict(zip(column_names, template))
            template_id = template_dict.get('id')
            template_name = template_dict.get('template_name', template_dict.get('name', 'Unknown'))
            
            print(f"\nProcessing template: {template_name} (ID: {template_id})")
            
            # Check if this template already has the Story Playback plugin mapped
            cursor.execute("""
                SELECT * FROM ai_agent_plugin_mapping 
                WHERE template_id = %s AND plugin_id = %s
            """, (template_id, story_playback_plugin_id))
            existing_mapping = cursor.fetchone()
            
            if existing_mapping:
                mapping_dict = dict(zip([desc[0] for desc in cursor.description], existing_mapping))
                current_status = mapping_dict.get('status', 0)
                
                print(f"  Found existing mapping with status: {current_status}")
                
                if current_status != 1:  # 1 = selected/enabled, 0 = unselected/disabled
                    # Update the mapping to enable the plugin
                    cursor.execute("""
                        UPDATE ai_agent_plugin_mapping 
                        SET status = 1, update_date = NOW(), updater = 0
                        WHERE template_id = %s AND plugin_id = %s
                    """, (template_id, story_playback_plugin_id))
                    
                    print(f"  ✓ Updated Story Playback status from {current_status} to 1 (selected)")
                    updates_made += 1
                else:
                    print(f"  ✓ Story Playback already selected for this template")
            else:
                # Create new mapping with status = 1 (selected)
                cursor.execute("""
                    INSERT INTO ai_agent_plugin_mapping 
                    (template_id, plugin_id, status, sort, creator, create_date, updater, update_date)
                    VALUES (%s, %s, 1, 0, 0, NOW(), 0, NOW())
                """, (template_id, story_playback_plugin_id))
                
                print(f"  ✓ Created new mapping with Story Playback selected")
                updates_made += 1
        
        connection.commit()
        print(f"\n{'='*60}")
        print(f"Fix completed! Made {updates_made} updates to ensure Story Playback is selected for all agent templates.")
        print('='*60)
        
    except Error as e:
        print(f"Error fixing Story Playback function: {e}")
        connection.rollback()
    finally:
        cursor.close()

def verify_fix(connection):
    """Verify that Story Playback is now selected for all templates"""
    cursor = connection.cursor()
    try:
        print(f"\n{'='*60}")
        print("Verifying fix...")
        print('='*60)
        
        cursor.execute("""
            SELECT 
                at.id as template_id,
                at.template_name,
                apm.plugin_id,
                apm.status,
                amp.name as plugin_name
            FROM ai_agent_template at
            LEFT JOIN ai_agent_plugin_mapping apm ON at.id = apm.template_id AND apm.plugin_id = 'SYSTEM_PLUGIN_STORY'
            LEFT JOIN ai_model_provider amp ON apm.plugin_id = amp.id
            ORDER BY at.template_name
        """)
        
        results = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        
        print(f"\nStory Playback status for all templates:")
        print(tabulate(results, headers=column_names, tablefmt="grid"))
        
        # Count how many are selected
        selected_count = sum(1 for result in results if result[3] == 1)  # status column
        total_templates = len([r for r in results if r[0] is not None])  # templates with non-null id
        
        print(f"\nSummary:")
        print(f"Total templates: {total_templates}")
        print(f"Templates with Story Playback selected: {selected_count}")
        
        if selected_count == total_templates:
            print("✅ SUCCESS: Story Playback is now selected for ALL agent templates!")
        else:
            print(f"⚠️  WARNING: {total_templates - selected_count} templates still don't have Story Playback selected")
        
    except Error as e:
        print(f"Error verifying fix: {e}")
    finally:
        cursor.close()

def main():
    print("Fixing Story Playback function placement in xiaozhi database")
    print("=" * 70)
    
    # Connect to database
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        # Examine agent template structure
        examine_ai_agent_template(connection)
        
        # Check plugin mapping table
        check_ai_agent_plugin_mapping(connection)
        
        # Fix Story Playback placement
        fix_story_playback_in_templates(connection)
        
        # Verify the fix
        verify_fix(connection)
        
    finally:
        if connection.is_connected():
            connection.close()
            print(f"\nMySQL connection closed")

if __name__ == "__main__":
    main()