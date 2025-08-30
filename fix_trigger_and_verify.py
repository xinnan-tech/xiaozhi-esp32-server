#!/usr/bin/env python3
"""
Fix the trigger and ensure Story Playback is added to ALL new agents
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

def check_latest_agent(connection):
    """Check the latest agent that was just created"""
    cursor = connection.cursor()
    try:
        print("\n1. Checking Latest Agent...")
        print("=" * 60)
        
        # Get the most recent agent
        cursor.execute("""
            SELECT 
                a.id,
                a.agent_name,
                a.agent_code,
                a.created_at,
                GROUP_CONCAT(apm.plugin_id) as plugins
            FROM ai_agent a
            LEFT JOIN ai_agent_plugin_mapping apm ON a.id = apm.agent_id
            WHERE a.agent_name = 'test' OR a.agent_code LIKE 'AGT_1756545169%'
            GROUP BY a.id, a.agent_name, a.agent_code, a.created_at
            ORDER BY a.created_at DESC
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        
        if result:
            agent_id, name, code, created, plugins = result
            print(f"Latest agent: {name} (ID: {agent_id[:16]}...)")
            print(f"Code: {code}")
            print(f"Created: {created}")
            print(f"Plugins: {plugins}")
            
            if plugins and 'SYSTEM_PLUGIN_STORY' not in plugins:
                print("\n[!] Story Playback is MISSING! Adding it now...")
                
                # Add Story Playback
                param_info = {
                    "story_dir": "./stories",
                    "story_ext": ".mp3;.wav;.m4a",
                    "refresh_time": "300"
                }
                
                cursor.execute("""
                    INSERT INTO ai_agent_plugin_mapping 
                    (agent_id, plugin_id, param_info)
                    VALUES (%s, %s, %s)
                """, (agent_id, "SYSTEM_PLUGIN_STORY", json.dumps(param_info)))
                
                connection.commit()
                print("[FIXED] Added Story Playback to latest agent!")
                
                return agent_id
            elif plugins and 'SYSTEM_PLUGIN_STORY' in plugins:
                print("[OK] Story Playback already present!")
                return agent_id
        else:
            print("No agent found with name 'test'")
            
        return None
        
    except Error as e:
        print(f"Error checking latest agent: {e}")
        return None
    finally:
        cursor.close()

def drop_and_recreate_trigger(connection):
    """Drop the old trigger and create a better one"""
    cursor = connection.cursor()
    try:
        print("\n2. Recreating Database Trigger...")
        print("=" * 60)
        
        # Drop existing trigger
        cursor.execute("DROP TRIGGER IF EXISTS add_story_to_new_agent")
        print("Dropped old trigger")
        
        # Create new trigger that works after INSERT
        # Using simpler syntax that should work on more MySQL versions
        trigger_sql = """
        CREATE TRIGGER add_story_to_new_agent
        AFTER INSERT ON ai_agent
        FOR EACH ROW
        BEGIN
            INSERT IGNORE INTO ai_agent_plugin_mapping (agent_id, plugin_id, param_info)
            VALUES (NEW.id, 'SYSTEM_PLUGIN_STORY', '{"story_dir": "./stories", "story_ext": ".mp3;.wav;.m4a", "refresh_time": "300"}');
        END
        """
        
        cursor.execute(trigger_sql)
        connection.commit()
        print("Created new trigger successfully!")
        
        return True
        
    except Error as e:
        print(f"Trigger creation failed: {e}")
        
        # Try alternative approach - stored procedure
        try:
            print("\nTrying stored procedure approach...")
            
            cursor.execute("DROP PROCEDURE IF EXISTS add_default_plugins")
            
            proc_sql = """
            CREATE PROCEDURE add_default_plugins(IN agent_id VARCHAR(32))
            BEGIN
                INSERT IGNORE INTO ai_agent_plugin_mapping (agent_id, plugin_id, param_info)
                VALUES (agent_id, 'SYSTEM_PLUGIN_STORY', '{"story_dir": "./stories", "story_ext": ".mp3;.wav;.m4a", "refresh_time": "300"}');
            END
            """
            
            cursor.execute(proc_sql)
            connection.commit()
            print("Created stored procedure as alternative!")
            
            return True
            
        except Error as e2:
            print(f"Stored procedure also failed: {e2}")
            return False
    finally:
        cursor.close()

def ensure_all_agents_have_story(connection):
    """Make sure ALL agents have Story Playback"""
    cursor = connection.cursor()
    try:
        print("\n3. Ensuring ALL Agents Have Story Playback...")
        print("=" * 60)
        
        # Find agents without Story Playback
        cursor.execute("""
            SELECT a.id, a.agent_name
            FROM ai_agent a
            LEFT JOIN ai_agent_plugin_mapping apm 
                ON a.id = apm.agent_id AND apm.plugin_id = 'SYSTEM_PLUGIN_STORY'
            WHERE apm.plugin_id IS NULL
        """)
        
        agents_without_story = cursor.fetchall()
        
        if agents_without_story:
            print(f"Found {len(agents_without_story)} agents without Story Playback:")
            
            param_info = {
                "story_dir": "./stories",
                "story_ext": ".mp3;.wav;.m4a",
                "refresh_time": "300"
            }
            
            for agent_id, agent_name in agents_without_story:
                print(f"  Adding to: {agent_name}")
                
                cursor.execute("""
                    INSERT IGNORE INTO ai_agent_plugin_mapping 
                    (agent_id, plugin_id, param_info)
                    VALUES (%s, %s, %s)
                """, (agent_id, "SYSTEM_PLUGIN_STORY", json.dumps(param_info)))
            
            connection.commit()
            print(f"[FIXED] Added Story Playback to {len(agents_without_story)} agents!")
        else:
            print("All agents already have Story Playback!")
        
        return True
        
    except Error as e:
        print(f"Error ensuring Story Playback: {e}")
        return False
    finally:
        cursor.close()

def update_manager_api_defaults(connection):
    """Update manager-api default plugins to include Story Playback"""
    cursor = connection.cursor()
    try:
        print("\n4. Updating Manager-API Default Plugins...")
        print("=" * 60)
        
        # Check if there's a default plugins configuration
        cursor.execute("""
            SELECT id, agent_code, agent_name
            FROM ai_agent_template
            WHERE is_visible = 0
            ORDER BY sort
            LIMIT 1
        """)
        
        default_template = cursor.fetchone()
        
        if default_template:
            template_id = default_template[0]
            print(f"Default template: {default_template[2]} (ID: {template_id})")
            
            # The manager-api needs to be configured to include Story Playback
            # when creating agents from templates
            
            print("\nRECOMMENDATION FOR MANAGER-API:")
            print("The manager-api code should be updated to include")
            print("SYSTEM_PLUGIN_STORY in the default plugins list when")
            print("creating new agents. Currently it only adds:")
            print("  - SYSTEM_PLUGIN_MUSIC")
            print("  - SYSTEM_PLUGIN_WEATHER")
            print("  - SYSTEM_PLUGIN_NEWS_NEWSNOW")
            print("\nIt should also add:")
            print("  - SYSTEM_PLUGIN_STORY")
        
        return True
        
    except Error as e:
        print(f"Error updating defaults: {e}")
        return False
    finally:
        cursor.close()

def main():
    print("Fixing Story Playback Auto-Addition for New Agents")
    print("=" * 70)
    
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        # 1. Check and fix the latest agent
        latest_agent_id = check_latest_agent(connection)
        
        # 2. Try to recreate trigger
        trigger_created = drop_and_recreate_trigger(connection)
        
        # 3. Ensure all agents have Story Playback
        ensure_all_agents_have_story(connection)
        
        # 4. Update manager-api defaults
        update_manager_api_defaults(connection)
        
        # Summary
        print(f"\n{'='*70}")
        print("SUMMARY")
        print('='*70)
        
        if latest_agent_id:
            print("[FIXED] Latest agent now has Story Playback")
        
        if trigger_created:
            print("[OK] Database trigger/procedure created")
        else:
            print("[INFO] Trigger couldn't be created - manual fix needed")
        
        print("\nIMPORTANT:")
        print("The manager-api Java code needs to be updated to")
        print("automatically include SYSTEM_PLUGIN_STORY when")
        print("creating new agents from templates.")
        print("\nUntil then, Story Playback must be added manually")
        print("or via this script after agent creation.")
        
    finally:
        connection.close()

if __name__ == "__main__":
    main()