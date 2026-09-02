import os
import json
import re
from typing import List, Dict, Optional
from config.logger import setup_logging

TAG = "history_rag"
logger = setup_logging()

class HistoryRAG:
    _instance = None
    _cache = {}  # {client_id: {"mtime": float, "chunks": List[Dict]}}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HistoryRAG, cls).__new__(cls)
            cls._instance.stopwords = {
                "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", 
                "in", "on", "at", "to", "for", "with", "by", "about", "of", "it", 
                "this", "that", "i", "you", "he", "she", "they", "we", "what", 
                "when", "where", "who", "why", "how",
                "me", "my", "myself", "mine", "your", "yours", "yourself", 
                "him", "his", "her", "hers", "its", "our", "ours", "their", "theirs",
                "do", "does", "did", "can", "could", "will", "would", "should", 
                "have", "has", "had", "be", "been", "being",
                "s", "re", "m", "ll", "ve", "d", "t"
            }
        return cls._instance

    def _load_history(self, client_id: str):
        """Load and chunk memory.json for a specific client if changed"""
        memory_path = os.path.join("data", client_id, "memory.json")
        if not os.path.exists(memory_path):
            return []
            
        mtime = os.path.getmtime(memory_path)
        
        # Check cache
        if client_id in self._cache:
            cache_entry = self._cache[client_id]
            if mtime <= cache_entry["mtime"]:
                return cache_entry["chunks"]
            
        try:
            with open(memory_path, "r", encoding="utf-8") as f:
                history_data = json.load(f)
                
            if not isinstance(history_data, list):
                return []

            chunks = []
            
            for session in history_data:
                session_timestamp = session.get("timestamp", "")
                messages = session.get("messages", [])
                
                # Pair up User and Assistant messages roughly
                # Or just treat each relevant message as a chunk
                # For context, it's nice to have the response.
                
                for i, msg in enumerate(messages):
                    role = msg.get("role")
                    content = msg.get("content")
                    
                    if role == "system" or not content:
                        continue
                        
                    # Clean content
                    # 1. Remove News Context if present
                    if "\n\n\n---\nRELEVANT NEWS CONTEXT:" in content:
                        content = content.split("\n\n\n---\nRELEVANT NEWS CONTEXT:")[0]

                    # 2. Remove History RAG Context if present
                    content = re.sub(r'<history_rag>.*?</history_rag>', '', content, flags=re.DOTALL)
                    
                    # 3. Parse JSON if it looks like JSON (User messages are often JSON)
                    if content.strip().startswith("{") and "\"content\":" in content:
                        try:
                            data = json.loads(content)
                            if "content" in data:
                                content = data["content"]
                        except:
                            pass
                            
                    if not content.strip():
                        continue

                    # Precompute keywords
                    keywords = self._tokenize(content)
                    if not keywords:
                        continue
                        
                    chunks.append({
                        "session_date": session_timestamp[:10] if session_timestamp else "Unknown Date",
                        "role": role,
                        "content": content,
                        "keywords": keywords,
                        "full_text": f"[{session_timestamp[:16]}] {role}: {content}" 
                    })
                
            # Update cache
            self._cache[client_id] = {
                "mtime": mtime,
                "chunks": chunks
            }
            logger.bind(tag=TAG).debug(f"Loaded {len(chunks)} history items for {client_id}")
            return chunks
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to load history for {client_id}: {e}")
            return []

    def _tokenize(self, text: str) -> set:
        """Simple tokenizer: lower, remove punct, remove stopwords"""
        # Remove JSON artifacts if any (sometimes content is a JSON string)
        # But usually it's cleaned text.
        
        # Handle JSON content strings like '{"content": "..."}'
        if text.strip().startswith("{") and "content" in text:
             try:
                 data = json.loads(text)
                 if "content" in data:
                     text = data["content"]
             except:
                 pass
        
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        tokens = set(text.split())
        return tokens - self.stopwords

    def search(self, query: str, client_id: str, top_k: int = 3) -> str:
        """Search history for relevant context"""
        if not client_id:
            return ""
            
        chunks = self._load_history(client_id)
        if not chunks:
            return ""
            
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return ""
            
        # For history, even 1 keyword overlap can be significant (e.g. "chickens")
        # provided it's not a stopword.
        threshold = 1
        
        scored_chunks = []
        for chunk in chunks:
            overlap = len(query_tokens.intersection(chunk["keywords"]))
            if overlap >= threshold:
                scored_chunks.append((overlap, chunk))
        
        # Sort by score desc, then by date (implicitly via list order? No, list is historical order)
        # We want most relevant first. If tie, maybe most recent?
        # Let's sort by score (desc), then index (desc) to prefer recent.
        # But 'chunk' doesn't have index explicitly, but they are appended in order.
        # So stable sort by score will keep order. But we want Recent history if scores are equal.
        # So let's reverse chunks list before processing? 
        # Actually, let's just sort by score.
        
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        
        # Take top K
        results = []
        for score, chunk in scored_chunks[:top_k]:
            results.append(chunk["full_text"])
            
        if results:
            return "\n\n<history_rag>\n" + "\n".join(results) + "\n</history_rag>\n"
            
        return ""

history_rag = HistoryRAG()
