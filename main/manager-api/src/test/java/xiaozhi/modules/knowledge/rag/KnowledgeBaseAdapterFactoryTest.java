package xiaozhi.modules.knowledge.rag;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.Mockito.mockStatic;

import java.util.Map;
import java.util.Set;
import java.util.function.Consumer;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.MockedStatic;

import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.utils.MessageUtils;
import xiaozhi.modules.knowledge.dto.KnowledgeFilesDTO;
import xiaozhi.modules.knowledge.dto.dataset.DatasetDTO;
import xiaozhi.modules.knowledge.dto.document.ChunkDTO;
import xiaozhi.modules.knowledge.dto.document.DocumentDTO;
import xiaozhi.modules.knowledge.dto.document.RetrievalDTO;

class KnowledgeBaseAdapterFactoryTest {

    private static final String REGISTERED_TYPE = "kb-test-registered";
    private static final String UNKNOWN_TYPE = "kb-test-unknown";

    @BeforeEach
    void resetCache() {
        KnowledgeBaseAdapterFactory.clearCache();
    }

    @AfterEach
    void cleanupCache() {
        KnowledgeBaseAdapterFactory.clearCache();
        KnowledgeBaseAdapterFactory.removeCacheByType(REGISTERED_TYPE);
    }

    @Test
    void getAdapter_returns_non_null_instance_for_registered_type() {
        KnowledgeBaseAdapterFactory.registerAdapter(REGISTERED_TYPE, StubAdapter.class);

        KnowledgeBaseAdapter adapter = KnowledgeBaseAdapterFactory.getAdapter(REGISTERED_TYPE);

        assertNotNull(adapter);
        assertEquals(REGISTERED_TYPE, adapter.getAdapterType());
    }

    @Test
    void getAdapter_returns_cached_instance_for_repeated_calls() {
        KnowledgeBaseAdapterFactory.registerAdapter(REGISTERED_TYPE, StubAdapter.class);

        KnowledgeBaseAdapter first = KnowledgeBaseAdapterFactory.getAdapter(REGISTERED_TYPE);
        KnowledgeBaseAdapter second = KnowledgeBaseAdapterFactory.getAdapter(REGISTERED_TYPE);

        assertSame(first, second);
    }

    @Test
    void getAdapter_throws_RenException_for_unknown_type() {
        try (MockedStatic<MessageUtils> messageUtils = mockStatic(MessageUtils.class)) {
            messageUtils.when(() -> MessageUtils.getMessage(anyInt())).thenReturn("mocked message");
            messageUtils.when(() -> MessageUtils.getMessage(anyInt(), any(String[].class)))
                    .thenReturn("mocked message");

            RenException ex = assertThrows(RenException.class,
                    () -> KnowledgeBaseAdapterFactory.getAdapter(UNKNOWN_TYPE));

            assertEquals(ErrorCode.RAG_ADAPTER_TYPE_NOT_SUPPORTED, ex.getCode());
        }
    }

    @Test
    void isAdapterTypeRegistered_returns_true_for_registered_types() {
        KnowledgeBaseAdapterFactory.registerAdapter(REGISTERED_TYPE, StubAdapter.class);

        assertTrue(KnowledgeBaseAdapterFactory.isAdapterTypeRegistered(REGISTERED_TYPE));
        assertTrue(KnowledgeBaseAdapterFactory.isAdapterTypeRegistered("ragflow"));
        assertFalse(KnowledgeBaseAdapterFactory.isAdapterTypeRegistered(UNKNOWN_TYPE));
    }

    @Test
    void getRegisteredAdapterTypes_contains_all_registered_types() {
        KnowledgeBaseAdapterFactory.registerAdapter(REGISTERED_TYPE, StubAdapter.class);

        Set<String> types = KnowledgeBaseAdapterFactory.getRegisteredAdapterTypes();

        assertTrue(types.contains(REGISTERED_TYPE));
        assertTrue(types.contains("ragflow"));
    }

    @Test
    void clearCache_empties_cached_instance_count() {
        KnowledgeBaseAdapterFactory.registerAdapter(REGISTERED_TYPE, StubAdapter.class);
        KnowledgeBaseAdapterFactory.getAdapter(REGISTERED_TYPE);

        KnowledgeBaseAdapterFactory.clearCache();
        Map<String, Object> status = KnowledgeBaseAdapterFactory.getFactoryStatus();

        assertEquals(0, status.get("cachedAdapterCount"));
    }

    /**
     * Test stub adapter that satisfies the abstract API surface so the factory's
     * reflection-based instantiation works in the unit test.
     */
    public static class StubAdapter extends KnowledgeBaseAdapter {
        @Override
        public String getAdapterType() {
            return REGISTERED_TYPE;
        }

        @Override
        public void initialize(Map<String, Object> config) {
        }

        @Override
        public boolean validateConfig(Map<String, Object> config) {
            return true;
        }

        @Override
        public PageData<KnowledgeFilesDTO> getDocumentList(String datasetId,
                DocumentDTO.ListReq req) {
            return new PageData<>(java.util.Collections.emptyList(), 0);
        }

        @Override
        public DocumentDTO.InfoVO getDocumentById(String datasetId, String documentId) {
            return null;
        }

        @Override
        public KnowledgeFilesDTO uploadDocument(DocumentDTO.UploadReq req) {
            return null;
        }

        @Override
        public PageData<KnowledgeFilesDTO> getDocumentListByStatus(String datasetId,
                Integer status, Integer page, Integer limit) {
            return new PageData<>(java.util.Collections.emptyList(), 0);
        }

        @Override
        public void deleteDocument(String datasetId, DocumentDTO.BatchIdReq req) {
        }

        @Override
        public boolean parseDocuments(String datasetId, java.util.List<String> documentIds) {
            return true;
        }

        @Override
        public ChunkDTO.ListVO listChunks(String datasetId, String documentId,
                ChunkDTO.ListReq req) {
            return null;
        }

        @Override
        public RetrievalDTO.ResultVO retrievalTest(RetrievalDTO.TestReq req) {
            return null;
        }

        @Override
        public boolean testConnection() {
            return true;
        }

        @Override
        public Map<String, Object> getStatus() {
            return java.util.Collections.emptyMap();
        }

        @Override
        public Map<String, Object> getSupportedConfig() {
            return java.util.Collections.emptyMap();
        }

        @Override
        public Map<String, Object> getDefaultConfig() {
            return java.util.Collections.emptyMap();
        }

        @Override
        public DatasetDTO.InfoVO createDataset(DatasetDTO.CreateReq req) {
            return null;
        }

        @Override
        public DatasetDTO.InfoVO updateDataset(String datasetId, DatasetDTO.UpdateReq req) {
            return null;
        }

        @Override
        public DatasetDTO.BatchOperationVO deleteDataset(DatasetDTO.BatchIdReq req) {
            return null;
        }

        @Override
        public Integer getDocumentCount(String datasetId) {
            return 0;
        }

        @Override
        public DatasetDTO.InfoVO getDatasetInfo(String datasetId) {
            return null;
        }

        @Override
        public void postStream(String endpoint, Object body, Consumer<String> onData) {
        }

        @Override
        public Object postSearchBotAsk(Map<String, Object> config, Object body,
                Consumer<String> onData) {
            return null;
        }

        @Override
        public void postAgentBotCompletion(Map<String, Object> config, String agentId,
                Object body, Consumer<String> onData) {
        }
    }
}
