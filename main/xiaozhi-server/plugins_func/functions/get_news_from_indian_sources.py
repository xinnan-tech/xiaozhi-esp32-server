import random
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action

TAG = __name__
logger = setup_logging()

# Indian news RSS sources
INDIAN_NEWS_SOURCES = {
    "times_of_india": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "hindu": "https://www.thehindu.com/feeder/default.rss",
    "indian_express": "https://indianexpress.com/feed/",
    "ndtv": "https://feeds.feedburner.com/ndtvnews-top-stories",
    "hindustan_times": "https://www.hindustantimes.com/feeds/rss/news/rssfeed.xml",
    "economic_times": "https://economictimes.indiatimes.com/rssfeedstopstories.cms",
    "business_standard": "https://www.business-standard.com/rss/home_page_top_stories.rss",
    "india_today": "https://www.indiatoday.in/rss/1206578",
    "news18": "https://www.news18.com/rss/india.xml",
    "zee_news": "https://zeenews.india.com/rss/india-national-news.xml"
}

GET_INDIAN_NEWS_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_indian_news",
        "description": (
            "Get latest Indian news from major Indian news sources like Times of India, The Hindu, Indian Express, NDTV, etc. "
            "Randomly selects one news item for broadcast. Users can specify news source or category. "
            "Users can request detailed content for more information."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Indian news source, e.g., Times of India, The Hindu, Indian Express, NDTV, Economic Times. Optional parameter",
                },
                "detail": {
                    "type": "boolean",
                    "description": "Whether to get detailed content, defaults to false",
                },
                "lang": {
                    "type": "string",
                    "description": "Language code for response, defaults to en_US",
                },
            },
            "required": ["lang"],
        },
    },
}


def fetch_indian_news_from_rss(rss_url):
    """Fetch news from Indian RSS sources"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(rss_url, headers=headers, timeout=15)
        response.raise_for_status()

        # Parse XML
        root = ET.fromstring(response.content)
        news_items = []

        for item in root.findall(".//item"):
            title = item.find("title").text if item.find(
                "title") is not None else "No title"
            link = item.find("link").text if item.find(
                "link") is not None else "#"
            description = item.find("description").text if item.find(
                "description") is not None else "No description"
            pubDate = item.find("pubDate").text if item.find(
                "pubDate") is not None else "Unknown time"

            # Clean HTML from description
            if description and description != "No description":
                soup = BeautifulSoup(description, "html.parser")
                description = soup.get_text().strip()

            news_items.append({
                "title": title,
                "link": link,
                "description": description,
                "pubDate": pubDate,
            })

        return news_items

    except Exception as e:
        logger.bind(tag=TAG).error(f"Failed to fetch Indian RSS news: {e}")
        return []


def fetch_indian_news_detail(url):
    """Fetch detailed content from Indian news websites"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # Common selectors for Indian news sites
        content_selectors = [
            ".story-content",  # Times of India
            ".article-content",  # The Hindu
            ".full-details",   # Indian Express
            ".ins_storybody",  # NDTV
            ".detail-body",    # Hindustan Times
            ".artText",        # Economic Times
            "article",         # Generic
            ".content",        # Generic
        ]

        content = ""
        for selector in content_selectors:
            content_div = soup.select_one(selector)
            if content_div:
                paragraphs = content_div.find_all("p")
                content = "\n".join([p.get_text().strip()
                                    for p in paragraphs if p.get_text().strip()])
                break

        if not content:
            # Fallback: get all paragraphs
            paragraphs = soup.find_all("p")
            content = "\n".join([p.get_text().strip()
                                for p in paragraphs if p.get_text().strip()])

        return content[:2000] if content else "Unable to extract content"

    except Exception as e:
        logger.bind(tag=TAG).error(f"Failed to fetch Indian news details: {e}")
        return "Unable to get detailed content"


@register_function("get_indian_news", GET_INDIAN_NEWS_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def get_indian_news(conn, source: str = "Times of India", detail: bool = False, lang: str = "en_US"):
    """Get Indian news and randomly select one for broadcast"""
    try:
        # If detail is True, get detailed content of previous news
        if detail:
            if not hasattr(conn, "last_indian_news_link") or not conn.last_indian_news_link:
                return ActionResponse(
                    Action.REQLLM,
                    "Sorry, no recent Indian news query found, please get a news item first.",
                    None,
                )

            url = conn.last_indian_news_link.get("link")
            title = conn.last_indian_news_link.get("title", "Unknown title")

            if not url or url == "#":
                return ActionResponse(
                    Action.REQLLM,
                    "Sorry, this news has no available link to get detailed content.",
                    None
                )

            logger.bind(tag=TAG).info(f"Fetching Indian news details: {title}")
            detail_content = fetch_indian_news_detail(url)

            detail_report = (
                f"Based on the following data, respond to user's Indian news detail query in {lang}:\n\n"
                f"News title: {title}\n"
                f"Detailed content: {detail_content}\n\n"
                f"(Please summarize this Indian news content and present it naturally to the user)"
            )

            return ActionResponse(Action.REQLLM, detail_report, None)

        # Map source name to RSS URL
        source_key = None
        source_lower = source.lower().replace(" ", "_")

        for key in INDIAN_NEWS_SOURCES.keys():
            if key.replace("_", " ").lower() in source.lower() or source.lower() in key.replace("_", " ").lower():
                source_key = key
                break

        if not source_key:
            source_key = "times_of_india"  # Default to Times of India
            source = "Times of India"

        rss_url = INDIAN_NEWS_SOURCES[source_key]

        logger.bind(tag=TAG).info(
            f"Fetching Indian news from {source}: {rss_url}")

        # Fetch news
        news_items = fetch_indian_news_from_rss(rss_url)
        if not news_items:
            return ActionResponse(
                Action.REQLLM,
                f"Sorry, failed to get news from {source}, please try again later.",
                None,
            )

        # Randomly select one news item
        selected_news = random.choice(news_items)

        # Save for detail queries
        if not hasattr(conn, "last_indian_news_link"):
            conn.last_indian_news_link = {}
        conn.last_indian_news_link = {
            "link": selected_news.get("link", "#"),
            "title": selected_news.get("title", "Unknown title"),
        }

        # Build news report
        news_report = (
            f"Based on the following data, respond to user's Indian news query in {lang}:\n\n"
            f"News source: {source}\n"
            f"News title: {selected_news['title']}\n"
            f"Published: {selected_news['pubDate']}\n"
            f"Summary: {selected_news['description']}\n\n"
            f"(Please present this Indian news to the user naturally. "
            f"If user wants more details, they can ask for detailed content.)"
        )

        return ActionResponse(Action.REQLLM, news_report, None)

    except Exception as e:
        logger.bind(tag=TAG).error(f"Error getting Indian news: {e}")
        return ActionResponse(
            Action.REQLLM,
            "Sorry, an error occurred while getting Indian news, please try again later.",
            None
        )
