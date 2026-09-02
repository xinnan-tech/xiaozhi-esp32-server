import os
import re
import json
import time
from typing import List, Dict, Optional
from config.logger import setup_logging

TAG = "news_rag"
logger = setup_logging()

class NewsRAG:
    _instance = None
    _articles_cache = None # ID -> ArticleObj
    _topic_index = None    # Topic -> [ID list]
    _last_load_time = 0
    _stopwords = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NewsRAG, cls).__new__(cls)
            cls._instance._stopwords = {
                "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", 
                "in", "on", "at", "to", "for", "with", "by", "about", "of", "it", 
                "this", "that", "i", "you", "he", "she", "they", "we", "what", 
                "when", "where", "who", "why", "how",
                "me", "my", "myself", "mine", "your", "yours", "yourself", 
                "him", "his", "her", "hers", "its", "our", "ours", "their", "theirs",
                "do", "does", "did", "can", "could", "will", "would", "should", 
                "have", "has", "had", "be", "been", "being",
                "s", "re", "m", "ll", "ve", "d", "t",
                "name", "tell", "say", "ask", "know", "think", "give",
                "hello", "hi", "hey", "goodbye", "bye", "good", "morning", "afternoon", "evening", "night"
            }
        return cls._instance

    def _load_news(self):
        """Load and index news.json if changed"""
        news_path = os.path.join("data", "news.json")
        if not os.path.exists(news_path):
            return {}, {}
            
        mtime = os.path.getmtime(news_path)
        if self._articles_cache is not None and mtime <= self._last_load_time:
            return self._articles_cache, self._topic_index
            
        try:
            with open(news_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Schema: 
            # "articles": {"1001": {...}}, 
            # "topic_index": {"Trump": [1001]}
            
            articles = data.get("articles", {})
            topic_index = data.get("topic_index", {})
            
            # Precompute keywords for each article to speed up search
            for aid, art in articles.items():
                if "keywords" not in art:
                    text_content = f"{art.get('title', '')}\n{art.get('content', '')}"
                    art["keywords"] = self._tokenize(text_content)
            
            self._articles_cache = articles
            self._topic_index = topic_index
            self._last_load_time = mtime
            
            logger.bind(tag=TAG).info(f"Loaded {len(articles)} articles and {len(topic_index)} topics")
            return articles, topic_index
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to load news for RAG: {e}")
            return {}, {}

    def _tokenize(self, text: str) -> set:
        """Simple tokenizer"""
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        tokens = set(text.split())
        return tokens - self._stopwords

    def search(self, query: str, top_k: int = 5) -> str:
        """
        Search news. 
        1. Identify relevant articles by keyword match.
        2. Identify the dominant topics from those articles.
        3. Retrieve full timeline for those topics (evolution).
        """
        articles, topic_index = self._load_news()
        if not articles:
            return ""
            
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return ""
            
        explicit_triggers = {"news", "headline", "headlines", "happening", "current", "events"}
        is_explicit_news_query = len(query_tokens.intersection(explicit_triggers)) > 0
        
        # Dynamic threshold: if query keywords are few, require fewer matches
        # e.g. "Tell me about state" -> "state" (1 token) -> match 1
        # "State Department" -> "state", "department" (2 tokens) -> match 2
        # But maybe safer to cap at 2.
        if is_explicit_news_query:
            threshold = 1
        else:
             threshold = min(2, len(query_tokens))

        # 1. Score articles to find best matches
        scored_articles = []
        for aid, art in articles.items():
            # art["keywords"] precomputed in _load_news
            overlap = len(query_tokens.intersection(art.get("keywords", set())))
            if overlap >= threshold:
                scored_articles.append((overlap, art))
        
        scored_articles.sort(key=lambda x: x[0], reverse=True)
        
        # If no specific matches, handle generic "news" query
        if not scored_articles:
            if "news" in query_tokens:
                # Return latest 3 articles (sorted by ID decending)
                # Assuming larger ID = newer
                sorted_ids = sorted([int(k) for k in articles.keys()], reverse=True)[:3]
                latest_arts = [articles[str(i)] for i in sorted_ids if str(i) in articles]
                
                if latest_arts:
                    out = "\n\n---\nLATEST NEWS HEADLINES:\n"
                    for art in latest_arts:
                        ts = time.strftime('%Y-%m-%d', time.localtime(art.get('timestamp', time.time())))
                        out += f"Title: {art.get('title')}\nDate: {ts}\nSummary: {art.get('content')}\n\n"
                    out += "---\n"
                    return out
            return ""

        # 2. Identify Dominant Topic
        # We take the BEST matching article, and look at its topics.
        best_match_art = scored_articles[0][1]
        best_topics = best_match_art.get("topics", [])
        
        if not best_topics:
            # Fallback: just return the single article
            return f"\n\n---\nRELEVANT NEWS:\nTitle: {best_match_art.get('title')}\nSummary: {best_match_art.get('content')}\n---\n"
            
        # Pick the first topic as primary (or valid approach: merge all articles from all its topics?)
        # Let's pick the first one for now as "Primary Topic"
        target_topic = best_topics[0]
        
        # 3. Retrieve Timeline
        if target_topic in topic_index:
            art_ids = topic_index[target_topic]
            # Convert to ints for sorting
            art_ids_int = [int(i) for i in art_ids]
            art_ids_int.sort() # Oldest to Newest
            
            # Limit to context window (e.g., last 3 articles)
            relevant_ids = art_ids_int[-3:]
            
            timeline_arts = []
            for i in relevant_ids:
                if str(i) in articles:
                    timeline_arts.append(articles[str(i)])
            
            out = f"\n\n---\nNEWS TIMELINE (Topic: {target_topic}):\n"
            for art in timeline_arts:
                ts = time.strftime('%Y-%m-%d', time.localtime(art.get('timestamp', time.time())))
                out += f"\n[{ts}] {art.get('title')}\n{art.get('content')}\n"
            out += "\n---\n"
            return out
            
        return ""

news_rag = NewsRAG()
