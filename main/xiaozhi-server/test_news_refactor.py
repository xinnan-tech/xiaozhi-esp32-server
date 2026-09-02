import sys
import os
import json
import logging
from unittest.mock import MagicMock

# Setup path
sys.path.insert(0, os.getcwd())

# Mock logger
logging.basicConfig(level=logging.INFO)

# --- MOCKING DEPENDENCIES TO AVOID IMPORT ERRORS ---
# We need to mock these before npr_scraper uses them
import core.utils.llm
import config.settings

class MockLLM:
    def response_no_stream(self, system_prompt, user_prompt):
        # Return a valid mock response matching the expected format
        return "Topics: Politics, TestTopic\nSummary: This is a mocked summary of the article. It talks about important events."

def mock_load_config():
    return {
        "selected_module": {"LLM": "mock"},
        "LLM": {"mock": {"type": "mock"}}
    }

# Apply mocks
core.utils.llm.create_instance = lambda *args: MockLLM()
config.settings.load_config = mock_load_config

# Now import modules under test
from core.utils import npr_scraper
# Patch the imported function in npr_scraper namespace
npr_scraper.load_config = mock_load_config

from core.utils.npr_scraper import fetch_npr_news
from core.utils.news_rag import news_rag

def test_refactor():
    print(f"CWD: {os.getcwd()}")
    abs_path = os.path.abspath("data/news.json")
    print(f"Target Path: {abs_path}")
    print(f"Scraper Module Path: {npr_scraper.NEWS_JSON_PATH}")
    print(f"Scraper Module Absolute Path: {os.path.abspath(npr_scraper.NEWS_JSON_PATH)}")

    if os.path.exists("data"):
        print(f"Data dir contents: {os.listdir('data')}")
        # Try writing a test file
        try:
            with open("data/test_write.txt", "w") as f:
                f.write("test")
            print("Successfully wrote data/test_write.txt")
        except Exception as e:
            print(f"Failed to write test file: {e}")
    else:
        print("Data dir NOT found!")

    print("--> 1. Running Scraper...")
    try:
        fetch_npr_news()
        print("Scraper completed.")
        
        # DEBUG: Check directory AFTER run
        if os.path.exists("data"):
             print(f"Data dir contents AFTER scrape: {os.listdir('data')}")
        else:
             print("Data dir disappeared?!")
             
    except Exception as e:
        print(f"Scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return

    print("--> 2. Checking JSON file...")
    if os.path.exists("data/news.json"):
        with open("data/news.json", "r") as f:
            data = json.load(f)
            # Schema: articles, topic_index, next_sequence_id
            articles = data.get("articles", {})
            topic_index = data.get("topic_index", {})
            
            print(f"JSON loaded. Article count: {len(articles)}")
            print(f"Topic count: {len(topic_index)}")
            print(f"Sample topics: {list(topic_index.keys())[:5]}")
            
            # Check for dummy entries from mock
            print(f"Example article keys: {list(articles.keys())[:3]}")
            
            if topic_index:
                first_topic = list(topic_index.keys())[0]
                ids = topic_index[first_topic]
                print(f"IDs in '{first_topic}': {ids}")
                
    else:
        print(f"data/news.json not found! Checked: {abs_path}")
        return

    print("--> 3. Testing RAG Search...")
    # Test 1: Generic News (Expect Latest)
    print("Search 'news':")
    res = news_rag.search("What is the news today?")
    print(f"Result length: {len(res)}")
    print(res[:300] + "..." if len(res) > 300 else res)
    
    # Test 2: Specific Topic (Dynamic based on what we fetched)
    if topic_index:
        test_topic = list(topic_index.keys())[0]
        # Get an article ID from this topic
        if topic_index[test_topic]:
            article_id = str(topic_index[test_topic][0])
            if article_id in articles:
                title_word = articles[article_id]["title"].split()[0]
                print(f"\nSearch '{title_word}' (expecting topic '{test_topic}'):")
                res = news_rag.search(f"Tell me about {title_word}")
                print(f"Result length: {len(res)}")
                print(res[:600] + "..." if len(res) > 600 else res)

if __name__ == "__main__":
    test_refactor()
