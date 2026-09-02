import os
import time
import json
import asyncio
import requests
import logging
import re
from bs4 import BeautifulSoup
from config.settings import load_config
from config.logger import setup_logging
from core.utils import llm

TAG = "npr_scraper"
logger = setup_logging()

NEWS_JSON_PATH = os.path.join("data", "news.json")
MAX_ARTICLES = 100

def generate_summary_and_topics(llm_instance, text, title):
    """Summarize text and extract multiple topics using the provided LLM instance."""
    try:
        # Simple heuristic to skip very short articles
        if len(text) < 300:
            return text, ["General"]
            
        system_prompt = (
            "You are a news editor. Read the article and provide:\n"
            "1. A concise summary (80-100 words).\n"
            "2. A list of 1-3 relevant topic tags (e.g., 'Politics', 'Trump', 'Economy', 'World').\n"
            "Format your response exactly as:\n"
            "Topics: [Topic1], [Topic2]\n"
            "Summary: [Summary Content]"
        )
        user_prompt = f"Title: {title}\n\nContent:\n{text[:3000]}" # Truncate to avoid context limits
        
        response = llm_instance.response_no_stream(system_prompt=system_prompt, user_prompt=user_prompt)
        
        # Parse response
        topics = ["General"]
        summary = response
        
        if "Topics:" in response and "Summary:" in response:
            try:
                parts = response.split("Summary:")
                topic_part = parts[0].replace("Topics:", "").strip()
                summary_part = parts[1].strip()
                
                # Parse comma-separated topics
                parsed_topics = [t.strip() for t in topic_part.split(",") if t.strip()]
                if parsed_topics:
                    topics = parsed_topics
                    
                if summary_part:
                    summary = summary_part
            except:
                pass
                
        return summary, topics
    except Exception as e:
        logger.bind(tag=TAG).warning(f"Summarization/Topic extraction failed for '{title}': {e}")
        words = text.split()
        return (" ".join(words[:150]) + "..." if len(words) > 150 else text), ["General"]

def _load_news_json():
    """Load existing news using new schema."""
    if not os.path.exists(NEWS_JSON_PATH):
        return {
            "next_sequence_id": 1000,
            "articles": {},     # ID -> ArticleObj
            "topic_index": {}   # TopicName -> [ID, ID...]
        }
    
    try:
        with open(NEWS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure schema integrity if upgrading from old format
            if "articles" not in data:
                return {
                    "next_sequence_id": 1000,
                    "articles": {},
                    "topic_index": {}
                }
            return data
    except Exception as e:
        logger.bind(tag=TAG).error(f"Failed to load news.json: {e}")
        return {
            "next_sequence_id": 1000,
            "articles": {},
            "topic_index": {}
        }

def _save_news_json(data):
    """Save news data to news.json."""
    try:
        with open(NEWS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.bind(tag=TAG).error(f"Failed to save news.json: {e}")

def _prune_articles(data):
    """
    Enforce MAX_ARTICLES limit using FIFO on Sequence ID.
    If len(articles) > MAX_ARTICLES:
    1. Identify oldest articles by ID.
    2. Remove from 'articles'.
    3. Remove ID from all 'topic_index' lists.
    4. Remove empty topics.
    """
    articles = data.get("articles", {})
    topic_index = data.get("topic_index", {})
    
    current_count = len(articles)
    if current_count <= MAX_ARTICLES:
        return

    logger.bind(tag=TAG).info(f"Pruning articles... Current: {current_count}, Max: {MAX_ARTICLES}")
    
    # Sort IDs (keys are strings in JSON, need int conversion for reliable sorting)
    # But wait, next_sequence_id is int. Keys in json dump are strings.
    # So we sort by int(id)
    sorted_ids = sorted([int(k) for k in articles.keys()])
    
    # Calculate how many to remove
    to_remove_count = current_count - MAX_ARTICLES
    ids_to_remove = sorted_ids[:to_remove_count]
    
    for aid_int in ids_to_remove:
        aid_str = str(aid_int)
        
        # 1. Remove from articles
        if aid_str in articles:
            # title = articles[aid_str].get("title", "Unknown")
            del articles[aid_str]
            
        # 2. Remove from topic_index
        topics_to_delete = []
        for topic, id_list in topic_index.items():
            # Filter out this ID
            # Use int comparison just in case list has ints or strings
            if aid_int in id_list:
                id_list.remove(aid_int)
            elif aid_str in id_list:
                id_list.remove(aid_str)
                
            if not id_list:
                topics_to_delete.append(topic)
                
        # 3. Cleanup empty topics
        for t in topics_to_delete:
            del topic_index[t]

    _save_news_json(data)

def fetch_npr_news():
    """
    Fetches headlines, summarizes, categorizes, and updates news.json.
    """
    logger.bind(tag=TAG).info("Starting NPR news scrape (Relational JSON mode)...")
    
    # Initialize LLM
    try:
        config = load_config()
        select_llm_module = config["selected_module"]["LLM"]
        llm_config = config["LLM"][select_llm_module]
        llm_type = select_llm_module if "type" not in llm_config else llm_config["type"]
        llm_instance = llm.create_instance(llm_type, llm_config)
    except Exception as e:
        logger.bind(tag=TAG).error(f"Failed to initialize LLM: {e}")
        return

    # Load data
    news_data = _load_news_json()
    articles_map = news_data["articles"]
    topic_index = news_data["topic_index"]
    next_seq_id = news_data.get("next_sequence_id", 1000)
    
    # Quick lookup for existing titles
    existing_titles = {art.get("title") for art in articles_map.values()}

    base_url = "https://text.npr.org"
    
    try:
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        topic_container = soup.find("div", class_="topic-container")
        
        if not topic_container:
            return

        links = topic_container.find_all("a", class_="topic-title")
        logger.bind(tag=TAG).info(f"Found {len(links)} articles.")
        
        new_article_count = 0
        current_time = time.time()

        for i, link in enumerate(links):
            title = link.get_text().strip()
            if title in existing_titles:
                continue
                
            href = link.get('href')
            article_url = base_url + href if not href.startswith("http") else href
            
            logger.bind(tag=TAG).info(f"Processing [{i+1}/{len(links)}]: {title}")
            
            try:
                art_resp = requests.get(article_url, timeout=10)
                art_resp.raise_for_status()
                art_soup = BeautifulSoup(art_resp.text, 'html.parser')
                
                # Extract text
                search_root = art_soup.find("div", class_="paragraphs-container") or art_soup.find("main") or art_soup
                elements = search_root.find_all(["p", "h2", "h3"])
                
                article_text = ""
                for el in elements:
                    txt = el.get_text().strip()
                    if not txt or txt.lower() == "text-only version": continue
                    if txt.strip().upper().startswith("TRANSCRIPT"): break
                    article_text += txt + "\n\n"
                
                # LLM Process
                summary, topics_list = generate_summary_and_topics(llm_instance, article_text, title)
                
                # Assign ID
                seq_id = next_seq_id
                next_seq_id += 1
                
                # Create Article Object
                article_obj = {
                    "id": seq_id,
                    "title": title,
                    "url": article_url,
                    "content": summary,
                    "timestamp": current_time,
                    "topics": topics_list
                }
                
                # Update Storage
                articles_map[str(seq_id)] = article_obj
                
                # Update Index
                for topic in topics_list:
                    if topic not in topic_index:
                        topic_index[topic] = []
                    topic_index[topic].append(seq_id)
                
                news_data["next_sequence_id"] = next_seq_id
                new_article_count += 1
                
                time.sleep(0.5)
                
            except Exception as e:
                logger.bind(tag=TAG).error(f"Failed to process '{title}': {e}")
                continue
        
        total_articles = len(news_data.get("articles", {}))
        total_topics = len(news_data.get("topic_index", {}))
        
        if new_article_count > 0:
            _prune_articles(news_data) # This saves internally IF pruning happens
            # Force save if pruning didn't happen (or just save again to be safe)
            _save_news_json(news_data)
            logger.bind(tag=TAG).info(f"Added {new_article_count} new articles. Total: {total_articles}, Topics: {total_topics}")
        else:
            logger.bind(tag=TAG).info(f"No changes. No new articles found. Total: {total_articles}, Topics: {total_topics}")

    except Exception as e:
        logger.bind(tag=TAG).error(f"Scraper error: {e}")

async def news_scraper_task():
    """Background task to run the scraper every hour."""
    logger.bind(tag=TAG).info("NPR Scraper task initialized.")
    loop = asyncio.get_running_loop()
    
    # Run immediately
    await loop.run_in_executor(None, fetch_npr_news)
    
    while True:
        try:
            await asyncio.sleep(3600)
            logger.bind(tag=TAG).info("Running scheduled NPR scrape...")
            await loop.run_in_executor(None, fetch_npr_news)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in scraper loop: {e}")
            await asyncio.sleep(60)
