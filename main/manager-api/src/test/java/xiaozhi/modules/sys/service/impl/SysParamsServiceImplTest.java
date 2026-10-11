package xiaozhi.modules.sys.service.impl;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import xiaozhi.common.constant.Constant;
import xiaozhi.modules.agent.service.AgentPluginMappingService;
import xiaozhi.modules.sys.dao.SysParamsDao;
import xiaozhi.modules.sys.redis.SysParamsRedis;

class SysParamsServiceImplTest {

    @Test
    void disablingAddressBookStillDeletesItsSystemPlugin() {
        SysParamsRedis sysParamsRedis = mock(SysParamsRedis.class);
        AgentPluginMappingService pluginMappingService = mock(AgentPluginMappingService.class);
        SysParamsDao sysParamsDao = mock(SysParamsDao.class);
        SysParamsServiceImpl service = new SysParamsServiceImpl(sysParamsRedis, pluginMappingService);
        ReflectionTestUtils.setField(service, "baseDao", sysParamsDao);

        String currentConfig = "{\"features\":{\"addressBook\":{\"enabled\":true}}}";
        String newConfig = "{\"features\":{\"addressBook\":{\"enabled\":false}}}";
        when(sysParamsDao.getValueByCode(Constant.SYSTEM_WEB_MENU)).thenReturn(currentConfig);
        when(sysParamsDao.updateValueByCode(Constant.SYSTEM_WEB_MENU, newConfig)).thenReturn(1);

        service.updateSystemWebMenu(newConfig);

        verify(pluginMappingService).deleteByPluginId("SYSTEM_PLUGIN_CALL_DEVICE");
        verify(sysParamsDao).updateValueByCode(Constant.SYSTEM_WEB_MENU, newConfig);
        verify(sysParamsRedis).set(Constant.SYSTEM_WEB_MENU, newConfig);
    }
}
