import random
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action

TAG = __name__
logger = setup_logging()

GET_NEWS_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_news",
        "description": (
            "获取最新新闻，随机选择一条新闻进行播报。"
            "用户可以指定新闻类型，如社会新闻、科技新闻、国际新闻等。"
            "如果没有指定，默认播报社会新闻。"
            "用户可以要求获取详细内容，此时会获取新闻的详细内容。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "新闻类别，例如社会、科技、国际。可选参数，如果不提供则使用默认类别"
                },
                "detail": {
                    "type": "boolean",
                    "description": "是否获取详细内容，默认为false。如果为true，则获取上一条新闻的详细内容"
                },
                "lang": {
                    "type": "string",
                    "description": "返回用户使用的语言code，例如zh_CN/zh_HK/en_US/ja_JP等，默认zh_CN"
                }
            },
            "required": ["lang"]
        }
    }
}


def fetch_news_from_rss(rss_url):
    """从RSS源获取新闻列表"""
    try:
        response = requests.get(rss_url)
        response.raise_for_status()

        # 解析XML
        root = ET.fromstring(response.content)

        # 查找所有item元素（新闻条目）
        news_items = []
        for item in root.findall('.//item'):
            title = item.find('title').text if item.find('title') is not None else "无标题"
            link = item.find('link').text if item.find('link') is not None else "#"
            description = item.find('description').text if item.find('description') is not None else "无描述"
            pubDate = item.find('pubDate').text if item.find('pubDate') is not None else "未知时间"

            news_items.append({
                'title': title,
                'link': link,
                'description': description,
                'pubDate': pubDate
            })

        return news_items
    except Exception as e:
        logger.bind(tag=TAG).error(f"获取RSS新闻失败: {e}")
        return []


def fetch_news_detail(url):
    """获取新闻详情页内容并总结"""
    try:
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # 尝试提取正文内容 (这里的选择器需要根据实际网站结构调整)
        content_div = soup.select_one('.content_desc, .content, article, .article-content')
        if content_div:
            paragraphs = content_div.find_all('p')
            content = '\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
            return content
        else:
            # 如果找不到特定的内容区域，尝试获取所有段落
            paragraphs = soup.find_all('p')
            content = '\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
            return content[:2000]  # 限制长度
    except Exception as e:
        logger.bind(tag=TAG).error(f"获取新闻详情失败: {e}")
        return "无法获取详细内容"


def map_category(category_text):
    """将用户输入的中文类别映射到配置文件中的类别键"""
    if not category_text:
        return None

    # 类别映射字典，目前支持社会、国际、财经新闻，如需更多类型，参见配置文件
    category_map = {
        # 社会新闻
        "社会": "society",
        "社会新闻": "society",
        # 国际新闻
        "国际": "world",
        "国际新闻": "world",
        # 财经新闻
        "财经": "finance",
        "财经新闻": "finance",
        "金融": "finance",
        "经济": "finance"
    }

    # 转换为小写并去除空格
    normalized_category = category_text.lower().strip()

    # 返回映射结果，如果没有匹配项则返回原始输入
    return category_map.get(normalized_category, category_text)


@register_function('get_news', GET_NEWS_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def get_news(conn, category: str = None, detail: bool = False, lang: str = "zh_CN"):
    """获取新闻并随机选择一条进行播报，或获取上一条新闻的详细内容"""
    try:
        # 如果detail为True，获取上一条新闻的详细内容
        if detail:
            if not hasattr(conn, 'last_news_link') or not conn.last_news_link or 'link' not in conn.last_news_link:
                return ActionResponse(Action.REQLLM, "抱歉，没有找到最近查询的新闻，请先获取一条新闻。", None)

            link = conn.last_news_link.get('link')
            title = conn.last_news_link.get('title', '未知标题')

            if link == '#':
                return ActionResponse(Action.REQLLM, "抱歉，该新闻没有可用的链接获取详细内容。", None)

            logger.bind(tag=TAG).debug(f"获取新闻详情: {title}, URL={link}")

            # 获取新闻详情
            detail_content = fetch_news_detail(link)

            if not detail_content or detail_content == "无法获取详细内容":
                return ActionResponse(Action.REQLLM,
                                      f"抱歉，无法获取《{title}》的详细内容，可能是链接已失效或网站结构发生变化。", None)

            # 构建详情报告
            detail_report = (
                f"根据下列数据，用{lang}回应用户的新闻详情查询请求：\n\n"
                f"新闻标题: {title}\n"
                f"详细内容: {detail_content}\n\n"
                f"(请对上述新闻内容进行总结，提取关键信息，以自然、流畅的方式向用户播报，"
                f"不要提及这是总结，就像是在讲述一个完整的新闻故事)"
            )

            return ActionResponse(Action.REQLLM, detail_report, None)

        # 否则，获取新闻列表并随机选择一条
        # 从配置中获取RSS URL
        rss_config = conn.config["plugins"]["get_news"]
        default_rss_url = rss_config.get("default_rss_url", "https://www.chinanews.com.cn/rss/society.xml")

        # 将用户输入的类别映射到配置中的类别键
        mapped_category = map_category(category)

        # 如果提供了类别，尝试从配置中获取对应的URL
        rss_url = default_rss_url
        if mapped_category and mapped_category in rss_config.get("category_urls", {}):
            rss_url = rss_config["category_urls"][mapped_category]

        logger.bind(tag=TAG).info(f"获取新闻: 原始类别={category}, 映射类别={mapped_category}, URL={rss_url}")

        # 获取新闻列表
        news_items = fetch_news_from_rss(rss_url)

        if not news_items:
            return ActionResponse(Action.REQLLM, "抱歉，未能获取到新闻信息，请稍后再试。", None)

        # 随机选择一条新闻
        selected_news = random.choice(news_items)

        # 保存当前新闻链接到连接对象，以便后续查询详情
        if not hasattr(conn, 'last_news_link'):
            conn.last_news_link = {}
        conn.last_news_link = {
            'link': selected_news.get('link', '#'),
            'title': selected_news.get('title', '未知标题')
        }

        # 构建新闻报告
        news_report = (
            f"根据下列数据，用{lang}回应用户的新闻查询请求：\n\n"
            f"新闻标题: {selected_news['title']}\n"
            f"发布时间: {selected_news['pubDate']}\n"
            f"新闻内容: {selected_news['description']}\n"
            f"(请以自然、流畅的方式向用户播报这条新闻，可以适当总结内容，"
            f"直接读出新闻即可，不需要额外多余的内容。"
            f"如果用户询问更多详情，告知用户可以说'请详细介绍这条新闻'获取更多内容)"
        )

        return ActionResponse(Action.REQLLM, news_report, None)

    except Exception as e:
        logger.bind(tag=TAG).error(f"获取新闻出错: {e}")
        return ActionResponse(Action.REQLLM, "抱歉，获取新闻时发生错误，请稍后再试。", None)