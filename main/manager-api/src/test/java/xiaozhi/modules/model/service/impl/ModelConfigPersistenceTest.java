package xiaozhi.modules.model.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

import java.util.UUID;

import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

import cn.hutool.json.JSONObject;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.modules.model.dto.ModelConfigBodyDTO;
import xiaozhi.modules.model.dto.ModelConfigDTO;
import xiaozhi.modules.model.service.ModelConfigService;

@SpringBootTest
@ActiveProfiles("dev")
@Transactional
class ModelConfigPersistenceTest {

    @Autowired
    private ModelConfigService service;

    @Autowired
    private JdbcTemplate jdbc;

    @Autowired
    private RedisUtils redis;

    @ParameterizedTest
    @CsvSource({"tts,TTS", "memory,Memory", "intent,Intent"})
    void preservesRegisteredTypeWhenAddingAndEditing(String requestedType, String registeredType) {
        String id = UUID.randomUUID().toString().replace("-", "");
        String providerCode = "test-" + id;
        jdbc.update("INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields) VALUES (?, ?, ?, ?, ?)",
                id, registeredType, providerCode, "Persistence test provider", "[]");

        ModelConfigBodyDTO body = new ModelConfigBodyDTO();
        body.setId(id);
        body.setModelCode(providerCode);
        body.setModelName("Persistence test model");
        body.setIsDefault(0);
        body.setIsEnabled(1);
        body.setSort(1);
        body.setConfigJson(new JSONObject().set("type", providerCode));

        ModelConfigDTO added = service.add(requestedType, providerCode, body);
        assertEquals(registeredType, added.getModelType());
        assertEquals(registeredType,
                jdbc.queryForObject("SELECT model_type FROM ai_model_config WHERE id = ?", String.class, id));

        String cacheKey = RedisKeys.getModelConfigById(id);
        try {
            redis.set(cacheKey, "cached model");
            body.setModelName("Updated persistence test model");
            ModelConfigDTO edited = service.edit(requestedType, providerCode, id, body);

            assertEquals(registeredType, edited.getModelType());
            assertEquals(registeredType,
                    jdbc.queryForObject("SELECT model_type FROM ai_model_config WHERE id = ?", String.class, id));
            assertEquals(body.getModelName(),
                    jdbc.queryForObject("SELECT model_name FROM ai_model_config WHERE id = ?", String.class, id));
            assertNull(redis.get(cacheKey));
        } finally {
            redis.delete(cacheKey);
        }
    }
}
