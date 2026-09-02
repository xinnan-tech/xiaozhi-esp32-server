package xiaozhi.modules.agent.Enums;

import java.util.Arrays;
import java.util.List;
import java.util.function.BiConsumer;
import java.util.function.Function;

import lombok.Getter;
import xiaozhi.modules.agent.dto.AgentSnapshotDataDTO;
import xiaozhi.modules.agent.dto.AgentUpdateDTO;
import xiaozhi.modules.agent.entity.AgentEntity;

@Getter
public enum AgentSnapshotField {
    AGENT_CODE("agentCode", AgentSnapshotDataDTO::getAgentCode, AgentUpdateDTO::getAgentCode,
            (agent, data) -> agent.setAgentCode(data.getAgentCode())),
    AGENT_NAME("agentName", AgentSnapshotDataDTO::getAgentName, AgentUpdateDTO::getAgentName,
            (agent, data) -> agent.setAgentName(data.getAgentName())),
    ASR_MODEL_ID("asrModelId", AgentSnapshotDataDTO::getAsrModelId, AgentUpdateDTO::getAsrModelId,
            (agent, data) -> agent.setAsrModelId(data.getAsrModelId())),
    VAD_MODEL_ID("vadModelId", AgentSnapshotDataDTO::getVadModelId, AgentUpdateDTO::getVadModelId,
            (agent, data) -> agent.setVadModelId(data.getVadModelId())),
    LLM_MODEL_ID("llmModelId", AgentSnapshotDataDTO::getLlmModelId, AgentUpdateDTO::getLlmModelId,
            (agent, data) -> agent.setLlmModelId(data.getLlmModelId())),
    SLM_MODEL_ID("slmModelId", AgentSnapshotDataDTO::getSlmModelId, AgentUpdateDTO::getSlmModelId,
            (agent, data) -> agent.setSlmModelId(data.getSlmModelId())),
    VLLM_MODEL_ID("vllmModelId", AgentSnapshotDataDTO::getVllmModelId, AgentUpdateDTO::getVllmModelId,
            (agent, data) -> agent.setVllmModelId(data.getVllmModelId())),
    TTS_MODEL_ID("ttsModelId", AgentSnapshotDataDTO::getTtsModelId, AgentUpdateDTO::getTtsModelId,
            (agent, data) -> agent.setTtsModelId(data.getTtsModelId())),
    TTS_VOICE_ID("ttsVoiceId", AgentSnapshotDataDTO::getTtsVoiceId, AgentUpdateDTO::getTtsVoiceId,
            (agent, data) -> agent.setTtsVoiceId(data.getTtsVoiceId())),
    TTS_LANGUAGE("ttsLanguage", AgentSnapshotDataDTO::getTtsLanguage, AgentUpdateDTO::getTtsLanguage,
            (agent, data) -> agent.setTtsLanguage(data.getTtsLanguage())),
    TTS_VOLUME("ttsVolume", AgentSnapshotDataDTO::getTtsVolume, AgentUpdateDTO::getTtsVolume,
            (agent, data) -> agent.setTtsVolume(data.getTtsVolume())),
    TTS_RATE("ttsRate", AgentSnapshotDataDTO::getTtsRate, AgentUpdateDTO::getTtsRate,
            (agent, data) -> agent.setTtsRate(data.getTtsRate())),
    TTS_PITCH("ttsPitch", AgentSnapshotDataDTO::getTtsPitch, AgentUpdateDTO::getTtsPitch,
            (agent, data) -> agent.setTtsPitch(data.getTtsPitch())),
    MEM_MODEL_ID("memModelId", AgentSnapshotDataDTO::getMemModelId, AgentUpdateDTO::getMemModelId,
            (agent, data) -> agent.setMemModelId(data.getMemModelId())),
    INTENT_MODEL_ID("intentModelId", AgentSnapshotDataDTO::getIntentModelId, AgentUpdateDTO::getIntentModelId,
            (agent, data) -> agent.setIntentModelId(data.getIntentModelId())),
    CHAT_HISTORY_CONF("chatHistoryConf", AgentSnapshotDataDTO::getChatHistoryConf, AgentUpdateDTO::getChatHistoryConf,
            (agent, data) -> agent.setChatHistoryConf(data.getChatHistoryConf())),
    SYSTEM_PROMPT("systemPrompt", AgentSnapshotDataDTO::getSystemPrompt, AgentUpdateDTO::getSystemPrompt,
            (agent, data) -> agent.setSystemPrompt(data.getSystemPrompt())),
    SUMMARY_MEMORY("summaryMemory", AgentSnapshotDataDTO::getSummaryMemory, AgentUpdateDTO::getSummaryMemory,
            (agent, data) -> agent.setSummaryMemory(data.getSummaryMemory())),
    LANG_CODE("langCode", AgentSnapshotDataDTO::getLangCode, AgentUpdateDTO::getLangCode,
            (agent, data) -> agent.setLangCode(data.getLangCode())),
    LANGUAGE("language", AgentSnapshotDataDTO::getLanguage, AgentUpdateDTO::getLanguage,
            (agent, data) -> agent.setLanguage(data.getLanguage())),
    SORT("sort", AgentSnapshotDataDTO::getSort, AgentUpdateDTO::getSort,
            (agent, data) -> agent.setSort(data.getSort())),
    FUNCTIONS("functions", AgentSnapshotDataDTO::getFunctions, AgentUpdateDTO::getFunctions, null),
    CONTEXT_PROVIDERS("contextProviders", AgentSnapshotDataDTO::getContextProviders,
            AgentUpdateDTO::getContextProviders, null),
    CORRECT_WORD_FILE_IDS("correctWordFileIds", AgentSnapshotDataDTO::getCorrectWordFileIds,
            AgentUpdateDTO::getCorrectWordFileIds, null),
    TAG_NAMES("tagNames", AgentSnapshotDataDTO::getTagNames, AgentUpdateDTO::getTagNames, null);

    private final String fieldName;
    private final Function<AgentSnapshotDataDTO, Object> snapshotGetter;
    private final Function<AgentUpdateDTO, Object> updateGetter;
    private final BiConsumer<AgentEntity, AgentSnapshotDataDTO> restoreApplier;

    AgentSnapshotField(String fieldName, Function<AgentSnapshotDataDTO, Object> snapshotGetter,
            Function<AgentUpdateDTO, Object> updateGetter,
            BiConsumer<AgentEntity, AgentSnapshotDataDTO> restoreApplier) {
        this.fieldName = fieldName;
        this.snapshotGetter = snapshotGetter;
        this.updateGetter = updateGetter;
        this.restoreApplier = restoreApplier;
    }

    public static List<String> names() {
        return Arrays.stream(values()).map(AgentSnapshotField::getFieldName).toList();
    }

    public static String canonicalName(String fieldName) {
        return "tags".equals(fieldName) ? TAG_NAMES.getFieldName() : fieldName;
    }

    public Object snapshotValue(AgentSnapshotDataDTO data) {
        return data == null ? null : snapshotGetter.apply(data);
    }

    public Object updateValue(AgentUpdateDTO data) {
        return data == null ? null : updateGetter.apply(data);
    }

    public boolean isRestorableAgentField() {
        return restoreApplier != null;
    }

    public void applyTo(AgentEntity agent, AgentSnapshotDataDTO data) {
        if (restoreApplier != null) {
            restoreApplier.accept(agent, data);
        }
    }
}
