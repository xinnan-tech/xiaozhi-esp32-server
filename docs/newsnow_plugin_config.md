# get_news_from_newsnow plugin news source configuration guide

## Overview

The `get_news_from_newsnow` plugin now supports dynamic configuration of news sources through the web management interface, eliminating the need for code modifications. Users can configure different news sources for each agent in the dashboard.

## Configuration

### 1. Configuration via the Web Management Interface (Recommended)

1. Log in to the smart console
2. Enter the "Role Configuration" page
3. Select the agent to configure
4. Click the "Edit Function" button
5. Find the "newsnow news aggregation" plug-in in the parameter configuration area on the right
6. Enter the Chinese name separated by semicolons in the "News Source Configuration" field

### 2. Configuration file method

Configure in `config.yaml`:

```yaml
plugins:
  get_news_from_newsnow:
    url: "https://newsnow.busiyi.world/api/s?id="
    news_sources: "The Paper; Baidu Trending Search; Cailianshe; Weibo; TikTok"
```

## News source configuration format

The news source configuration uses Chinese names separated by semicolons in the following format:

```
Chinese name 1; Chinese name 2; Chinese name 3
```

### Configuration Example

```
The Paper; Baidu Trending Search; Cailianshe; Weibo; Douyin; Zhihu; 36Kr
```

## Supported News Sources

The plugin supports the following Chinese names of news sources:

- The Paper
- Baidu Hot Search
- Cailianshe
- Weibo
- Tik Tok
- Zhihu
- 36Kr
- Wall Street Journal
- IT Home
- Toutiao
- Hupu
- Bilibili
- Kuaishou
- Snowball
- Gelonghui
- Fab Finance
- Jinshi Data
- Niuke
- Minority
- Rare Earth Mining
- Phoenix.com
- Bug Tribe
- Lianhe Zaobao
- Cool Security
- Vision Forum
- Reference News
- Satellite News Agency
- Baidu Tieba
- Reliable News
- and more...

## Default Configuration

If no news source is configured, the plugin will use the following default configuration:

```
The Paper; Baidu Trending Search; Cailianshe
```

## Usage Instructions

1. **Configure news source**: Set the Chinese name of the news source in the web interface or configuration file, separated by semicolons
2. **Call plugin**: Users can say "broadcast news" or "get news"
3. **Specify news source**: Users can say "report The Paper" or "get Baidu trending searches"
4. **Get details**: Users can say "Get more details about this news"

How it works

1. The plugin accepts Chinese names as parameters (e.g. "The Paper")
2. According to the configured news source list, convert the Chinese name to the corresponding English ID (such as "thepaper")
3. Use the English ID to call the API to obtain news data
4. Return news content to the user

## Notes

1. The configured Chinese name must be exactly the same as the name defined in CHANNEL_MAP
2. After the configuration changes, you need to restart the service or reload the configuration
3. If the configured news source is invalid, the plugin will automatically use the default news source
4. Use English semicolons (;) to separate multiple news sources. Do not use Chinese semicolons (；).
