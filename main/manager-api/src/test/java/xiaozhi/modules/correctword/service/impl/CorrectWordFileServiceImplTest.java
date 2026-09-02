package xiaozhi.modules.correctword.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import xiaozhi.modules.agent.dao.AgentCorrectWordMappingDao;
import xiaozhi.modules.agent.entity.AgentCorrectWordMappingEntity;
import xiaozhi.modules.correctword.dao.CorrectWordFileDao;
import xiaozhi.modules.correctword.dao.CorrectWordItemDao;
import xiaozhi.modules.correctword.entity.CorrectWordFileEntity;
import xiaozhi.modules.correctword.entity.CorrectWordItemEntity;
import xiaozhi.modules.correctword.vo.CorrectWordFileVO;
import xiaozhi.modules.correctword.vo.CorrectWordSimpleVO;

class CorrectWordFileServiceImplTest {

    private static final String AGENT_ID = "agent-1";
    private static final String FILE_ID = "file-1";

    private final CorrectWordFileDao fileDao = mock(CorrectWordFileDao.class);
    private final CorrectWordItemDao itemDao = mock(CorrectWordItemDao.class);
    private final AgentCorrectWordMappingDao mappingDao = mock(AgentCorrectWordMappingDao.class);
    private final CorrectWordFileServiceImpl service =
            new CorrectWordFileServiceImpl(fileDao, itemDao, mappingDao);

    @Test
    void getAllItemsByAgentId_returns_empty_list_when_no_mappings() {
        when(mappingDao.selectByAgentId(AGENT_ID)).thenReturn(Collections.emptyList());

        List<CorrectWordSimpleVO> result = service.getAllItemsByAgentId(AGENT_ID);

        assertTrue(result.isEmpty());
        verify(itemDao, never()).selectList(org.mockito.ArgumentMatchers.any());
    }

    @Test
    void getAllItemsByAgentId_returns_mapped_items_when_mappings_exist() {
        AgentCorrectWordMappingEntity mapping = new AgentCorrectWordMappingEntity();
        mapping.setFileId(FILE_ID);
        when(mappingDao.selectByAgentId(AGENT_ID)).thenReturn(List.of(mapping));

        CorrectWordItemEntity item = new CorrectWordItemEntity();
        item.setSourceWord("hello");
        item.setTargetWord("hi");
        when(itemDao.selectList(org.mockito.ArgumentMatchers.any())).thenReturn(List.of(item));

        List<CorrectWordSimpleVO> result = service.getAllItemsByAgentId(AGENT_ID);

        assertEquals(1, result.size());
        assertEquals("hello", result.get(0).getSourceWord());
        assertEquals("hi", result.get(0).getTargetWord());
    }

    @Test
    void getAllItemsByAgentId_returns_empty_list_when_mappings_are_null() {
        when(mappingDao.selectByAgentId(AGENT_ID)).thenReturn(null);

        List<CorrectWordSimpleVO> result = service.getAllItemsByAgentId(AGENT_ID);

        assertNotNull(result);
        assertTrue(result.isEmpty());
    }

    @Test
    void getAgentCorrectWordFileIds_returns_empty_list_when_no_mappings() {
        when(mappingDao.selectByAgentId(AGENT_ID)).thenReturn(Collections.emptyList());

        List<String> result = service.getAgentCorrectWordFileIds(AGENT_ID);

        assertTrue(result.isEmpty());
    }

    @Test
    void getAgentCorrectWordFileIds_returns_file_ids_when_mappings_exist() {
        AgentCorrectWordMappingEntity m1 = new AgentCorrectWordMappingEntity();
        m1.setFileId("f1");
        AgentCorrectWordMappingEntity m2 = new AgentCorrectWordMappingEntity();
        m2.setFileId("f2");
        when(mappingDao.selectByAgentId(AGENT_ID)).thenReturn(List.of(m1, m2));

        List<String> result = service.getAgentCorrectWordFileIds(AGENT_ID);

        assertEquals(List.of("f1", "f2"), result);
    }

    @Test
    void getFileContent_returns_null_when_entity_not_found() {
        when(fileDao.selectById(FILE_ID)).thenReturn(null);

        CorrectWordFileVO result = service.getFileContent(FILE_ID);

        assertNull(result);
    }

    @Test
    void getFileContent_returns_vo_when_entity_found() {
        CorrectWordFileEntity entity = new CorrectWordFileEntity();
        entity.setId(FILE_ID);
        entity.setFileName("dict.txt");
        entity.setWordCount(2);
        entity.setContent("hello|hi\nbye|goodbye");
        entity.setCreatedAt(new Date());
        when(fileDao.selectById(FILE_ID)).thenReturn(entity);

        CorrectWordFileVO result = service.getFileContent(FILE_ID);

        assertNotNull(result);
        assertEquals(FILE_ID, result.getId());
        assertEquals("dict.txt", result.getFileName());
        assertEquals(2, result.getWordCount().intValue());
        assertEquals(2, result.getContent().size());
        assertEquals("hello|hi", result.getContent().get(0));
    }

    @Test
    void deleteMappingsByAgentId_delegates_to_dao() {
        service.deleteMappingsByAgentId(AGENT_ID);

        verify(mappingDao).deleteByAgentId(AGENT_ID);
    }

    @Test
    void batchDeleteFiles_skips_null_and_empty_ids() {
        List<String> ids = new ArrayList<>();
        ids.add(null);
        ids.add("");
        ids.add("   ");
        ids.add(FILE_ID);

        service.batchDeleteFiles(ids);

        verify(fileDao).deleteById(FILE_ID);
    }
}
