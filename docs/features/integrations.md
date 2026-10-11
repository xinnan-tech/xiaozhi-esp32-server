# ✨ Integrations

This guide covers the various integrations available with Xiaozhi ESP32 Server, including smart home platforms, communication services, and third-party APIs.

## 🎯 Integration Overview

Xiaozhi supports integrations with:
- **Smart Home Platforms** (HomeAssistant, MQTT)
- **Communication Services** (SMS, Email, Notifications)
- **AI Services** (Vision models, Voice recognition)
- **Data Sources** (Weather, News, APIs)
- **Development Tools** (MCP, Function calling)

## 🏠 Smart Home Integrations

### **HomeAssistant Integration**

Connect Xiaozhi to HomeAssistant for comprehensive smart home control.

#### **Features**
- **Voice control** of lights, switches, and sensors
- **Temperature control** via thermostats
- **Security monitoring** with cameras and alarms
- **Automation triggers** based on voice commands

#### **Setup**
```yaml
# In your configuration
homeassistant:
  enabled: true
  url: http://homeassistant.local:8123
  api_key: your-homeassistant-api-key
  entities:
    lights:
      - light.living_room
      - light.kitchen
      - light.bedroom
    switches:
      - switch.coffee_maker
      - switch.tv_power
    sensors:
      - sensor.temperature
      - sensor.humidity
    climate:
      - climate.thermostat
```

#### **Voice Commands**
- "Turn on the living room light"
- "Set temperature to 72 degrees"
- "Turn off the coffee maker"
- "What's the temperature in the bedroom?"

#### **Advanced Features**
- **Function calling** for complex operations
- **MCP service** integration for advanced automation
- **Custom entities** and device support

### **MQTT Gateway Integration**

Use MQTT for lightweight IoT device communication.

#### **Features**
- **Publish/subscribe** messaging
- **Device discovery** and management
- **Real-time updates** from sensors
- **Command execution** via MQTT topics

#### **Setup**
```yaml
# MQTT configuration
mqtt:
  enabled: true
  broker: mqtt://broker.hivemq.com:1883
  username: your-username
  password: your-password
  topics:
    commands: xiaozhi/commands
    status: xiaozhi/status
    sensors: xiaozhi/sensors
```

#### **MQTT Topics**
- **Commands**: `xiaozhi/commands/{device_id}`
- **Status**: `xiaozhi/status/{device_id}`
- **Sensors**: `xiaozhi/sensors/{sensor_id}`

## 📱 Communication Integrations

### **SMS Integration**

Send and receive SMS messages via Twilio or other providers.

#### **Features**
- **Send SMS** notifications
- **Receive SMS** commands
- **Two-factor authentication** support
- **Emergency alerts** and notifications

#### **Setup**
```yaml
# SMS configuration
sms:
  enabled: true
  provider: twilio
  account_sid: your-twilio-account-sid
  auth_token: your-twilio-auth-token
  from_number: +1234567890
  to_numbers:
    - +1234567890
    - +0987654321
```

#### **Voice Commands**
- "Send SMS to John: Meeting at 3 PM"
- "Text my wife: I'll be home late"
- "Send emergency alert"

### **Email Integration**

Send email notifications and reports.

#### **Features**
- **Email notifications** for events
- **Daily reports** and summaries
- **Alert emails** for critical issues
- **Custom email templates**

#### **Setup**
```yaml
# Email configuration
email:
  enabled: true
  smtp_server: smtp.gmail.com
  smtp_port: 587
  username: your-email@gmail.com
  password: your-app-password
  recipients:
    - admin@yourdomain.com
    - alerts@yourdomain.com
```

## 🤖 AI Service Integrations

### **Vision Model Integration**

Enable image recognition and analysis capabilities.

#### **Features**
- **Image recognition** and classification
- **Object detection** and counting
- **Text extraction** from images
- **Scene analysis** and description

#### **Setup**
```yaml
# Vision model configuration
VLLM:
  OpenAILLMVLLM:
    type: openai
    api_key: your-openai-api-key
    model: gpt-4o
    vision_enabled: true
    max_image_size: 1024
    supported_formats: [jpg, png, gif, webp]
```

#### **Voice Commands**
- "What do you see in this image?"
- "Describe the scene"
- "Count the objects"
- "Read the text in this image"

### **Voiceprint Recognition**

Identify users by their voice patterns.

#### **Features**
- **User identification** by voice
- **Personalized responses** based on user
- **Access control** via voice recognition
- **Multi-user support** with different profiles

#### **Setup**
```yaml
# Voiceprint configuration
voiceprint:
  url: http://192.168.1.100:8005/voiceprint/health?key=abcd
  speakers:
    - "user1,John,John is a software engineer"
    - "user2,Jane,Jane is a designer"
    - "user3,Bob,Bob is a student"
```

See [Voiceprint Recognition](../guides/voiceprint.md) for the service
protocol and privacy notes.

#### **Voice Commands**
- "Do you know who I am?"
- "Register my voice"
- "Delete my voice profile"

## 🌐 Data Source Integrations

### **Weather Integration**

Get real-time weather information and forecasts.

#### **Features**
- **Current weather** conditions
- **Weather forecasts** for multiple days
- **Location-based** weather data
- **Weather alerts** and warnings

#### **Setup**
```yaml
# Weather configuration
weather:
  enabled: true
  provider: openweathermap
  api_key: your-openweathermap-api-key
  default_location: "New York, NY"
  units: metric
  cache_duration: 300
```

#### **Voice Commands**
- "What's the weather like?"
- "Will it rain today?"
- "What's the temperature?"
- "Weather forecast for tomorrow"

### **News Integration**

Get the latest news and updates.

#### **Features**
- **Latest news** headlines
- **News summaries** and briefings
- **Topic-specific** news filtering
- **News alerts** for breaking stories

#### **Setup**
```yaml
# News configuration
news:
  enabled: true
  provider: newsapi
  api_key: your-newsapi-key
  sources: ["bbc-news", "cnn", "reuters"]
  categories: ["technology", "science", "health"]
  max_articles: 10
```

#### **Voice Commands**
- "What's the latest news?"
- "News about technology"
- "Breaking news"
- "News summary"

## 🔧 Development Integrations

### **MCP (Model Context Protocol) Integration**

Use MCP for advanced AI model communication.

#### **Features**
- **Standardized communication** with AI models
- **Function calling** capabilities
- **Context management** for conversations
- **Plugin system** for extensibility

#### **Setup**
```yaml
# MCP configuration
mcp:
  enabled: true
  servers:
    - name: homeassistant
      url: http://homeassistant.local:8123
      api_key: your-ha-api-key
    - name: weather
      url: http://weather-api.local:8000
      api_key: your-weather-api-key
```

#### **MCP Functions**
- **HomeAssistant**: Control smart home devices
- **Weather**: Get weather information
- **News**: Fetch news articles
- **Custom**: Define your own functions

### **Function Calling Integration**

Enable AI models to call external functions.

#### **Features**
- **Dynamic function** execution
- **Parameter validation** and type checking
- **Error handling** and fallback mechanisms
- **Function chaining** for complex operations

#### **Setup**
```yaml
# Function calling configuration
function_calling:
  enabled: true
  
  functions:
    - name: get_weather
      description: Get current weather information
      parameters:
        location:
          type: string
          description: City name or coordinates
          required: true
        units:
          type: string
          enum: [metric, imperial]
          default: metric
    
    - name: control_light
      description: Control smart home lights
      parameters:
        entity_id:
          type: string
          description: HomeAssistant entity ID
          required: true
        action:
          type: string
          enum: [on, off, toggle, dim]
          required: true
        brightness:
          type: integer
          description: Brightness level (0-255)
          required: false
```

## 🔌 Custom Integration Development

### **Creating Custom Integrations**

Develop your own integrations for specific needs.

#### **Integration Structure**
```python
# Custom integration example
class CustomIntegration:
    def __init__(self, config):
        self.config = config
        self.enabled = config.get('enabled', False)
    
    def initialize(self):
        """Initialize the integration"""
        pass
    
    def process_command(self, command):
        """Process voice commands"""
        pass
    
    def get_status(self):
        """Get integration status"""
        pass
```

#### **Configuration Template**
```yaml
# Custom integration configuration
custom_integration:
  enabled: true
  name: "My Custom Integration"
  version: "1.0.0"
  settings:
    api_key: your-api-key
    endpoint: https://api.example.com
    timeout: 30
```

### **Integration Best Practices**

#### **Error Handling**
```python
def safe_api_call(self, endpoint, data):
    try:
        response = requests.post(endpoint, json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"API call failed: {e}")
        return None
```

#### **Configuration Validation**
```python
def validate_config(self, config):
    required_fields = ['api_key', 'endpoint']
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field: {field}")
```

#### **Logging and Monitoring**
```python
import logging

logger = logging.getLogger(__name__)

def log_integration_activity(self, action, details):
    logger.info(f"Integration {self.name}: {action} - {details}")
```

## 📊 Integration Monitoring

### **Health Checks**

Monitor integration status and performance.

```yaml
# Integration monitoring
monitoring:
  integrations:
    enabled: true
    
    health_checks:
      interval: 60  # seconds
      timeout: 10   # seconds
      
      checks:
        - name: homeassistant
          type: http
          url: http://homeassistant.local:8123/api/
          expected_status: 200
        
        - name: weather_api
          type: http
          url: https://api.openweathermap.org/data/2.5/weather
          expected_status: 200
```

### **Performance Metrics**

Track integration performance and usage.

```yaml
# Performance monitoring
metrics:
  enabled: true
  
  integration_metrics:
    response_time: true
    success_rate: true
    error_count: true
    usage_count: true
```

## 🎯 Integration Examples

### **Complete Smart Home Setup**

```yaml
# Complete smart home integration
integrations:
  homeassistant:
    enabled: true
    url: http://homeassistant.local:8123
    api_key: your-ha-api-key
    entities:
      lights: [light.living_room, light.kitchen]
      switches: [switch.coffee_maker, switch.tv]
      sensors: [sensor.temperature, sensor.humidity]
  
  mqtt:
    enabled: true
    broker: mqtt://broker.hivemq.com:1883
    topics:
      commands: xiaozhi/commands
      status: xiaozhi/status
  
  weather:
    enabled: true
    provider: openweathermap
    api_key: your-weather-api-key
    default_location: "New York, NY"
  
  sms:
    enabled: true
    provider: twilio
    account_sid: your-twilio-sid
    auth_token: your-twilio-token
    from_number: +1234567890
```

### **Educational Environment Setup**

```yaml
# Educational integration setup
integrations:
  math_helper:
    enabled: true
    functions:
      - calculate
      - solve_equation
      - explain_concept
  
  language_learning:
    enabled: true
    target_language: spanish
    difficulty: beginner
    functions:
      - translate
      - practice_conversation
      - grammar_check
  
  news:
    enabled: true
    provider: newsapi
    api_key: your-newsapi-key
    sources: ["bbc-news", "cnn"]
    categories: ["technology", "science"]
```

## 🛠️ Troubleshooting Integrations

### **Common Issues**

#### **Integration Not Working**
1. **Check configuration** - Verify all required fields
2. **Test connectivity** - Ping endpoints and check ports
3. **Check logs** - Look for error messages
4. **Verify credentials** - Ensure API keys are valid

#### **Performance Issues**
1. **Monitor response times** - Check API latency
2. **Optimize requests** - Use caching and batching
3. **Check rate limits** - Ensure you're not exceeding limits
4. **Scale resources** - Add more processing power if needed

#### **Authentication Failures**
1. **Verify API keys** - Check expiration and permissions
2. **Test authentication** - Use curl or Postman
3. **Check network** - Ensure firewall allows connections
4. **Update credentials** - Refresh expired tokens

## 🎯 Next Steps

After setting up integrations:

1. **[Test Voice Commands](../features/voice-interaction.md)** - Verify integration functionality
2. **[Configure AI Providers](../configuration/providers.md)** - Set up AI services
3. **[Advanced Configuration](../configuration/advanced.md)** - Fine-tune settings
4. **[Create Custom Integrations](../guides/custom-integrations.md)** - Build your own

## 🆘 Need Help?

- **Integration Issues?** Check [Troubleshooting](../support/troubleshooting.md)
- **Specific Integrations?** See individual integration guides
- **General Questions?** Browse [FAQ](../support/faq.md)

---

## 🎯 Quick Reference

### **Popular Integrations**
- **HomeAssistant**: Smart home control
- **MQTT**: IoT device communication
- **Weather**: Weather information
- **SMS**: Text messaging
- **Vision**: Image recognition

### **Integration Types**
- **Smart Home**: HomeAssistant, MQTT
- **Communication**: SMS, Email
- **AI Services**: Vision, Voiceprint
- **Data Sources**: Weather, News
- **Development**: MCP, Function calling

### **Setup Checklist**
- ✅ Configure integration settings
- ✅ Test API connectivity
- ✅ Verify authentication
- ✅ Test voice commands
- ✅ Monitor performance

---

**Your integrations are ready! 🎉**

👉 **[Next: Plugin System →](plugins.md)**
