#!/usr/bin/env python3
"""
Final script to fix Story Playback function placement
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

def check_agents_and_templates(connection):
    """Check both agent templates and actual agents"""
    cursor = connection.cursor()
    try:
        print("\n1. Checking agent templates...")
        cursor.execute("SELECT id, agent_name FROM ai_agent_template")
        templates = cursor.fetchall()
        
        print(f"Found {len(templates)} agent templates:")
        for template in templates:
            print(f"  Template ID: {template[0]}, Name: {template[1]}")
        
        print("\n2. Checking actual agents...")
        cursor.execute("SELECT id, agent_name FROM ai_agent")
        agents = cursor.fetchall()
        
        print(f"Found {len(agents)} agents:")
        for agent in agents:
            print(f"  Agent ID: {agent[0]}, Name: {agent[1]}")
        
        print("\n3. Checking current Story Playback mappings...")
        cursor.execute("""
            SELECT agent_id, param_info FROM ai_agent_plugin_mapping 
            WHERE plugin_id = 'SYSTEM_PLUGIN_STORY'
        """)
        story_mappings = cursor.fetchall()
        
        print(f"Found {len(story_mappings)} existing Story Playback mappings:")
        for mapping in story_mappings:
            print(f"  Agent ID: {mapping[0]}")
            
        return agents, templates, story_mappings
        
    except Error as e:
        print(f"Error checking agents and templates: {e}")
        return [], [], []
    finally:
        cursor.close()

def add_missing_story_playback_mappings(connection, agents, story_mappings):
    """Add Story Playback to agents that don't have it"""
    cursor = connection.cursor()
    try:
        # Get list of agent IDs that already have Story Playback
        existing_story_agent_ids = [mapping[0] for mapping in story_mappings]
        
        # Default parameters for Story Playback plugin
        param_info = {
            "story_dir": "./stories",
            "story_ext": ".mp3;.wav;.m4a",
            "refresh_time": "300"
        }
        
        updates_made = 0
        
        print(f"\n4. Adding Story Playback to agents without it...")
        
        for agent_id, agent_name in agents:
            if agent_id not in existing_story_agent_ids:
                print(f"Adding Story Playback to: {agent_name} (ID: {agent_id})")
                
                cursor.execute("""
                    INSERT INTO ai_agent_plugin_mapping 
                    (agent_id, plugin_id, param_info)
                    VALUES (%s, %s, %s)
                """, (agent_id, "SYSTEM_PLUGIN_STORY", json.dumps(param_info)))
                
                updates_made += 1
                print(f"  Added successfully")
            else:
                print(f"Already has Story Playback: {agent_name} (ID: {agent_id})")
        
        if updates_made > 0:
            connection.commit()
            print(f"\nCommitted {updates_made} new Story Playback mappings to database")
        else:
            print(f"\nNo updates needed - all agents already have Story Playback")
            
        return updates_made
        
    except Error as e:
        print(f"Error adding Story Playback mappings: {e}")
        connection.rollback()
        return 0
    finally:
        cursor.close()

def verify_final_state(connection):
    """Verify all agents now have Story Playback"""
    cursor = connection.cursor()
    try:
        print(f"\n5. Final verification...")
        
        cursor.execute("""
            SELECT 
                a.id,
                a.agent_name,
                CASE WHEN apm.plugin_id IS NOT NULL THEN 'YES' ELSE 'NO' END as has_story_playback
            FROM ai_agent a
            LEFT JOIN ai_agent_plugin_mapping apm 
                ON a.id = apm.agent_id AND apm.plugin_id = 'SYSTEM_PLUGIN_STORY'
            ORDER BY a.agent_name
        """)
        
        results = cursor.fetchall()
        
        total_agents = len(results)
        with_story_playback = sum(1 for result in results if result[2] == 'YES')
        
        print(f"\nFinal Story Playback status:")
        for result in results:
            agent_id, agent_name, has_playback = result
            status_symbol = "[YES]" if has_playback == 'YES' else "[NO] "
            print(f"  {status_symbol} {agent_name}")
        
        print(f"\nSUMMARY:")
        print(f"Total agents: {total_agents}")
        print(f"With Story Playback: {with_story_playback}")
        
        if with_story_playback == total_agents:
            print("SUCCESS: All agents now have Story Playback function!")
        else:
            print(f"WARNING: {total_agents - with_story_playback} agents still missing Story Playback")
            
        return with_story_playback == total_agents
        
    except Error as e:
        print(f"Error verifying final state: {e}")
        return False
    finally:
        cursor.close()

def main():
    print("Fixing Story Playback function for all agents")
    print("=" * 50)
    
    connection = connect_to_database()
    if not connection:
        return
    
    try:
        # Check current state
        agents, templates, story_mappings = check_agents_and_templates(connection)
        
        if not agents:
            print("ERROR: No agents found in database!")
            return
        
        # Add Story Playback to agents that don't have it
        updates_made = add_missing_story_playback_mappings(connection, agents, story_mappings)
        
        # Verify the final state
        success = verify_final_state(connection)
        
        if success:
            print("\nMission accomplished! All agents now have access to Story Playback function.")
        else:
            print("\nSome issues remain. Please check the output above.")
            
    finally:
        if connection.is_connected():
            connection.close()
            print(f"\nDatabase connection closed")

if __name__ == "__main__":
    main()