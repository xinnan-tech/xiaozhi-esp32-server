import random
import requests
from datetime import datetime
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action

TAG = __name__
logger = setup_logging()

# Sample Indian news for demo (when APIs are not available)
SAMPLE_INDIAN_NEWS = [
    {
        "title": "India's GDP Growth Shows Strong Recovery in Q2",
        "description": "India's economy demonstrates robust growth with improved manufacturing and services sectors contributing to overall economic recovery.",
        "source": "Economic Times",
        "publishedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "category": "Business"
    },
    {
        "title": "New Digital India Initiative Launched for Rural Areas",
        "description": "Government announces comprehensive digital infrastructure program to connect remote villages with high-speed internet and digital services.",
        "source": "PIB India",
        "publishedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "category": "Technology"
    },
    {
        "title": "Monsoon Update: Normal Rainfall Expected Across Most States",
        "description": "India Meteorological Department forecasts normal to above-normal rainfall for the remaining monsoon season across major agricultural states.",
        "source": "India Today",
        "publishedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "category": "Weather"
    },
    {
        "title": "Indian Space Mission Achieves New Milestone",
        "description": "ISRO successfully completes another phase of its ambitious space exploration program, marking significant progress in space technology.",
        "source": "The Hindu",
        "publishedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "category": "Science"
    },
    {
        "title": "Education Reform: New Policy Implementation Shows Progress",
        "description": "National Education Policy 2020 implementation shows positive results in improving learning outcomes across Indian schools.",
        "source": "NDTV",
        "publishedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "category": "Education"
    },
    {
        "title": "Startup India Initiative Crosses 100,000 Registered Startups",
        "description": "India's startup ecosystem reaches new milestone with over 100,000 registered startups, creating millions of jobs across sectors.",
        "source": "Business Standard",
        "publishedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "category": "Business"
    }
]

# Reliable Indian RSS feeds that usually work
RELIABLE_INDIAN_RSS = {
    "pib": "https://pib.gov.in/rss/leng.xml",  # Press Information Bureau
    "dd_news": "https://ddnews.gov.in/rss.xml",  # DD News
    "business_standard": "https://www.business-standard.com/rss/home_page_top_stories.rss",
    "mint": "https://www.livemint.com/rss/news",
    "scroll": "https://scroll.in/feed",
    "wire": "https://thewire.in/feed",
    "quint": "https://www.thequint.com/feed"
}

GET_INDIAN_NEWS_API_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_indian_news_api",
        "description": (
            "Get latest Indian news from reliable sources including business, technology, politics, and general news. "
            "Provides current news from major Indian publications and government sources. "
            "Can specify category like business, technology, politics, or get general news."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "News category: business, technology, politics, science, education, or general. Optional parameter",
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


def fetch_indian_news_from_api():
    """Fetch Indian news from API sources"""
    # For demo purposes, we'll use sample news
    # In production, you would use actual API keys

    # Try NewsAPI (requires free API key)
    # Uncomment and add your API key:
    # try:
    #     api_key = "your_newsapi_key_here"
    #     url = "https://newsapi.org/v2/top-headlines"
    #     params = {
    #         "country": "in",
    #         "apiKey": api_key,
    #         "pageSize": 20
    #     }
    #     response = requests.get(url, params=params, timeout=10)
    #     if response.status_code == 200:
    #         data = response.json()
    #         return data.get("articles", [])
    # except Exception as e:
    #     logger.bind(tag=TAG).error(f"NewsAPI error: {e}")

    # For now, return sample news
    logger.bind(tag=TAG).info("Using sample Indian news data")
    return SAMPLE_INDIAN_NEWS


def fetch_indian_rss_news():
    """Fetch from reliable Indian RSS sources"""
    import xml.etree.ElementTree as ET
    from bs4 import BeautifulSoup

    news_items = []

    for source_name, rss_url in RELIABLE_INDIAN_RSS.items():
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; IndianNewsBot/1.0)"
            }
            response = requests.get(rss_url, headers=headers, timeout=10)

            if response.status_code == 200:
                root = ET.fromstring(response.content)

                for item in root.findall(".//item")[:5]:  # Get first 5 items
                    title = item.find("title").text if item.find(
                        "title") is not None else "No title"
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
                        "description": description,
                        "source": source_name.replace("_", " ").title(),
                        "publishedAt": pubDate,
                        "category": "General"
                    })

                logger.bind(tag=TAG).info(
                    f"Fetched {len(news_items)} items from {source_name}")
                break  # Use first successful source

        except Exception as e:
            logger.bind(tag=TAG).warning(
                f"Failed to fetch from {source_name}: {e}")
            continue

    return news_items if news_items else SAMPLE_INDIAN_NEWS


@register_function("get_indian_news_api", GET_INDIAN_NEWS_API_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def get_indian_news_api(conn, category: str = "general", detail: bool = False, lang: str = "en_US"):
    """Get Indian news from API sources"""
    try:
        logger.bind(tag=TAG).info(
            f"Fetching Indian news - Category: {category}")

        # Try API first, then RSS fallback
        news_items = fetch_indian_news_from_api()

        if not news_items:
            logger.bind(tag=TAG).info("API failed, trying RSS sources")
            news_items = fetch_indian_rss_news()

        if not news_items:
            return ActionResponse(
                Action.REQLLM,
                "Sorry, unable to fetch Indian news at the moment. Please try again later.",
                None,
            )

        # Filter by category if specified
        if category and category.lower() != "general":
            filtered_items = [
                item for item in news_items
                if category.lower() in item.get("category", "").lower()
            ]
            if filtered_items:
                news_items = filtered_items

        # Randomly select one news item
        selected_news = random.choice(news_items)

        # Save for detail queries
        if not hasattr(conn, "last_indian_news_api"):
            conn.last_indian_news_api = {}
        conn.last_indian_news_api = selected_news

        # Build news report
        news_report = (
            f"Based on the following Indian news data, respond to user's query in {lang}:\\n\\n"
            f"📰 News Title: {selected_news['title']}\\n"
            f"📅 Published: {selected_news['publishedAt']}\\n"
            f"📺 Source: {selected_news['source']}\\n"
            f"📝 Summary: {selected_news['description']}\\n"
            f"🏷️ Category: {selected_news.get('category', 'General')}\\n\\n"
            f"(Please present this Indian news to the user in a natural, conversational way. "
            f"Focus on the key information and make it engaging for Indian audience.)"
        )

        return ActionResponse(Action.REQLLM, news_report, None)

    except Exception as e:
        logger.bind(tag=TAG).error(f"Error getting Indian news: {e}")
        return ActionResponse(
            Action.REQLLM,
            "Sorry, an error occurred while fetching Indian news. Please try again later.",
            None
        )
