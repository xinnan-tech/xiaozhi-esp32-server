import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
import core.utils.cache.manager as cache_module

TAG = __name__
logger = setup_logging()

GET_NEWS_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_news",
        "description": (
            "Get the latest news from major news sources (Reuters, CNN, BBC, Guardian, etc.), "
            "randomly selecting one news item for broadcast. Supports multiple categories including world news, "
            "technology, business, sports, health, politics, and science. Uses multiple news sources with "
            "automatic fallback for reliability. Users can request detailed content for full article text."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "News category: world/international, technology/tech, business/finance, sports, health/medical, politics, science. Optional parameter, defaults to world news",
                },
                "detail": {
                    "type": "boolean",
                    "description": "Whether to get detailed content, defaults to false. If true, gets detailed content of the last news item",
                },
                "lang": {
                    "type": "string",
                    "description": "Language code for user response, e.g., en_US/zh_CN/zh_HK/ja_JP, defaults to en_US",
                },
            },
            "required": ["lang"],
        },
    },
}


def fetch_news_from_rss(rss_url):
    """Fetch news list from RSS feed"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(rss_url, headers=headers, timeout=10)
        response.raise_for_status()

        # Parse XML
        root = ET.fromstring(response.content)

        # Find all item elements (news items)
        news_items = []
        for item in root.findall(".//item"):
            title = (
                item.find("title").text if item.find("title") is not None else "No Title"
            )
            link = item.find("link").text if item.find("link") is not None else "#"
            description = (
                item.find("description").text
                if item.find("description") is not None
                else "No Description"
            )
            pubDate = (
                item.find("pubDate").text
                if item.find("pubDate") is not None
                else "Unknown Date"
            )

            news_items.append(
                {
                    "title": title,
                    "link": link,
                    "description": description,
                    "pubDate": pubDate,
                }
            )

        return news_items
    except Exception as e:
        logger.bind(tag=TAG).error(f"Failed to fetch RSS news: {e}")
        return []


def fetch_news_detail(url):
    """Fetch news detail page content and summarize"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "header", "footer", "aside", "advertisement", "ads"]):
            element.decompose()

        # Enhanced content selectors for major news sites
        content_selectors = [
            # Reuters
            "[data-testid='paragraph']",
            ".StandardArticleBody_body",
            ".ArticleBodyWrapper",
            # CNN
            ".article__content",
            ".zn-body__paragraph",
            "[data-module='ArticleBody']",
            # BBC
            "[data-component='text-block']",
            ".ssrcss-1ocoo3l-Wrap",
            ".StoryBody",
            # Guardian
            "[data-testid='article-body']",
            ".article-body-commercial-selector",
            # NYT
            "[data-testid='article-content']",
            ".css-53u6y8",
            # Generic selectors
            "article .story-body",
            "article .article-body", 
            "article .content",
            ".article-content",
            ".story-content",
            ".entry-content",
            "article p",
            ".content p",
            "[data-module='ArticleBody']",
            ".ArticleBody",
            "main p",
            ".main-content p"
        ]
        
        content_div = None
        for selector in content_selectors:
            content_div = soup.select_one(selector)
            if content_div:
                logger.bind(tag=TAG).debug(f"Found content with selector: {selector}")
                break
        
        # If found a container, get paragraphs from it
        if content_div:
            paragraphs = content_div.find_all("p")
            if not paragraphs:
                # Try to get text directly from the container
                content = content_div.get_text(separator='\n', strip=True)
            else:
                content = "\n".join(
                    [p.get_text().strip() for p in paragraphs if p.get_text().strip()]
                )
        else:
            # Fallback: try to get all paragraphs from the page
            paragraphs = soup.find_all("p")
            content = "\n".join(
                [p.get_text().strip() for p in paragraphs if p.get_text().strip()]
            )
            
        # Clean up content
        if content:
            # Remove excessive whitespace
            content = '\n'.join(line.strip() for line in content.split('\n') if line.strip())
            # Limit length but try to end at a sentence
            if len(content) > 2000:
                content = content[:2000]
                last_period = content.rfind('.')
                if last_period > 1000:  # Only truncate at sentence if we don't lose too much
                    content = content[:last_period + 1]
            
            return content
        else:
            return "Unable to extract content from this page"
            
    except Exception as e:
        logger.bind(tag=TAG).error(f"Failed to fetch news detail: {e}")
        return "Unable to fetch detailed content"


def get_news_sources():
    """Get list of news sources with fallback options"""
    # Note: Reuters discontinued its public RSS feeds in 2020; the sources
    # below are live feeds (BBC / NPR / Guardian / CNN / TechCrunch / Ars).
    # First entry per category is tried first, later entries are fallbacks.
    return {
        "world": [
            "https://feeds.bbci.co.uk/news/world/rss.xml",
            "https://rss.cnn.com/rss/edition_world.rss",
            "https://feeds.npr.org/1004/rss.xml",
            "https://www.theguardian.com/world/rss",
            "https://rss.cnn.com/rss/edition.rss"
        ],
        "technology": [
            "https://techcrunch.com/feed/",
            "https://feeds.arstechnica.com/arstechnica/index",
            "https://rss.cnn.com/rss/edition_technology.rss",
            "https://www.theverge.com/rss/index.xml"
        ],
        "business": [
            "https://rss.cnn.com/rss/money_latest.rss",
            "https://www.theguardian.com/uk/business/rss",
            "https://feeds.bbci.co.uk/news/business/rss.xml",
            "https://rss.cnn.com/rss/edition_business.rss"
        ],
        "sports": [
            "https://feeds.bbci.co.uk/sport/rss.xml",
            "https://rss.cnn.com/rss/edition_sport.rss",
            "https://www.theguardian.com/uk/sport/rss",
            "https://rss.cnn.com/rss/edition_football.rss"
        ],
        "health": [
            "https://feeds.bbci.co.uk/news/health/rss.xml",
            "https://rss.cnn.com/rss/edition_health.rss",
            "https://feeds.npr.org/1128/rss.xml"
        ],
        "politics": [
            "https://feeds.bbci.co.uk/news/politics/rss.xml",
            "https://rss.cnn.com/rss/edition_politics.rss",
            "https://www.theguardian.com/politics/rss",
            "https://feeds.npr.org/1014/rss.xml"
        ],
        "science": [
            "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
            "https://feeds.npr.org/1007/rss.xml",
            "https://www.theguardian.com/science/rss",
            "https://rss.cnn.com/rss/edition_space.rss"
        ]
    }


def map_category(category_text):
    """Map user input category to configuration category key"""
    if not category_text:
        return None

    # Category mapping dictionary
    category_map = {
        # World news
        "world": "world",
        "world news": "world",
        "international": "world",
        "international news": "world",
        "global": "world",
        "global news": "world",
        # Technology news
        "technology": "technology",
        "tech": "technology",
        "tech news": "technology",
        "technology news": "technology",
        "innovation": "technology",
        "ai": "technology",
        "artificial intelligence": "technology",
        # Business news
        "business": "business",
        "business news": "business",
        "finance": "business",
        "financial": "business",
        "economy": "business",
        "economic": "business",
        "market": "business",
        "markets": "business",
        "stocks": "business",
        # Sports news
        "sports": "sports",
        "sport": "sports",
        "sports news": "sports",
        "football": "sports",
        "soccer": "sports",
        "basketball": "sports",
        "baseball": "sports",
        # Health news
        "health": "health",
        "health news": "health",
        "medical": "health",
        "medicine": "health",
        "healthcare": "health",
        # Politics news
        "politics": "politics",
        "political": "politics",
        "election": "politics",
        "government": "politics",
        # Science news
        "science": "science",
        "scientific": "science",
        "research": "science",
        "climate": "science",
        "environment": "science"
    }

    # Convert to lowercase and strip whitespace
    normalized_category = category_text.lower().strip()

    # Return mapped result, or original input if no match
    return category_map.get(normalized_category, category_text)


@register_function(
    "get_news",
    GET_NEWS_FUNCTION_DESC,
    ToolType.SYSTEM_CTL,
)
def get_news(
    conn, category: str = None, detail: bool = False, lang: str = "en_US"
):
    """Get news and randomly select one for broadcast, or get detailed content of last news"""
    try:
        # If detail is True, get detailed content of last news
        if detail:
            last_news_link = getattr(conn, "last_news_link", None)
            if not isinstance(last_news_link, dict) or not last_news_link.get("link"):
                return ActionResponse(
                    Action.REQLLM,
                    "Sorry, there is no recently queried news. Please get a news item first.",
                    None,
                )

            link = last_news_link.get("link")
            title = last_news_link.get("title", "Unknown Title")

            if link == "#":
                return ActionResponse(
                    Action.REQLLM, "Sorry, this news item has no available link for detailed content.", None
                )

            logger.bind(tag=TAG).debug(f"Fetching news detail: {title}, URL={link}")

            # Get news detail
            detail_content = fetch_news_detail(link)

            if not detail_content or detail_content == "Unable to fetch detailed content":
                return ActionResponse(
                    Action.REQLLM,
                    f"Sorry, unable to get detailed content for '{title}'. The link may be invalid or the website structure has changed.",
                    None,
                )

            # Build detail report
            detail_report = (
                f"Based on the following data, respond to the user's news detail query in {lang}:\n\n"
                f"News Title: {title}\n"
                f"Detailed Content: {detail_content}\n\n"
                f"(Please summarize the above news content, extract key information, and broadcast it to the user in a natural and fluent way. "
                f"Don't mention this is a summary, just tell it like a complete news story)"
            )

            return ActionResponse(Action.REQLLM, detail_report, None)

        # Otherwise, get news list and select one deterministic item
        # Map user input category to configuration category key
        mapped_category = map_category(category)
        if not mapped_category:
            mapped_category = "world"  # Default category

        cache_key = f"news_{mapped_category}_{lang}"
        cached_report = cache_module.cache_manager.get(cache_module.CacheType.NEWS, cache_key, namespace="news")
        if cached_report:
            return ActionResponse(Action.REQLLM, cached_report, None)

        # Get news sources for the category
        news_sources = get_news_sources()
        category_sources = news_sources.get(mapped_category, news_sources["world"])

        # Try sources in order until we get news
        news_items = []
        used_source = None
        
        for rss_url in category_sources:
            logger.bind(tag=TAG).info(f"Trying RSS source: {rss_url}")
            news_items = fetch_news_from_rss(rss_url)
            if news_items:
                used_source = rss_url
                break
        
        # Fallback to configuration if built-in sources fail
        if not news_items:
            rss_config = conn.config.get("plugins", {}).get("get_news", {})
            fallback_url = rss_config.get("default_rss_url", "https://feeds.bbci.co.uk/news/world/rss.xml")
            logger.bind(tag=TAG).info(f"Trying fallback source: {fallback_url}")
            news_items = fetch_news_from_rss(fallback_url)
            used_source = fallback_url

        logger.bind(tag=TAG).info(
            f"Getting news: original category={category}, mapped category={mapped_category}, "
            f"used source={used_source}, found {len(news_items)} items"
        )

        if not news_items:
            return ActionResponse(
                Action.REQLLM, "no news information could be retrieved", None
            )

        # Select the first news item to keep the response stable for caching/tests
        selected_news = news_items[0]

        # Save current news link to connection object for subsequent detail queries
        if not hasattr(conn, "last_news_link"):
            conn.last_news_link = {}
        conn.last_news_link = {
            "link": selected_news.get("link", "#"),
            "title": selected_news.get("title", "Unknown Title"),
        }

        # Build news report
        news_report = (
            f"Based on the following data, respond to the user's news query in {lang}:\n\n"
            f"News Title: {selected_news['title']}\n"
            f"Published Date: {selected_news['pubDate']}\n"
            f"News Content: {selected_news['description']}\n"
            f"(Please broadcast this news to the user in a natural and fluent way. You can summarize the content appropriately. "
            f"Just read the news directly without additional unnecessary content. "
            f"If the user asks for more details, tell them they can say 'please provide more details about this news' to get more content)"
        )

        cache_module.cache_manager.set(cache_module.CacheType.NEWS, cache_key, news_report, namespace="news")

        return ActionResponse(Action.REQLLM, news_report, None)

    except Exception as e:
        logger.bind(tag=TAG).error(f"Error getting news: {e}")
        return ActionResponse(
            Action.REQLLM, "Sorry, an error occurred while getting news. Please try again later.", None
        )
