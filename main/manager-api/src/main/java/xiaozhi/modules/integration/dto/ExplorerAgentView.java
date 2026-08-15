package xiaozhi.modules.integration.dto;

public record ExplorerAgentView(
        String id,
        String agentName,
        String systemPrompt,
        String ttsVoiceId,
        String ttsLanguage,
        String llmModelId,
        String asrModelId,
        String ttsModelId) {
}
