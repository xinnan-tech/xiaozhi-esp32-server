# Web search plugin usage guide

## Feature description

The web search plugin `web_search` supports real-time web search during conversations and returns results. The plugin supports three search sources: Metaso, Tavily, and Serply. Users can choose one as needed.

## API Key Application Guide

We currently support `Mita Search `,`Tavily Search` and `Serply Search`.
- Tavily Search: 1000 free requests per month.
- Metaso Search: Offers high-quality domestic data sources.
- Serply Search: Returns Google search results. Registration grants 2500 free credits; payment is required after credits are exhausted.

## API Key Application Guide

### Method 1: Use Metaso Search

- Visit [Metaso Search API](https://metaso.cn/search-api/api-keys), register and log in
- On the API key management page, click " to create a new Key"
- Copy the generated API Key (prefixed with `mk-`), which is essential for configuration

### Method 2: Use Tavily search

- Visit [Tavily Console ](https://app.tavily.com/home), register and log in
- Create an API Key in the Console
- Copy the generated API Key (prefixed with `tvly-`); this is critical for configuration

### Method 3: Use Serply search

- Visit [Serply](https://serply.io), register and log in to your account
- Create an API Key in the Console
- Copy the generated API Key; this is critical information for configuration
- See [Serply documentation ](https://serply.io/docs) for interface details

## Configuration Method

### Method 1. Deploy via Console (recommended)

- Log in to Console
- Go to the "Configure Role" page and select the Agent to configure
- Click the "Edit Function" button, find the "Web Search" plugin in the parameter configuration area on the right
- Check " for online search"
- Fill in the search source (`metaso`, `tavily`, or `serply`) and enter the corresponding `API Key` in the config
- Save config, then save agent config

### Method 2. Single-module xiaozhi-server deployment

Configure in `data/.config.yaml`:

- Fill search source into `provider`, valid values are `metaso`, `tavily` or `serply`
- Enter the obtained API Key into `api_key`

```yaml
plugins:
  web_search:
    provider: "metaso"
    api_key: "your API Key"
```

To customize the number of returned results and tool descriptions, additionally configure `max_results` and `description`:

```yaml
plugins:
  web_search:
    provider: "metaso"
    description: " web search tool. Use this tool when the user explicitly needs to search the web."
    max_results: 5
    api_key: "your API Key"
```

Also ensure `web_search` is enabled in the `functions` list:

```yaml
plugins:
  functions:
    - web_search
```

Restart service after configuration to apply changes.
