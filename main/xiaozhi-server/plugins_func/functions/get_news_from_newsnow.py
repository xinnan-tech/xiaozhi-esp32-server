import random
import requests
import json
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from markitdown import MarkItDown

TAG = __name__
logger = setup_logging()

CHANNEL_MAP = {
    "V2EX": "v2ex-share",
    "知乎": "zhihu",
    "微博": "weibo",
    "联合早报": "zaobao",
    "酷安": "coolapk",
    "MKTNews": "mktnews-flash",
    "华尔街见闻": "wallstreetcn-quick",
    "36氪": "36kr-quick",
    "抖音": "douyin",
    "虎扑": "hupu",
    "百度贴吧": "tieba",
    "今日头条": "toutiao",
    "IT之家": "ithome",
    "澎湃新闻": "thepaper",
    "卫星通讯社": "sputniknewscn",
    "参考消息": "cankaoxiaoxi",
    "远景论坛": "pcbeta-windows11",
    "财联社": "cls-depth",
    "雪球": "xueqiu-hotstock",
    "格隆汇": "gelonghui",
    "法布财经": "fastbull-express",
    "Solidot": "solidot",
    "Hacker News": "hackernews",
    "Product Hunt": "producthunt",
    "Github": "github-trending-today",
    "哔哩哔哩": "bilibili-hot-search",
    "快手": "kuaishou",
    "靠谱新闻": "kaopu",
    "金十数据": "jin10",
    "百度热搜": "baidu",
    "牛客": "nowcoder",
    "少数派": "sspai",
    "稀土掘金": "juejin",
    "凤凰网": "ifeng",
    "虫部落": "chongbuluo-latest",
}


# 默认新闻来源字典，当配置中没有指定时使用
DEFAULT_NEWS_SOURCES = "澎湃新闻;百度热搜;财联社"


def get_news_sources_from_config(conn):
    """从配置中获取新闻源字符串"""
    try:
        # 尝试从插件配置中获取新闻源
        if (
            conn.config.get("plugins")
            and conn.config["plugins"].get("get_news_from_newsnow")
            and conn.config["plugins"]["get_news_from_newsnow"].get("news_sources")
        ):
            # 获取配置的新闻源字符串
            news_sources_config = conn.config["plugins"]["get_news_from_newsnow"][
                "news_sources"
            ]

            if isinstance(news_sources_config, str) and news_sources_config.strip():
                logger.bind(tag=TAG).debug(f"使用配置的新闻源: {news_sources_config}")
                return news_sources_config
            else:
                logger.bind(tag=TAG).warning("新闻源配置为空或格式错误，使用默认配置")
        else:
            logger.bind(tag=TAG).debug("未找到新闻源配置，使用默认配置")

        return DEFAULT_NEWS_SOURCES

    except Exception as e:
        logger.bind(tag=TAG).error(f"获取新闻源配置失败: {e}，使用默认配置")
        return DEFAULT_NEWS_SOURCES


# 从CHANNEL_MAP获取所有可用的新闻源名称
available_sources = list(CHANNEL_MAP.keys())
example_sources_str = "、".join(available_sources)

GET_NEWS_FROM_NEWSNOW_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_news_from_newsnow",
        "description": (
            "获取最新新闻，随机选择一条新闻进行播报。"
            f"用户可以选择不同的新闻源，标准的名称是：{example_sources_str}"
            "例如用户要求百度新闻，其实就是百度热搜。如果没有指定，默认从澎湃新闻获取。"
            "用户可以要求获取详细内容，此时会获取新闻的详细内容。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": f"新闻源的标准中文名称，例如{example_sources_str}等。可选参数，如果不提供则使用默认新闻源",
                },
                "detail": {
                    "type": "boolean",
                    "description": "是否获取详细内容，默认为false。如果为true，则获取上一条新闻的详细内容",
                },
                "lang": {
                    "type": "string",
                    "description": "返回用户使用的语言code，例如zh_CN/zh_HK/en_US/ja_JP等，默认zh_CN",
                },
            },
            "required": ["lang"],
        },
    },
}


def fetch_news_from_api(conn, source="thepaper"):
    """从API获取新闻列表"""
    try:
        api_url = f"https://newsnow.busiyi.world/api/s?id={source}"
        if conn.config["plugins"].get("get_news_from_newsnow") and conn.config[
            "plugins"
        ]["get_news_from_newsnow"].get("url"):
            api_url = conn.config["plugins"]["get_news_from_newsnow"]["url"] + source

        response = requests.get(api_url, timeout=10)
        response.raise_for_status()

        data = response.json()

        if "items" in data:
            return data["items"]
        else:
            logger.bind(tag=TAG).error(f"获取新闻API响应格式错误: {data}")
            return []

    except Exception as e:
        logger.bind(tag=TAG).error(f"获取新闻API失败: {e}")
        return []


def fetch_news_detail(url):
    """获取新闻详情页内容并使用MarkItDown清理HTML"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # 使用MarkItDown清理HTML内容
        md = MarkItDown(enable_plugins=False)
        result = md.convert(response)

        # 获取清理后的文本内容
        clean_text = result.text_content

        # 如果清理后的内容为空，返回提示信息
        if not clean_text or len(clean_text.strip()) == 0:
            logger.bind(tag=TAG).warning(f"清理后的新闻内容为空: {url}")
            return "无法解析新闻详情内容，可能是网站结构特殊或内容受限。"

        return clean_text
    except Exception as e:
        logger.bind(tag=TAG).error(f"获取新闻详情失败: {e}")
        return "无法获取详细内容"


@register_function(
    "get_news_from_newsnow",
    GET_NEWS_FROM_NEWSNOW_FUNCTION_DESC,
    ToolType.SYSTEM_CTL,
)
def get_news_from_newsnow(
    conn, source: str = "澎湃新闻", detail: bool = False, lang: str = "zh_CN"
):
    """获取新闻并随机选择一条进行播报，或获取上一条新闻的详细内容"""
    try:
        # 获取当前配置的新闻源
        news_sources = get_news_sources_from_config(conn)

        # 如果detail为True，获取上一条新闻的详细内容
        detail = str(detail).lower() == "true"
        if detail:
            if (
                not hasattr(conn, "last_newsnow_link")
                or not conn.last_newsnow_link
                or "url" not in conn.last_newsnow_link
            ):
                return ActionResponse(
                    Action.REQLLM,
                    "抱歉，没有找到最近查询的新闻，请先获取一条新闻。",
                    None,
                )

            url = conn.last_newsnow_link.get("url")
            title = conn.last_newsnow_link.get("title", "未知标题")
            source_id = conn.last_newsnow_link.get("source_id", "thepaper")
            source_name = CHANNEL_MAP.get(source_id, "未知来源")

            if not url or url == "#":
                return ActionResponse(
                    Action.REQLLM, "抱歉，该新闻没有可用的链接获取详细内容。", None
                )

            logger.bind(tag=TAG).debug(
                f"获取新闻详情: {title}, 来源: {source_name}, URL={url}"
            )

            # 获取新闻详情
            detail_content = fetch_news_detail(url)

            if not detail_content or detail_content == "无法获取详细内容":
                return ActionResponse(
                    Action.REQLLM,
                    f"抱歉，无法获取《{title}》的详细内容，可能是链接已失效或网站结构发生变化。",
                    None,
                )

            # 构建详情报告
            detail_report = (
                f"根据下列数据，用{lang}回应用户的新闻详情查询请求：\n\n"
                f"新闻标题: {title}\n"
                # f"新闻来源: {source_name}\n"
                f"详细内容: {detail_content}\n\n"
                f"(请对上述新闻内容进行总结，提取关键信息，以自然、流畅的方式向用户播报，"
                f"不要提及这是总结，就像是在讲述一个完整的新闻故事)"
            )

            return ActionResponse(Action.REQLLM, detail_report, None)

        # 否则，获取新闻列表并随机选择一条
        # 将中文名称转换为英文ID
        english_source_id = None

        # 检查输入的中文名称是否在配置的新闻源中
        news_sources_list = [
            name.strip() for name in news_sources.split(";") if name.strip()
        ]
        if source in news_sources_list:
            # 如果输入的中文名称在配置的新闻源中，在 CHANNEL_MAP 中查找对应的英文ID
            english_source_id = CHANNEL_MAP.get(source)

        # 如果找不到对应的英文ID，使用默认源
        if not english_source_id:
            logger.bind(tag=TAG).warning(f"无效的新闻源: {source}，使用默认源澎湃新闻")
            english_source_id = "thepaper"
            source = "澎湃新闻"

        logger.bind(tag=TAG).info(f"获取新闻: 新闻源={source}({english_source_id})")

        # 获取新闻列表
        news_items = fetch_news_from_api(conn, english_source_id)

        if not news_items:
            return ActionResponse(
                Action.REQLLM,
                f"抱歉，未能从{source}获取到新闻信息，请稍后再试或尝试其他新闻源。",
                None,
            )

        # 随机选择一条新闻
        selected_news = random.choice(news_items)

        # 保存当前新闻链接到连接对象，以便后续查询详情
        if not hasattr(conn, "last_newsnow_link"):
            conn.last_newsnow_link = {}
        conn.last_newsnow_link = {
            "url": selected_news.get("url", "#"),
            "title": selected_news.get("title", "未知标题"),
            "source_id": english_source_id,
        }

        # 构建新闻报告
        news_report = (
            f"根据下列数据，用{lang}回应用户的新闻查询请求：\n\n"
            f"新闻标题: {selected_news['title']}\n"
            # f"新闻来源: {source}\n"
            f"(请以自然、流畅的方式向用户播报这条新闻标题，"
            f"提示用户可以要求获取详细内容，此时会获取新闻的详细内容。)"
        )

        return ActionResponse(Action.REQLLM, news_report, None)

    except Exception as e:
        logger.bind(tag=TAG).error(f"获取新闻出错: {e}")
        return ActionResponse(
            Action.REQLLM, "抱歉，获取新闻时发生错误，请稍后再试。", None
        )
