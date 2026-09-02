package xiaozhi.modules.agent.dto;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.LinkedHashMap;
import java.util.Map;

import org.junit.jupiter.api.Test;

class AgentUpdateDTOTest {

    @Test
    void functionInfoAcceptsJsonStringParamInfo() {
        AgentUpdateDTO.FunctionInfo info = new AgentUpdateDTO.FunctionInfo();

        info.setParamInfo("{\"api_key\":\"abc\",\"max_results\":5}");

        assertEquals("abc", info.getParamInfo().get("api_key"));
        assertEquals(5, info.getParamInfo().get("max_results"));
    }

    @Test
    void functionInfoNormalizesMapKeysToStrings() {
        AgentUpdateDTO.FunctionInfo info = new AgentUpdateDTO.FunctionInfo();
        Map<Object, Object> params = new LinkedHashMap<>();
        params.put("api_key", "abc");
        params.put(42, true);

        info.setParamInfo(params);

        assertEquals("abc", info.getParamInfo().get("api_key"));
        assertEquals(true, info.getParamInfo().get("42"));
    }

    @Test
    void functionInfoFallsBackToEmptyMapForBlankParamInfo() {
        AgentUpdateDTO.FunctionInfo info = new AgentUpdateDTO.FunctionInfo();

        info.setParamInfo(" ");

        assertTrue(info.getParamInfo().isEmpty());
    }
}
