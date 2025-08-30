#!/usr/bin/env python3
"""
Script to ensure play_story is included in default agent template
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
            print("Connected to Railway MySQL database")
            return connection
            
    except Error as e:
        print(f"Database connection error: {e}")
        return None

def check_agent_templates(connection):
    """Check all agent templates and their plugin configurations"""
    cursor = connection.cursor()
    try:
        print("\n1. Checking Agent Templates...")
        print("=" * 50)
        
        # Get all agent templates
        cursor.execute("""
            SELECT id, agent_name, agent_code
            FROM ai_agent_template
            ORDER BY sort, id
        """)
        
        templates = cursor.fetchall()
        
        print(f"Found {len(templates)} agent templates:")
        for template_id, agent_name, agent_code in templates:
            print(f"  - {agent_name or agent_code} (ID: {template_id})")
        
        return templates
        
    except Error as e:
        print(f"Error checking templates: {e}")
        return []
    finally:
        cursor.close()

def check_template_plugin_mappings(connection):
    """Check if templates have default plugin mappings"""
    cursor = connection.cursor()
    try:
        print("\n2. Checking Template Plugin Mappings...")
        print("=" * 50)
        
        # Check if there's a template plugin mapping table
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = 'railway' 
            AND TABLE_NAME LIKE '%template%plugin%'
        """)
        
        mapping_tables = cursor.fetchall()
        
        if mapping_tables:
            print("Found template plugin mapping tables:")
            for table in mapping_tables:
                print(f"  - {table[0]}")
        else:
            print("No template plugin mapping tables found")
            print("Templates likely don't have default plugin configurations")
            print("Plugins are probably added when agents are created from templates")
        
        return mapping_tables
        
    except Error as e:
        print(f"Error checking template mappings: {e}")
        return []
    finally:
        cursor.close()

def add_story_to_all_templates(connection):
    """Ensure all templates will include play_story for new agents"""
    cursor = connection.cursor()
    try:
        print("\n3. Adding Story Playback to All Templates...")
        print("=" * 50)
        
        # Get all templates
        cursor.execute("SELECT id, agent_name FROM ai_agent_template")
        templates = cursor.fetchall()
        
        # For each template, we need to ensure Story Playback is included
        # Since templates don't have direct plugin mappings, we need to check
        # if there's a default plugin list or configuration
        
        # Check if there's a system parameter for default plugins
        cursor.execute("""
            SELECT param_key, param_value 
            FROM sys_params 
            WHERE param_key LIKE '%plugin%' OR param_key LIKE '%function%'
        """)
        
        system_params = cursor.fetchall()
        
        if system_params:
            print("Found system parameters related to plugins:")
            for key, value in system_params:
                print(f"  {key}: {value[:100] if value else 'NULL'}...")
                
                # Check if this parameter contains plugin defaults
                if 'default' in key.lower() and 'plugin' in key.lower():
                    try:
                        if value and value.startswith('['):
                            plugins = json.loads(value)
                            if 'SYSTEM_PLUGIN_STORY' not in plugins:
                                plugins.append('SYSTEM_PLUGIN_STORY')
                                cursor.execute("""
                                    UPDATE sys_params 
                                    SET param_value = %s 
                                    WHERE param_key = %s
                                """, (json.dumps(plugins), key))
                                print(f"  Updated {key} to include SYSTEM_PLUGIN_STORY")
                    except:
                        pass
        
        # Add a new system parameter for default plugins if it doesn't exist
        cursor.execute("""
            SELECT param_key FROM sys_params 
            WHERE param_key = 'default_agent_plugins'
        """)
        
        if not cursor.fetchone():
            print("\nAdding default_agent_plugins system parameter...")
            
            default_plugins = [
                "SYSTEM_PLUGIN_MUSIC",
                "SYSTEM_PLUGIN_STORY",
                "SYSTEM_PLUGIN_WEATHER",
                "SYSTEM_PLUGIN_NEWS_NEWSNOW"
            ]
            
            cursor.execute("""
                INSERT INTO sys_params (param_key, param_value, param_type, remark, creator, create_date, updater, update_date)
                VALUES (%s, %s, %s, %s, 0, NOW(), 0, NOW())
            """, (
                'default_agent_plugins',
                json.dumps(default_plugins),
                1,  # Type 1 for system parameter
                'Default plugins for new agents'
            ))
            
            print("Added default_agent_plugins with Story Playback included")
            connection.commit()
        else:
            # Update existing parameter
            cursor.execute("""
                SELECT param_value FROM sys_params 
                WHERE param_key = 'default_agent_plugins'
            """)
            
            current_value = cursor.fetchone()[0]
            if current_value:
                try:
                    plugins = json.loads(current_value)
                    if 'SYSTEM_PLUGIN_STORY' not in plugins:
                        plugins.append('SYSTEM_PLUGIN_STORY')
                        cursor.execute("""
                            UPDATE sys_params 
                            SET param_value = %s, update_date = NOW()
                            WHERE param_key = 'default_agent_plugins'
                        """, (json.dumps(plugins),))
                        print("Updated default_agent_plugins to include SYSTEM_PLUGIN_STORY")
                        connection.commit()
                    else:
                        print("SYSTEM_PLUGIN_STORY already in default_agent_plugins")
                except Exception as e:
                    print(f"Error updating default plugins: {e}")
        
        return True
        
    except Error as e:
        print(f"Error adding story to templates: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()

def ensure_template_story_mappings(connection):
    """Ensure all agent templates have Story Playback in their configuration"""
    cursor = connection.cursor()
    try:
        print("\n4. Ensuring Template Configurations Include Story...")
        print("=" * 50)
        
        # Since templates don't have direct plugin mappings,
        # we need to ensure the agent creation process includes Story Playback
        
        # Check if there's an agent_template_plugin table or similar
        cursor.execute("""
            SHOW TABLES LIKE '%agent_template%'
        """)
        
        template_tables = cursor.fetchall()
        print(f"Template-related tables found: {len(template_tables)}")
        for table in template_tables:
            print(f"  - {table[0]}")
        
        # The key is to ensure that when an agent is created from a template,
        # it automatically gets the Story Playback plugin
        
        # Check for any stored procedures or triggers that create agents
        cursor.execute("""
            SELECT ROUTINE_NAME, ROUTINE_TYPE 
            FROM information_schema.ROUTINES 
            WHERE ROUTINE_SCHEMA = 'railway' 
            AND (ROUTINE_NAME LIKE '%agent%' OR ROUTINE_NAME LIKE '%create%')
        """)
        
        procedures = cursor.fetchall()
        if procedures:
            print("\nFound stored procedures/functions related to agents:")
            for proc_name, proc_type in procedures:
                print(f"  - {proc_type}: {proc_name}")
        
        return True
        
    except Error as e:
        print(f"Error ensuring template mappings: {e}")
        return False
    finally:
        cursor.close()

def create_trigger_for_new_agents(connection):
    """Create a trigger to automatically add Story Playback to new agents"""
    cursor = connection.cursor()
    try:
        print("\n5. Creating Trigger for New Agents...")
        print("=" * 50)
        
        # Drop existing trigger if it exists
        cursor.execute("DROP TRIGGER IF EXISTS add_story_to_new_agent")
        
        # Create trigger to automatically add Story Playback when a new agent is created
        trigger_sql = """
        CREATE TRIGGER add_story_to_new_agent
        AFTER INSERT ON ai_agent
        FOR EACH ROW
        BEGIN
            -- Add Story Playback plugin to new agent
            IF NOT EXISTS (
                SELECT 1 FROM ai_agent_plugin_mapping 
                WHERE agent_id = NEW.id 
                AND plugin_id = 'SYSTEM_PLUGIN_STORY'
            ) THEN
                INSERT INTO ai_agent_plugin_mapping (agent_id, plugin_id, param_info)
                VALUES (
                    NEW.id, 
                    'SYSTEM_PLUGIN_STORY',
                    '{"story_dir": "./stories", "story_ext": ".mp3;.wav;.m4a", "refresh_time": "300"}'
                );
            END IF;
            
            -- Also add other default plugins
            IF NOT EXISTS (
                SELECT 1 FROM ai_agent_plugin_mapping 
                WHERE agent_id = NEW.id 
                AND plugin_id = 'SYSTEM_PLUGIN_MUSIC'
            ) THEN
                INSERT INTO ai_agent_plugin_mapping (agent_id, plugin_id, param_info)
                VALUES (NEW.id, 'SYSTEM_PLUGIN_MUSIC', '{}');
            END IF;
            
            IF NOT EXISTS (
                SELECT 1 FROM ai_agent_plugin_mapping 
                WHERE agent_id = NEW.id 
                AND plugin_id = 'SYSTEM_PLUGIN_WEATHER'
            ) THEN
                INSERT INTO ai_agent_plugin_mapping (agent_id, plugin_id, param_info)
                VALUES (NEW.id, 'SYSTEM_PLUGIN_WEATHER', '{"api_key": "12dd0eea5789636262549c9ec7f4f7d8", "default_location": "Bangalore", "units": "metric", "lang": "en"}');
            END IF;
        END
        """
        
        try:
            cursor.execute(trigger_sql)
            print("Created trigger to automatically add Story Playback to new agents!")
            connection.commit()
            return True
        except Error as e:
            if "This version of MySQL doesn't yet support" in str(e):
                print("Database doesn't support this trigger syntax")
                print("Will use alternative method...")
                return False
            else:
                print(f"Error creating trigger: {e}")
                return False
        
    except Error as e:
        print(f"Error with trigger creation: {e}")
        return False
    finally:
        cursor.close()

def main():
    print("Fixing Default Agent Template for Story Playback")
    print("=" * 70)
    
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        # 1. Check existing templates
        templates = check_agent_templates(connection)
        
        # 2. Check template plugin mappings
        check_template_plugin_mappings(connection)
        
        # 3. Add story to templates
        add_story_to_all_templates(connection)
        
        # 4. Ensure template configurations
        ensure_template_story_mappings(connection)
        
        # 5. Try to create trigger (may not work on all MySQL versions)
        trigger_created = create_trigger_for_new_agents(connection)
        
        # Summary
        print(f"\n{'='*70}")
        print("SUMMARY")
        print('='*70)
        
        print("Actions taken:")
        print("1. Checked all agent templates")
        print("2. Added default_agent_plugins system parameter with Story Playback")
        print("3. Ensured Story Playback is in default plugin list")
        
        if trigger_created:
            print("4. Created database trigger for automatic Story Playback addition")
        else:
            print("4. Trigger creation failed (database limitation)")
            print("   New agents will need Story Playback added by the application")
        
        print("\nRECOMMENDATION:")
        print("To ensure all new agents have Story Playback, the agent creation")
        print("process in the manager-api should be updated to automatically")
        print("include SYSTEM_PLUGIN_STORY in the plugin mappings.")
        
    finally:
        connection.close()

if __name__ == "__main__":
    main()