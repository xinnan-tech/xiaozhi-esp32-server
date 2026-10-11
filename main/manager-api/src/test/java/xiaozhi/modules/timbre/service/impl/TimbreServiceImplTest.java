package xiaozhi.modules.timbre.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import xiaozhi.common.redis.RedisUtils;
import xiaozhi.modules.timbre.dao.TimbreDao;
import xiaozhi.modules.timbre.dto.TimbreDataDTO;
import xiaozhi.modules.timbre.entity.TimbreEntity;
import xiaozhi.modules.timbre.vo.TimbreDetailsVO;
import xiaozhi.modules.voiceclone.dao.VoiceCloneDao;
import xiaozhi.modules.voiceclone.entity.VoiceCloneEntity;

class TimbreServiceImplTest {

    @Test
    void defaultLanguageUsesFirstValidRegularTimbreLanguageWithoutCloneQuery() {
        TimbreDao timbreDao = mock(TimbreDao.class);
        VoiceCloneDao voiceCloneDao = mock(VoiceCloneDao.class);
        TimbreServiceImpl service = new TimbreServiceImpl(timbreDao, voiceCloneDao, mock(RedisUtils.class));
        TimbreEntity timbre = new TimbreEntity();
        timbre.setLanguages(",, ; Mandarin; Cantonese");
        when(timbreDao.selectById("voice-id")).thenReturn(timbre);

        assertEquals("Mandarin", service.getDefaultLanguageById("voice-id"));

        verify(voiceCloneDao, never()).selectById("voice-id");
    }

    @Test
    void defaultLanguageFallsBackToCloneTimbre() {
        TimbreDao timbreDao = mock(TimbreDao.class);
        VoiceCloneDao voiceCloneDao = mock(VoiceCloneDao.class);
        TimbreServiceImpl service = new TimbreServiceImpl(timbreDao, voiceCloneDao, mock(RedisUtils.class));
        VoiceCloneEntity voiceClone = new VoiceCloneEntity();
        voiceClone.setLanguages(",, English, Chinese");
        when(voiceCloneDao.selectById("clone-id")).thenReturn(voiceClone);

        assertEquals("English", service.getDefaultLanguageById("clone-id"));
    }

    @Test
    void delimiterOnlyLanguageConfigurationReturnsNull() {
        TimbreDao timbreDao = mock(TimbreDao.class);
        VoiceCloneDao voiceCloneDao = mock(VoiceCloneDao.class);
        TimbreServiceImpl service = new TimbreServiceImpl(timbreDao, voiceCloneDao, mock(RedisUtils.class));
        TimbreEntity timbre = new TimbreEntity();
        timbre.setLanguages(",,,;;;,,");
        when(timbreDao.selectById("voice-id")).thenReturn(timbre);

        assertNull(service.getDefaultLanguageById("voice-id"));
    }

    @Test
    void updateLeavesSortOutOfTheUpdateWhenRequestOmitsIt() {
        TimbreDao timbreDao = mock(TimbreDao.class);
        RedisUtils redisUtils = mock(RedisUtils.class);
        TimbreServiceImpl service = new TimbreServiceImpl(timbreDao, mock(VoiceCloneDao.class), redisUtils);
        ReflectionTestUtils.setField(service, "baseDao", timbreDao);

        TimbreDataDTO dto = validTimbreData();
        service.update("voice-id", dto);

        verify(timbreDao, never()).selectById("voice-id");
        verify(timbreDao).updateById(argThat((TimbreEntity entity) ->
                "voice-id".equals(entity.getId()) && entity.getSort() == null));
        verify(redisUtils).delete("timbre:details:voice-id");
    }

    @Test
    void updateUsesExplicitSortWithoutLoadingExistingTimbre() {
        TimbreDao timbreDao = mock(TimbreDao.class);
        TimbreServiceImpl service = new TimbreServiceImpl(
                timbreDao, mock(VoiceCloneDao.class), mock(RedisUtils.class));
        ReflectionTestUtils.setField(service, "baseDao", timbreDao);
        TimbreDataDTO dto = validTimbreData();
        dto.setSort(0L);

        service.update("voice-id", dto);

        verify(timbreDao, never()).selectById("voice-id");
        verify(timbreDao).updateById(argThat((TimbreEntity entity) -> entity.getSort() == 0L));
    }

    @Test
    void saveDefaultsOmittedSortToZero() {
        TimbreDao timbreDao = mock(TimbreDao.class);
        TimbreServiceImpl service = new TimbreServiceImpl(
                timbreDao, mock(VoiceCloneDao.class), mock(RedisUtils.class));
        ReflectionTestUtils.setField(service, "baseDao", timbreDao);

        service.save(validTimbreData());

        verify(timbreDao).insert(argThat((TimbreEntity entity) ->
                "Test voice".equals(entity.getName()) && entity.getSort() == 0L));
    }

    @Test
    void getSupportsLegacyRowsWithNullSort() {
        TimbreDao timbreDao = mock(TimbreDao.class);
        RedisUtils redisUtils = mock(RedisUtils.class);
        TimbreServiceImpl service = new TimbreServiceImpl(
                timbreDao, mock(VoiceCloneDao.class), redisUtils);
        ReflectionTestUtils.setField(service, "baseDao", timbreDao);
        TimbreEntity entity = new TimbreEntity();
        entity.setId("voice-id");
        entity.setSort(null);
        when(timbreDao.selectById("voice-id")).thenReturn(entity);

        TimbreDetailsVO details = service.get("voice-id");

        assertNull(details.getSort());
    }

    private TimbreDataDTO validTimbreData() {
        TimbreDataDTO dto = new TimbreDataDTO();
        dto.setLanguages("Chinese");
        dto.setName("Test voice");
        dto.setTtsModelId("TTS_Test");
        dto.setTtsVoice("test-voice");
        return dto;
    }
}
