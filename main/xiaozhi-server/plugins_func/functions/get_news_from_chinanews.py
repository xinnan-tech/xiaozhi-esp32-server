import random
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action

TAG = __name__
logger = setup_logging()

GET_NEWS_FROM_CHINANEWS_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_news_from_chinanews",
        "description": (
            "Get latest news, randomly select one news item for broadcast. "
            "Users can specify news type, such as social news, tech news, international news, etc. "
            "If not specified, defaults to social news. "
            "Users can request detailed content, which will fetch detailed news content."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "News category, e.g., society, tech, international. Optional parameter, uses default category if not provided",
                },
                "detail": {
                    "type": "boolean",
                    "description": "Whether to get detailed content, defaults to false. If true, gets detailed content of the previous news item",
                },
                "lang": {
                    "type": "string",
                    "description": "Language code for user response, e.g., zh_CN/zh_HK/en_US/ja_JP etc., defaults to zh_CN",
                },
            },
            "required": ["lang"],
        },
    },
}

def fetch_news_from_rss(rss_url):
    """Fetch news list from RSS source"""
    try:
        response = requests.get(rss_url)
        response.raise_for_status()
        # Parse XML
        root = ET.fromstring(response.content)
        # Find all item elements (news entries)
        news_items = []
        for item in root.findall(".//item"):
            title = (
                item.find("title").text if item.find("title") is not None else "No title"
            )
            link = item.find("link").text if item.find("link") is not None else "#"
            description = (
                item.find("description").text
                if item.find("description") is not None
                else "No description"
            )
            pubDate = (
                item.find("pubDate").text
                if item.find("pubDate") is not None
                else "Unknown time"
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
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        # Try to extract body content (selectors need adjustment based on actual website structure)
        content_div = soup.select_one(
            ".content_desc, .content, article, .article-content"
        )
        if content_div:
            paragraphs = content_div.find_all("p")
            content = "\n".join(
                [p.get_text().strip() for p in paragraphs if p.get_text().strip()]
            )
            return content
        else:
            # If specific content area not found, try to get all paragraphs
            paragraphs = soup.find_all("p")
            content = "\n".join(
                [p.get_text().strip() for p in paragraphs if p.get_text().strip()]
            )
            return content[:2000]  # Limit length
    except Exception as e:
        logger.bind(tag=TAG).error(f"Failed to fetch news details: {e}")
        return "Unable to get detailed content"

def map_category(category_text):
    """Map user input Chinese category to category keys in config file"""
    if not category_text:
        return None
    # Category mapping dictionary, currently supports society, international, finance news
    # For more types, see config file
    category_map = {
        # Social news
        "society": "society_rss_url",
        "social news": "society_rss_url",
        # International news
        "international": "world_rss_url",
        "international news": "world_rss_url",
        # Finance news
        "finance": "finance_rss_url",
        "financial news": "finance_rss_url",
        "financial": "finance_rss_url",
        "economy": "finance_rss_url",
    }
    # Convert to lowercase and remove spaces
    normalized_category = category_text.lower().strip()
    # Return mapping result, if no match found return original input
    return category_map.get(normalized_category, category_text)

@register_function(
    "get_news_from_chinanews",
    GET_NEWS_FROM_CHINANEWS_FUNCTION_DESC,
    ToolType.SYSTEM_CTL,
)
def get_news_from_chinanews(
    conn, category: str = None, detail: bool = False, lang: str = "zh_CN"
):
    """Get news and randomly select one for broadcast, or get detailed content of previous news"""
    try:
        # If detail is True, get detailed content of previous news
        if detail:
            if (
                not hasattr(conn, "last_news_link")
                or not conn.last_news_link
                or "link" not in conn.last_news_link
            ):
                return ActionResponse(
                    Action.REQLLM,
                    "Sorry, no recent news query found, please get a news item first.",
                    None,
                )
            
            link = conn.last_news_link.get("link")
            title = conn.last_news_link.get("title", "Unknown title")
            if link == "#":
                return ActionResponse(
                    Action.REQLLM, "Sorry, this news has no available link to get detailed content.", None
                )
            
            logger.bind(tag=TAG).debug(f"Getting news details: {title}, URL={link}")
            # Get news details
            detail_content = fetch_news_detail(link)
            if not detail_content or detail_content == "Unable to get detailed content":
                return ActionResponse(
                    Action.REQLLM,
                    f"Sorry, unable to get detailed content for 《{title}》, link may be invalid or website structure has changed.",
                    None,
                )
            
            # Build detail report
            detail_report = (
                f"Based on the following data, respond to user's news detail query in {lang}:\n\n"
                f"News title: {title}\n"
                f"Detailed content: {detail_content}\n\n"
                f"(Please summarize the above news content, extract key information, and broadcast to user in a natural, fluent manner, "
                f"don't mention this is a summary, tell it like a complete news story)"
            )
            
            return ActionResponse(Action.REQLLM, detail_report, None)
        
        # Otherwise, get news list and randomly select one
        # Get RSS URL from config
        rss_config = conn.config["plugins"]["get_news_from_chinanews"]
        default_rss_url = rss_config.get(
            "default_rss_url", "https://www.chinanews.com.cn/rss/society.xml"
        )
        
        # Map user input category to category key in config
        mapped_category = map_category(category)
        # If category is provided, try to get corresponding URL from config
        rss_url = default_rss_url
        if mapped_category and mapped_category in rss_config:
            rss_url = rss_config[mapped_category]
        
        logger.bind(tag=TAG).info(
            f"Getting news: original category={category}, mapped category={mapped_category}, URL={rss_url}"
        )
        
        # Get news list
        news_items = fetch_news_from_rss(rss_url)
        if not news_items:
            return ActionResponse(
                Action.REQLLM, "Sorry, failed to get news information, please try again later.", None
            )
        
        # Randomly select one news item
        selected_news = random.choice(news_items)
        # Save current news link to connection object for later detail queries
        if not hasattr(conn, "last_news_link"):
            conn.last_news_link = {}
        conn.last_news_link = {
            "link": selected_news.get("link", "#"),
            "title": selected_news.get("title", "Unknown title"),
        }
        
        # Build news report
        news_report = (
            f"Based on the following data, respond to user's news query in {lang}:\n\n"
            f"News title: {selected_news['title']}\n"
            f"Publish time: {selected_news['pubDate']}\n"
            f"News content: {selected_news['description']}\n"
            f"(Please broadcast this news to user in a natural, fluent manner, can appropriately summarize content, "
            f"just read the news directly, no need for extra content. "
            f"If user asks for more details, tell them they can say 'please introduce this news in detail' to get more content)"
        )
        
        return ActionResponse(Action.REQLLM, news_report, None)
    
    except Exception as e:
        logger.bind(tag=TAG).error(f"Error getting news: {e}")
        return ActionResponse(
            Action.REQLLM, "Sorry, an error occurred while getting news, please try again later.", None
        )
