from ddgs import DDGS
from config.logger import setup_logging

TAG = "web_search"
logger = setup_logging()

class WebSearch:
    def __init__(self, config: dict):
        self.config = config
        self.plugin_config = config.get("plugins", {}).get("web_search", {})
        self.count = self.plugin_config.get("count", 5)

    def search(self, query: str) -> str:
        """Perform a web search using DuckDuckGo (via ddgs) and return a formatted string of results."""
        logger.bind(tag=TAG).info(f"Searching DuckDuckGo for: {query}")
        try:
            results = []
            with DDGS(timeout=10) as ddgs:
                ddgs_gen = ddgs.text(query, max_results=self.count)
                for r in ddgs_gen:
                    results.append(r)
            
            logger.bind(tag=TAG).info(f"DuckDuckGo found {len(results)} results")
            
            if not results:
                logger.bind(tag=TAG).warning(f"No results found for query: {query}")
                return "No search results found via DuckDuckGo."

            formatted_results = []
            for i, res in enumerate(results):
                title = res.get("title", "No Title")
                url = res.get("href", "No URL")
                snippet = res.get("body", "No Snippet")
                logger.bind(tag=TAG).debug(f"Result {i+1}: {title} ({url})")
                formatted_results.append(f"Title: {title}\nURL: {url}\nSnippet: {snippet}")

            return "\n\n<web_search_context>\n" + "\n---\n".join(formatted_results) + "\n</web_search_context>\n"

        except Exception as e:
            logger.bind(tag=TAG).error(f"DuckDuckGo search failed for query '{query}': {e}")
            return f"Search failed (DuckDuckGo): {str(e)}"

def perform_web_search(query: str, config: dict) -> str:
    """Helper function to perform web search."""
    searcher = WebSearch(config)
    return searcher.search(query)
