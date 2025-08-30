#!/usr/bin/env python3
"""
Simple script to fix Story Playback function placement in agent templates
"""

import mysql.connector
from mysql.connector import Error
import json

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

def check_current_mappings(connection):
    """Check current plugin mappings"""
    cursor = connection.cursor()
    try:
        print("\nChecking current plugin mappings...")
        
        # Check if ai_agent_plugin_mapping has the right structure
        cursor.execute("DESCRIBE ai_agent_plugin_mapping")
        columns = cursor.fetchall()
        
        column_names = [col[0] for col in columns]
        print(f"ai_agent_plugin_mapping columns: {column_names}")
        
        # Check if we should use template_id or agent_id
        if 'template_id' in column_names:
            id_column = 'template_id'
        elif 'agent_id' in column_names:
            id_column = 'agent_id'
        else:
            print("ERROR: Neither template_id nor agent_id found in ai_agent_plugin_mapping table")
            return None, None
            
        # Get all current mappings
        cursor.execute(f"SELECT * FROM ai_agent_plugin_mapping")
        mappings = cursor.fetchall()
        
        print(f"\nFound {len(mappings)} existing plugin mappings")
        for mapping in mappings:
            mapping_dict = dict(zip(column_names, mapping))
            print(f"ID: {mapping_dict.get('id')}, {id_column}: {mapping_dict.get(id_column)}, plugin_id: {mapping_dict.get('plugin_id')}")
        
        return mappings, id_column
        
    except Error as e:
        print(f"Error checking current mappings: {e}")
        return None, None
    finally:
        cursor.close()

def get_all_agent_templates(connection):
    """Get all agent template IDs"""
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id, agent_name FROM ai_agent_template")
        templates = cursor.fetchall()
        
        print(f"\nFound {len(templates)} agent templates:")
        for template in templates:
            print(f"  ID: {template[0]}, Name: {template[1]}")
        
        return templates
        
    except Error as e:
        print(f"Error getting agent templates: {e}")
        return []
    finally:
        cursor.close()

def add_story_playback_to_all_templates(connection, templates, id_column):
    """Add Story Playback plugin to all templates"""
    cursor = connection.cursor()
    try:
        story_playback_plugin_id = "SYSTEM_PLUGIN_STORY"
        updates_made = 0
        
        print(f"\nAdding Story Playback plugin to all templates...")
        
        for template_id, template_name in templates:
            print(f"\nProcessing template: {template_name} (ID: {template_id})")
            
            # Check if mapping already exists
            cursor.execute(f"""
                SELECT * FROM ai_agent_plugin_mapping 
                WHERE {id_column} = %s AND plugin_id = %s
            """, (template_id, story_playback_plugin_id))
            
            existing = cursor.fetchone()
            
            if existing:
                print(f"  Already has Story Playback mapping")
            else:
                # Insert new mapping
                # Create a basic param_info for the story plugin
                param_info = {
                    "story_dir": "./stories",
                    "story_ext": ".mp3;.wav;.m4a",
                    "refresh_time": "300"
                }
                
                cursor.execute(f"""
                    INSERT INTO ai_agent_plugin_mapping 
                    ({id_column}, plugin_id, param_info)
                    VALUES (%s, %s, %s)
                """, (template_id, story_playback_plugin_id, json.dumps(param_info)))
                
                print(f" Added Story Playback mapping")
                updates_made += 1
        
        connection.commit()
        print(f"\nCompleted! Added Story Playback to {updates_made} templates.")
        
    except Error as e:
        print(f"Error adding Story Playback mappings: {e}")
        connection.rollback()
    finally:
        cursor.close()

def verify_mappings(connection, id_column):
    """Verify all templates now have Story Playback"""
    cursor = connection.cursor()
    try:
        print(f"\nVerifying Story Playback mappings...")
        
        cursor.execute(f"""
            SELECT 
                at.id,
                at.agent_name,
                CASE WHEN apm.plugin_id IS NOT NULL THEN 'YES' ELSE 'NO' END as has_story_playback
            FROM ai_agent_template at
            LEFT JOIN ai_agent_plugin_mapping apm 
                ON at.id = apm.{id_column} AND apm.plugin_id = 'SYSTEM_PLUGIN_STORY'
            ORDER BY at.agent_name
        """)
        
        results = cursor.fetchall()
        
        total_templates = len(results)
        with_story_playback = sum(1 for result in results if result[2] == 'YES')
        
        print(f"\nStory Playback status:")
        for result in results:
            template_id, agent_name, has_playback = result
            status = "✓" if has_playback == 'YES' else "✗"
            print(f"  {status} {agent_name} (ID: {template_id})")
        
        print(f"\nSummary:")
        print(f"Total templates: {total_templates}")
        print(f"With Story Playback: {with_story_playback}")
        
        if with_story_playback == total_templates:
            print(" SUCCESS: All templates now have Story Playback!")
        else:
            print(f" {total_templates - with_story_playback} templates still missing Story Playback")
            
    except Error as e:
        print(f"Error verifying mappings: {e}")
    finally:
        cursor.close()

def main():
    print("Fixing Story Playback function for all agent templates")
    print("=" * 60)
    
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        # Check current state
        mappings, id_column = check_current_mappings(connection)
        if not id_column:
            return
        
        # Get all templates
        templates = get_all_agent_templates(connection)
        if not templates:
            print("No agent templates found!")
            return
        
        # Add Story Playback to all templates
        add_story_playback_to_all_templates(connection, templates, id_column)
        
        # Verify the fix
        verify_mappings(connection, id_column)
        
    finally:
        if connection.is_connected():
            connection.close()
            print(f"\nMySQL connection closed")

if __name__ == "__main__":
    main()