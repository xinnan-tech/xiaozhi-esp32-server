package xiaozhi.modules.model.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.mockStatic;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.List;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;
import org.mockito.ArgumentCaptor;
import org.mockito.MockedStatic;

import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.utils.MessageUtils;
import xiaozhi.modules.agent.dao.AgentDao;
import xiaozhi.modules.model.dao.ModelConfigDao;
import xiaozhi.modules.model.dto.ModelConfigBodyDTO;
import xiaozhi.modules.model.dto.ModelConfigDTO;
import xiaozhi.modules.model.dto.ModelProviderDTO;
import xiaozhi.modules.model.entity.ModelConfigEntity;
import xiaozhi.modules.model.service.ModelProviderService;

class ModelConfigServiceImplTest {

    private ModelConfigDao modelConfigDao;
    private ModelProviderService modelProviderService;
    private ModelConfigServiceImpl service;

    @BeforeEach
    void setUp() {
        modelConfigDao = mock(ModelConfigDao.class);
        modelProviderService = mock(ModelProviderService.class);
        service = new ModelConfigServiceImpl(
                modelConfigDao, modelProviderService, mock(RedisUtils.class), mock(AgentDao.class));
    }

    @ParameterizedTest
    @CsvSource({
            "vad, VAD", "asr, ASR", "tts, TTS", "llm, LLM", "vllm, VLLM",
            "memory, Memory", "intent, Intent", "rag, RAG", "LLM, LLM"
    })
    void addPreservesRegisteredProviderModelType(String requestedType, String registeredType) {
        registerProvider(requestedType, registeredType);

        ModelConfigDTO result = service.add(requestedType, "test-provider", modelBody());

        ArgumentCaptor<ModelConfigEntity> saved = ArgumentCaptor.forClass(ModelConfigEntity.class);
        verify(modelConfigDao).insert(saved.capture());
        assertEquals(registeredType, saved.getValue().getModelType());
        assertEquals(registeredType, result.getModelType());
    }

    @ParameterizedTest
    @CsvSource({
            "vad, VAD", "asr, ASR", "tts, TTS", "llm, LLM", "vllm, VLLM",
            "memory, Memory", "intent, Intent", "rag, RAG", "LLM, LLM"
    })
    void editPreservesRegisteredProviderModelType(String requestedType, String registeredType) {
        registerProvider(requestedType, registeredType);
        ModelConfigEntity original = new ModelConfigEntity();
        original.setId("test-model");
        original.setModelType(registeredType);
        when(modelConfigDao.selectById("test-model")).thenReturn(original);

        ModelConfigDTO result = service.edit(requestedType, "test-provider", "test-model", modelBody());

        ArgumentCaptor<ModelConfigEntity> saved = ArgumentCaptor.forClass(ModelConfigEntity.class);
        verify(modelConfigDao).updateById(saved.capture());
        assertEquals(registeredType, saved.getValue().getModelType());
        assertEquals(registeredType, result.getModelType());
    }

    @ParameterizedTest
    @ValueSource(booleans = {false, true})
    void rejectsUnknownProviderBeforeWriting(boolean editing) {
        when(modelProviderService.getList("tts", "missing")).thenReturn(List.of());

        try (MockedStatic<MessageUtils> messages = mockStatic(MessageUtils.class)) {
            messages.when(() -> MessageUtils.getMessage(ErrorCode.MODEL_PROVIDER_NOT_EXIST))
                    .thenReturn("Model provider does not exist");
            RenException error = assertThrows(RenException.class, () -> {
                if (editing) {
                    service.edit("tts", "missing", "test-model", modelBody());
                } else {
                    service.add("tts", "missing", modelBody());
                }
            });
            assertEquals(ErrorCode.MODEL_PROVIDER_NOT_EXIST, error.getCode());
        }

        verify(modelConfigDao, never()).insert(any(ModelConfigEntity.class));
        verify(modelConfigDao, never()).updateById(any(ModelConfigEntity.class));
    }

    private void registerProvider(String requestedType, String registeredType) {
        ModelProviderDTO provider = new ModelProviderDTO();
        provider.setModelType(registeredType);
        provider.setProviderCode("test-provider");
        when(modelProviderService.getList(requestedType, "test-provider")).thenReturn(List.of(provider));
    }

    private ModelConfigBodyDTO modelBody() {
        ModelConfigBodyDTO body = new ModelConfigBodyDTO();
        body.setId("test-model");
        body.setModelName("Test model");
        body.setIsEnabled(1);
        body.setSort(1);
        return body;
    }
}
