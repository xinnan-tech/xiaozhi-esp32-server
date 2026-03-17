# Langflow Integration Guide

## Overview

Langflow is a visual flow-based LLM orchestration platform that allows you to design conversational AI flows through a UI and invoke them via API. This integration enables xiaozhi-esp32-server to use Langflow flows as the LLM provider.

## Configuration

### Required Fields

- `type`: Must be set to `langflow`
- `api_key`: Your Langflow API key
- `flow_id`: The ID of your Langflow flow

### Optional Fields

- `base_url`: Langflow API endpoint (default: `https://api.langflow.astra.datastax.com`)
- `tweaks`: Runtime flow parameter overrides (default: `{}`)

### Example Configuration

```yaml
llm:
  type: langflow
  api_key: "your_langflow_api_key_here"
  flow_id: "your_flow_id_here"
  base_url: "https://api.langflow.astra.datastax.com"
  tweaks: {}
```

## Setup Steps

### 1. Create a Langflow Flow

1. Sign up at [Langflow](https://www.langflow.org/) or deploy your own instance
2. Create a new flow in the Langflow UI
3. Design your conversational flow with components
4. Ensure your flow has a Chat Input and Chat Output component
5. Save and deploy your flow

### 2. Get API Credentials

1. Navigate to your Langflow settings
2. Generate an API key
3. Copy your flow ID from the flow URL or settings

### 3. Configure xiaozhi-esp32-server

Add the configuration to your `config.yaml` or `data/.config.yaml`:

```yaml
LLM:
  LangflowLLM:
    type: langflow
    api_key: "sk-..."
    flow_id: "abc123..."
    base_url: "https://api.langflow.astra.datastax.com"
```

### 4. Select Langflow as Provider

Update your module selection:

```yaml
selected_module:
  LLM: LangflowLLM
```

## Advanced Usage

### Using Tweaks

The `tweaks` parameter allows you to customize flow components at runtime without modifying the flow design:

```yaml
llm:
  type: langflow
  api_key: "your_api_key"
  flow_id: "your_flow_id"
  tweaks:
    ChatOpenAI-abc123:
      temperature: 0.7
      model_name: "gpt-4"
```

To find component IDs for tweaks:
1. Open your flow in Langflow
2. Click on a component
3. Copy the component ID from the settings panel

## Troubleshooting

### Connection Issues

- Verify your API key is correct
- Check that the base_url is accessible from your server
- Ensure your flow_id exists and is deployed

### No Response

- Check Langflow logs for errors
- Verify your flow has proper Chat Input/Output components
- Test the flow directly in Langflow UI first

### Session Not Persisting

- The integration automatically handles session management
- Each device gets a unique session_id for conversation continuity

## API Reference

The integration uses Langflow's Run API:

```
POST {base_url}/api/v1/run/{flow_id}
Headers:
  x-api-key: {api_key}
Body:
  {
    "input_value": "user message",
    "output_type": "chat",
    "input_type": "chat",
    "session_id": "unique_session_id",
    "tweaks": {}
  }
```

## Limitations

- System prompts configured in `config.yaml` are ignored (configure in Langflow flow instead)
- Function calling is not currently supported
- Response streaming depends on Langflow flow configuration
