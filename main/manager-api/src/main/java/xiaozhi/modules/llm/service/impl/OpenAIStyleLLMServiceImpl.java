package xiaozhi.modules.llm.service.impl;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.modules.llm.service.LLMService;
import xiaozhi.modules.model.entity.ModelConfigEntity;
import xiaozhi.modules.model.service.ModelConfigService;

/**
 * LLM service implementation for OpenAI-style API
 * Supports models compatible with OpenAI API, such as Alibaba Cloud, DeepSeek, and ChatGLM
 */
@Slf4j
@Service
public class OpenAIStyleLLMServiceImpl implements LLMService {

    // Platform domains requiring thinking mode disabled and their corresponding parameters
    private static final Map<String, Map<String, Object>> THINKING_DISABLED_DOMAINS = new LinkedHashMap<>();
    static {
        THINKING_DISABLED_DOMAINS.put("aliyuncs.com", Map.of("enable_thinking", false));
        Map<String, Object> thinkingDisabled = Map.of("thinking", Map.of("type", "disabled"));
        THINKING_DISABLED_DOMAINS.put("deepseek.com", thinkingDisabled);
        THINKING_DISABLED_DOMAINS.put("bigmodel.cn", thinkingDisabled);
        THINKING_DISABLED_DOMAINS.put("moonshot.cn", thinkingDisabled);
        THINKING_DISABLED_DOMAINS.put("volces.com", thinkingDisabled);
    }

    @Autowired
    private ModelConfigService modelConfigService;

    private final RestTemplate restTemplate = new RestTemplate();

    /**
     * Automatically disable thinking mode based on domain
     */
    private void applyThinkingDisabled(String baseUrl, Map<String, Object> requestBody) {
        for (Map.Entry<String, Map<String, Object>> entry : THINKING_DISABLED_DOMAINS.entrySet()) {
            if (baseUrl.contains(entry.getKey())) {
                requestBody.putAll(entry.getValue());
                log.info("Disable thinking mode for domain {}, params: {}", baseUrl, entry.getValue());
                break;
            }
        }
    }

    private static final String DEFAULT_SUMMARY_PROMPT = "You are an experienced memory summarizer, skilled at summarizing conversation content. Follow these rules: \n 1. Summarize important user information to provide more personalized service in future conversations. 2. Do not repeat summaries or forget previous memories. Unless the original memory exceeds 1800 characters, do not forget or compress the user's historical memory. 3. Do not include content unrelated to the user, such as device volume control, music playback, weather, exit commands, or refusal to converse. 4. Do not include data unrelated to user events, such as today's date/time or today's weather, as storing this as memory affects subsequent conversations. 5. Do not include success or failure results of device control, nor include user filler words. 6. Do not summarize for the sake of summarizing. If the user's chat is meaningless, returning the original history is acceptable. 7. Return only the summary, strictly within 1800 characters. 8. Do not include code or XML. No explanations, comments, or descriptions. Extract information only from the conversation when saving memory; do not mix in example content. 9. If historical memory is provided, intelligently merge new conversation content with historical memory, preserving valuable historical information while adding new important information. Historical Memory: {history_memory} New Conversation Content: {conversation}";

    private static final String DEFAULT_TITLE_PROMPT = "Generate a concise session title (approx. 15 chars) based on the following conversation. Return only the title, with no explanations or punctuation: \n{conversation}";

    @Override
    public String generateSummary(String conversation) {
        return generateSummary(conversation, null, null);
    }

    @Override
    public String generateSummaryWithModel(String conversation, String modelId) {
        return generateSummary(conversation, null, modelId);
    }

    @Override
    public String generateSummary(String conversation, String promptTemplate, String modelId) {
        if (!isAvailable()) {
            log.warn("LLM service unavailable, unable to generate summary");
            return "LLM service unavailable, unable to generate summary";
        }

        try {
            // Fetch LLM model config from Console
            ModelConfigEntity llmConfig;
            if (modelId != null && !modelId.trim().isEmpty()) {
                // Get config by specific model ID
                llmConfig = modelConfigService.getModelByIdFromCache(modelId);
            } else {
                // Maintain backward compatibility using default config
                llmConfig = getDefaultLLMConfig();
            }

            if (llmConfig == null || llmConfig.getConfigJson() == null) {
                log.error("No available LLM model config found, modelId: {}", modelId);
                return "No available LLM model config found";
            }

            JSONObject configJson = llmConfig.getConfigJson();
            String baseUrl = configJson.getStr("base_url");
            String model = configJson.getStr("model_name");
            String apiKey = configJson.getStr("api_key");
            Double temperature = configJson.getDouble("temperature");
            Integer maxTokens = configJson.getInt("max_tokens");

            if (StringUtils.isBlank(baseUrl) || StringUtils.isBlank(apiKey)) {
                log.error("LLM config incomplete: baseUrl or apiKey is empty");
                return "LLM config incomplete, unable to generate summary";
            }

            // Build prompt
            String prompt = (promptTemplate != null ? promptTemplate : DEFAULT_SUMMARY_PROMPT).replace("{conversation}",
                    conversation);

            // Build request body
            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("model", model != null ? model : "gpt-3.5-turbo");

            Map<String, Object> message = new HashMap<>();
            message.put("role", "user");
            message.put("content", prompt);

            requestBody.put("messages", List.of(message));
            requestBody.put("temperature", temperature != null ? temperature : 0.7);
            requestBody.put("max_tokens", maxTokens != null ? maxTokens : 2000);

            // Disable thinking mode
            applyThinkingDisabled(baseUrl, requestBody);

            // Send HTTP request
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.set("Authorization", "Bearer " + apiKey);

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

            // Build the complete API URL
            String apiUrl = baseUrl;
            if (!apiUrl.endsWith("/chat/completions")) {
                if (!apiUrl.endsWith("/")) {
                    apiUrl += "/";
                }
                apiUrl += "chat/completions";
            }

            ResponseEntity<String> response = restTemplate.exchange(
                    apiUrl, HttpMethod.POST, entity, String.class);

            if (response.getStatusCode().is2xxSuccessful()) {
                JSONObject responseJson = JSONUtil.parseObj(response.getBody());
                JSONArray choices = responseJson.getJSONArray("choices");
                if (choices != null && choices.size() > 0) {
                    JSONObject choice = choices.getJSONObject(0);
                    JSONObject messageObj = choice.getJSONObject("message");
                    return messageObj.getStr("content");
                }
            } else {
                log.error("LLM API call failed, status code: {}, response: {}", response.getStatusCode(), response.getBody());
            }
        } catch (Exception e) {
            log.error("Exception occurred while calling LLM service to generate summary, modelId: {}", modelId, e);
        }

        return "Failed to generate summary, please try again later";
    }

    @Override
    public String generateSummary(String conversation, String promptTemplate) {
        return generateSummary(conversation, promptTemplate, null);
    }

    @Override
    public String generateSummaryWithHistory(String conversation, String historyMemory, String promptTemplate,
            String modelId) {
        if (!isAvailable()) {
            log.warn("LLM service unavailable, unable to generate summary");
            return "LLM service unavailable, unable to generate summary";
        }

        try {
            // Fetch LLM model config from Console
            ModelConfigEntity llmConfig;
            if (modelId != null && !modelId.trim().isEmpty()) {
                llmConfig = modelConfigService.getModelByIdFromCache(modelId);
            } else {
                llmConfig = getDefaultLLMConfig();
            }

            if (llmConfig == null || llmConfig.getConfigJson() == null) {
                log.error("No available LLM model config found, modelId: {}", modelId);
                return "No available LLM model config found";
            }

            JSONObject configJson = llmConfig.getConfigJson();
            String baseUrl = configJson.getStr("base_url");
            String model = configJson.getStr("model_name");
            String apiKey = configJson.getStr("api_key");

            if (StringUtils.isBlank(baseUrl) || StringUtils.isBlank(apiKey)) {
                log.error("LLM config incomplete: baseUrl or apiKey is empty");
                return "LLM config incomplete, unable to generate summary";
            }

            // Build the prompt including historical memory
            String prompt = (promptTemplate != null ? promptTemplate : DEFAULT_SUMMARY_PROMPT)
                    .replace("{history_memory}", historyMemory != null ? historyMemory : "No history memory")
                    .replace("{conversation}", conversation);

            // Build request body
            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("model", model != null ? model : "gpt-3.5-turbo");

            Map<String, Object> message = new HashMap<>();
            message.put("role", "user");
            message.put("content", prompt);

            requestBody.put("messages", List.of(message));
            requestBody.put("temperature", 0.2);
            requestBody.put("max_tokens", 2000);

            // Disable thinking mode
            applyThinkingDisabled(baseUrl, requestBody);

            // Send HTTP request
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.set("Authorization", "Bearer " + apiKey);

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

            // Build the complete API URL
            String apiUrl = baseUrl;
            if (!apiUrl.endsWith("/chat/completions")) {
                if (!apiUrl.endsWith("/")) {
                    apiUrl += "/";
                }
                apiUrl += "chat/completions";
            }

            ResponseEntity<String> response = restTemplate.exchange(
                    apiUrl, HttpMethod.POST, entity, String.class);

            if (response.getStatusCode().is2xxSuccessful()) {
                JSONObject responseJson = JSONUtil.parseObj(response.getBody());
                JSONArray choices = responseJson.getJSONArray("choices");
                if (choices != null && choices.size() > 0) {
                    JSONObject choice = choices.getJSONObject(0);
                    JSONObject messageObj = choice.getJSONObject("message");
                    return messageObj.getStr("content");
                }
            } else {
                log.error("LLM API call failed, status code: {}, response: {}", response.getStatusCode(), response.getBody());
            }
        } catch (Exception e) {
            log.error("Exception occurred while calling LLM service to generate summary, modelId: {}", modelId, e);
        }

        return "Failed to generate summary, please try again later";
    }

    @Override
    public boolean isAvailable() {
        try {
            ModelConfigEntity defaultLLMConfig = getDefaultLLMConfig();
            if (defaultLLMConfig == null || defaultLLMConfig.getConfigJson() == null) {
                return false;
            }

            JSONObject configJson = defaultLLMConfig.getConfigJson();
            String baseUrl = configJson.getStr("base_url");
            String apiKey = configJson.getStr("api_key");

            return baseUrl != null && !baseUrl.trim().isEmpty() &&
                    apiKey != null && !apiKey.trim().isEmpty();
        } catch (Exception e) {
            log.error("Exception occurred while checking LLM service availability:", e);
            return false;
        }
    }

    @Override
    public boolean isAvailable(String modelId) {
        try {
            if (modelId == null || modelId.trim().isEmpty()) {
                return isAvailable();
            }

            // Get config by specific model ID
            ModelConfigEntity modelConfig = modelConfigService.getModelByIdFromCache(modelId);
            if (modelConfig == null || modelConfig.getConfigJson() == null) {
                log.warn("Specified LLM model config not found, modelId: {}", modelId);
                return false;
            }

            JSONObject configJson = modelConfig.getConfigJson();
            String baseUrl = configJson.getStr("base_url");
            String apiKey = configJson.getStr("api_key");

            return baseUrl != null && !baseUrl.trim().isEmpty() &&
                    apiKey != null && !apiKey.trim().isEmpty();
        } catch (Exception e) {
            log.error("Exception while checking LLM service availability, modelId: {}", modelId, e);
            return false;
        }
    }

    /**
     * Get default LLM model config from Console
     */
    private ModelConfigEntity getDefaultLLMConfig() {
        try {
            // Get all enabled LLM model configs
            List<ModelConfigEntity> llmConfigs = modelConfigService.getEnabledModelsByType("LLM");
            if (llmConfigs == null || llmConfigs.isEmpty()) {
                return null;
            }

            // Return default config first; if none exists, return the first enabled config
            for (ModelConfigEntity config : llmConfigs) {
                if (config.getIsDefault() != null && config.getIsDefault() == 1) {
                    return config;
                }
            }

            return llmConfigs.get(0);
        } catch (Exception e) {
            log.error("Exception occurred while retrieving LLM model config:", e);
            return null;
        }
    }

    @Override
    public String generateTitle(String conversation, String modelId) {
        if (!isAvailable()) {
            log.warn("LLM service unavailable, unable to generate title");
            return null;
        }

        try {
            ModelConfigEntity llmConfig;
            if (modelId != null && !modelId.trim().isEmpty()) {
                llmConfig = modelConfigService.getModelByIdFromCache(modelId);
            } else {
                llmConfig = getDefaultLLMConfig();
            }

            if (llmConfig == null || llmConfig.getConfigJson() == null) {
                log.error("No available LLM model config found, modelId: {}", modelId);
                return null;
            }

            JSONObject configJson = llmConfig.getConfigJson();
            String baseUrl = configJson.getStr("base_url");
            String model = configJson.getStr("model_name");
            String apiKey = configJson.getStr("api_key");

            if (StringUtils.isBlank(baseUrl) || StringUtils.isBlank(apiKey)) {
                log.error("LLM config incomplete: baseUrl or apiKey is empty");
                return null;
            }

            String prompt = DEFAULT_TITLE_PROMPT.replace("{conversation}", conversation);

            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("model", model != null ? model : "gpt-3.5-turbo");

            Map<String, Object> message = new HashMap<>();
            message.put("role", "user");
            message.put("content", prompt);

            requestBody.put("messages", List.of(message));
            requestBody.put("temperature", 0.3);
            requestBody.put("max_tokens", 50);

            // Disable thinking mode
            applyThinkingDisabled(baseUrl, requestBody);

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.set("Authorization", "Bearer " + apiKey);

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

            String apiUrl = baseUrl;
            if (!apiUrl.endsWith("/chat/completions")) {
                if (!apiUrl.endsWith("/")) {
                    apiUrl += "/";
                }
                apiUrl += "chat/completions";
            }

            ResponseEntity<String> response = restTemplate.exchange(
                    apiUrl, HttpMethod.POST, entity, String.class);

            if (response.getStatusCode().is2xxSuccessful()) {
                JSONObject responseJson = JSONUtil.parseObj(response.getBody());
                JSONArray choices = responseJson.getJSONArray("choices");
                if (choices != null && choices.size() > 0) {
                    JSONObject choice = choices.getJSONObject(0);
                    JSONObject messageObj = choice.getJSONObject("message");
                    String title = messageObj.getStr("content");
                    if (StringUtils.isNotBlank(title)) {
                        title = title.trim().replaceAll("[，。！？、：；''\"\"【】（）]", "");
                        if (title.length() > 15) {
                            title = title.substring(0, 15);
                        }
                        return title;
                    }
                }
            } else {
                log.error("LLM API call failed, status code: {}, response: {}", response.getStatusCode(), response.getBody());
            }
        } catch (Exception e) {
            log.error("Exception occurred while calling LLM service to generate title, modelId: {}", modelId, e);
        }

        return null;
    }
}
