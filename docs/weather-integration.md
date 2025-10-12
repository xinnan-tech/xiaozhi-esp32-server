# Weather Plugin Usage Guide

## Overview

The `get_weather` weather plugin is a core feature of Xiaozhi's ESP32 voice assistant, allowing you to query weather information for locations across the country via voice. Based on the Hefeng Weather API, the plugin provides real-time weather and a 7-day forecast.

## API Key Application Guide

### 1. Register a Hefeng Weather account

1. Visit the QWeather console
2. Register an account and complete email verification
3. Log in to the console

### 2. Create an application and obtain an API Key

1. After entering the console, click ["Project Management"](https://console.qweather.com/project?lang=zh) on the right → "Create Project"
2. Fill in the project information:
   - **Project Name**: such as "Xiaozhi Voice Assistant"
3. Click Save
4. After the project is created, click "Create Credentials" in the project
5. Fill in the credentials:
    - **Credential Name**: such as "Xiaozhi Voice Assistant"
    - **Authentication method**: Select "API Key"
6. Click Save
7. Copy the `API Key` in the credentials, which is the first key configuration information

### 3. Get the API Host

1. In the console, click "Settings" → "API Host"
2. Check the dedicated `API Host` address assigned to you. This is the second key configuration information.

The above operation will get two important configuration information: `API Key` and `API Host`

## Configuration method (choose one)

### Method 1. If you use the Smart Console deployment (recommended)

1. Log in to the smart console
2. Enter the "Role Configuration" page
3. Select the agent to configure
4. Click the "Edit Function" button
5. Find the "Weather Query" plug-in in the parameter configuration area on the right
6. Check "Weather Query"
7. Fill in the copied first key configuration `API Key` into the `Weather Plugin API Key`
8. Fill in the copied second key configuration `API Host` into `Developer API Host`
9. Save the configuration, then save the agent configuration

### Method 2. If you only deploy a single module xiaozhi-server

Configure in `data/.config.yaml`:

1. Fill in the copied first key configuration `API Key` into `api_key`
2. Fill in the copied second key configuration `API Host` into `api_host`
3. Fill in your city in `default_location`, for example, `Guangzhou`

```yaml
plugins:
  get_weather:
    api_key: "Your Zephyr Weather API key"
    api_host: "Your Zefeng Weather API host address"
    default_location: "Your default query city"
```
