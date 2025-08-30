#!/usr/bin/env python3
"""
Verify all existing agents have Story Playback and check for issues
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

def check_all_agents_story_status(connection):
    """Check if all agents have Story Playback"""
    cursor = connection.cursor()
    try:
        print("\n1. Checking ALL Agents for Story Playback...")
        print("=" * 60)
        
        # Get all agents with their Story Playback status
        cursor.execute("""
            SELECT 
                a.id,
                a.agent_name,
                a.agent_code,
                a.created_at,
                CASE 
                    WHEN apm_story.plugin_id IS NOT NULL THEN 'YES'
                    ELSE 'NO'
                END as has_story_playback,
                apm_story.param_info as story_params
            FROM ai_agent a
            LEFT JOIN ai_agent_plugin_mapping apm_story 
                ON a.id = apm_story.agent_id 
                AND apm_story.plugin_id = 'SYSTEM_PLUGIN_STORY'
            ORDER BY a.created_at DESC
        """)
        
        agents = cursor.fetchall()
        
        print(f"Total agents in database: {len(agents)}\n")
        
        agents_with_story = 0
        agents_without_story = []
        
        for agent in agents:
            agent_id, agent_name, agent_code, created_at, has_story, story_params = agent
            
            if has_story == 'YES':
                agents_with_story += 1
                status = "[OK]"
            else:
                agents_without_story.append((agent_id, agent_name))
                status = "[MISSING]"
            
            print(f"{status} {agent_name or agent_code} (ID: {agent_id[:8]}...)")
            print(f"     Created: {created_at}")
            print(f"     Story Playback: {has_story}")
            if story_params:
                try:
                    params = json.loads(story_params)
                    print(f"     Params: {params}")
                except:
                    print(f"     Params: {story_params[:50]}...")
            print()
        
        print(f"\nSUMMARY:")
        print(f"Agents WITH Story Playback: {agents_with_story}")
        print(f"Agents WITHOUT Story Playback: {len(agents_without_story)}")
        
        return agents_without_story
        
    except Error as e:
        print(f"Error checking agents: {e}")
        return []
    finally:
        cursor.close()

def fix_agents_without_story(connection, agents_without_story):
    """Add Story Playback to agents that don't have it"""
    if not agents_without_story:
        print("\nAll agents already have Story Playback!")
        return True
    
    cursor = connection.cursor()
    try:
        print(f"\n2. Fixing {len(agents_without_story)} agents without Story Playback...")
        print("=" * 60)
        
        param_info = {
            "story_dir": "./stories",
            "story_ext": ".mp3;.wav;.m4a",
            "refresh_time": "300"
        }
        
        fixed_count = 0
        for agent_id, agent_name in agents_without_story:
            try:
                # Check if mapping already exists (shouldn't, but double-check)
                cursor.execute("""
                    SELECT id FROM ai_agent_plugin_mapping 
                    WHERE agent_id = %s AND plugin_id = 'SYSTEM_PLUGIN_STORY'
                """, (agent_id,))
                
                if cursor.fetchone():
                    print(f"Mapping already exists for {agent_name}, skipping...")
                    continue
                
                # Add Story Playback
                cursor.execute("""
                    INSERT INTO ai_agent_plugin_mapping 
                    (agent_id, plugin_id, param_info)
                    VALUES (%s, %s, %s)
                """, (agent_id, "SYSTEM_PLUGIN_STORY", json.dumps(param_info)))
                
                print(f"[FIXED] Added Story Playback to: {agent_name}")
                fixed_count += 1
                
            except Error as e:
                print(f"[ERROR] Failed to fix {agent_name}: {e}")
        
        connection.commit()
        print(f"\nFixed {fixed_count} agents!")
        return True
        
    except Error as e:
        print(f"Error fixing agents: {e}")
        connection.rollback()
        return False
    finally:
        cursor.close()

def check_duplicate_agent_issues(connection):
    """Check for duplicate agent names or codes that might cause the error"""
    cursor = connection.cursor()
    try:
        print("\n3. Checking for Duplicate Agent Issues...")
        print("=" * 60)
        
        print("\nThe error message suggests: 'Record already exists in database'")
        print("This usually means duplicate agent_name or agent_code\n")
        
        # Check for duplicate agent names
        cursor.execute("""
            SELECT agent_name, COUNT(*) as count
            FROM ai_agent
            WHERE agent_name IS NOT NULL
            GROUP BY agent_name
            HAVING COUNT(*) > 1
        """)
        
        duplicate_names = cursor.fetchall()
        
        if duplicate_names:
            print("Found duplicate agent names:")
            for name, count in duplicate_names:
                print(f"  - '{name}' appears {count} times")
        else:
            print("No duplicate agent names found")
        
        # Check for duplicate agent codes
        cursor.execute("""
            SELECT agent_code, COUNT(*) as count
            FROM ai_agent
            WHERE agent_code IS NOT NULL
            GROUP BY agent_code
            HAVING COUNT(*) > 1
        """)
        
        duplicate_codes = cursor.fetchall()
        
        if duplicate_codes:
            print("\nFound duplicate agent codes:")
            for code, count in duplicate_codes:
                print(f"  - '{code}' appears {count} times")
        else:
            print("No duplicate agent codes found")
        
        # Check unique constraints
        cursor.execute("""
            SELECT 
                CONSTRAINT_NAME,
                COLUMN_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = 'railway'
            AND TABLE_NAME = 'ai_agent'
            AND CONSTRAINT_NAME != 'PRIMARY'
        """)
        
        constraints = cursor.fetchall()
        
        if constraints:
            print("\nUnique constraints on ai_agent table:")
            for constraint_name, column_name in constraints:
                print(f"  - {constraint_name} on column: {column_name}")
        
        # Get recent agents to see naming pattern
        cursor.execute("""
            SELECT agent_name, agent_code, created_at
            FROM ai_agent
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        recent_agents = cursor.fetchall()
        
        print("\nMost recent agents (to check naming pattern):")
        for name, code, created in recent_agents:
            print(f"  - Name: '{name}', Code: '{code}', Created: {created}")
        
        print("\nRECOMMENDATION:")
        print("When creating a new agent, ensure:")
        print("1. The agent_name is unique")
        print("2. The agent_code is unique")
        print("3. Try adding a timestamp or random suffix to make it unique")
        
    except Error as e:
        print(f"Error checking duplicates: {e}")
    finally:
        cursor.close()

def check_all_plugins_for_agents(connection):
    """Check what plugins each agent has"""
    cursor = connection.cursor()
    try:
        print("\n4. Checking All Plugins for Each Agent...")
        print("=" * 60)
        
        cursor.execute("""
            SELECT 
                a.agent_name,
                GROUP_CONCAT(
                    CASE 
                        WHEN apm.plugin_id = 'SYSTEM_PLUGIN_STORY' THEN 'Story'
                        WHEN apm.plugin_id = 'SYSTEM_PLUGIN_MUSIC' THEN 'Music'
                        WHEN apm.plugin_id = 'SYSTEM_PLUGIN_WEATHER' THEN 'Weather'
                        WHEN apm.plugin_id LIKE '%NEWS%' THEN 'News'
                        ELSE SUBSTRING(apm.plugin_id, 15)
                    END
                    ORDER BY apm.plugin_id
                    SEPARATOR ', '
                ) as plugins
            FROM ai_agent a
            LEFT JOIN ai_agent_plugin_mapping apm ON a.id = apm.agent_id
            GROUP BY a.id, a.agent_name
            ORDER BY a.created_at DESC
        """)
        
        results = cursor.fetchall()
        
        print("Agent Plugin Summary:")
        for agent_name, plugins in results:
            if plugins:
                if 'Story' in plugins:
                    story_status = "[Has Story]"
                else:
                    story_status = "[NO STORY!]"
                print(f"{story_status} {agent_name}: {plugins}")
            else:
                print(f"[NO PLUGINS] {agent_name}: No plugins configured")
        
    except Error as e:
        print(f"Error checking plugins: {e}")
    finally:
        cursor.close()

def main():
    print("Comprehensive Agent Story Playback Verification")
    print("=" * 70)
    
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        # 1. Check all agents for Story Playback
        agents_without_story = check_all_agents_story_status(connection)
        
        # 2. Fix agents without Story Playback
        if agents_without_story:
            fix_agents_without_story(connection, agents_without_story)
        
        # 3. Check for duplicate issues
        check_duplicate_agent_issues(connection)
        
        # 4. Check all plugins
        check_all_plugins_for_agents(connection)
        
        # Final verification
        print(f"\n{'='*70}")
        print("FINAL STATUS")
        print('='*70)
        
        if not agents_without_story:
            print("[SUCCESS] All agents have Story Playback!")
        else:
            print(f"[FIXED] Added Story Playback to {len(agents_without_story)} agents")
        
        print("\nRegarding the error when creating new agents:")
        print("Error: 'Record already exists in database'")
        print("This means you're trying to create an agent with a name or code")
        print("that already exists. Use a unique name/code for new agents.")
        
    finally:
        connection.close()

if __name__ == "__main__":
    main()