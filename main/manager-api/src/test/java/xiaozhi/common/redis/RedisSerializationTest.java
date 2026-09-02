package xiaozhi.common.redis;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;
import org.springframework.data.redis.serializer.RedisSerializer;

import xiaozhi.common.utils.JsonUtils;
import xiaozhi.modules.sys.vo.SysDictDataItem;

class RedisSerializationTest {
    private final RedisSerializer<Object> serializer = RedisSerializer.json();

    @Test
    void serverConfigRoundTripRestoresStringKeyedMaps() {
        Map<String, Object> features = new HashMap<>();
        features.put("addressBook", Map.of("enabled", true));
        Map<String, Object> config = new HashMap<>();
        config.put("features", features);

        Object restored = roundTrip(config);
        Map<String, Object> restoredConfig = JsonUtils.toStringObjectMap(restored);
        Map<String, Object> restoredFeatures = JsonUtils.toStringObjectMap(restoredConfig.get("features"));
        Map<String, Object> addressBook = JsonUtils.toStringObjectMap(restoredFeatures.get("addressBook"));

        assertEquals(true, addressBook.get("enabled"));
    }

    @Test
    void dictionaryListRoundTripRestoresDtoElements() {
        SysDictDataItem item = new SysDictDataItem();
        item.setName("enabled");
        item.setKey("1");

        Object restored = roundTrip(new ArrayList<>(List.of(item)));
        List<SysDictDataItem> restoredItems = JsonUtils.toList(restored, SysDictDataItem.class);

        assertInstanceOf(SysDictDataItem.class, restoredItems.get(0));
        assertEquals("enabled", restoredItems.get(0).getName());
        assertEquals("1", restoredItems.get(0).getKey());
    }

    private Object roundTrip(Object value) {
        byte[] bytes = serializer.serialize(value);
        assertNotNull(bytes);
        Object restored = serializer.deserialize(bytes);
        assertNotNull(restored);
        return restored;
    }
}
