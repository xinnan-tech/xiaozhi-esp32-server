package xiaozhi.common.utils;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;

class JsonUtilsTest {

    @Test
    void parsesTypedMapsAndPreservesNestedCollectionShapes() {
        Map<String, Object> map = JsonUtils.parseMap(
                "{\"enabled\":true,\"nested\":{\"items\":[{\"name\":\"tool\"}]}}");
        Map<?, ?> nested = assertInstanceOf(Map.class, map.get("nested"));
        List<?> items = assertInstanceOf(List.class, nested.get("items"));
        Map<?, ?> item = assertInstanceOf(Map.class, items.get(0));

        assertEquals(true, map.get("enabled"));
        assertEquals("tool", item.get("name"));

        List<Map<String, Object>> maps = JsonUtils.parseMapList(
                "[{\"name\":\"first\",\"values\":[1,2]},{\"name\":\"second\"}]");
        assertEquals("first", maps.get(0).get("name"));
        assertEquals(List.of(1, 2), maps.get(0).get("values"));
        assertEquals("second", maps.get(1).get("name"));
    }

    @Test
    void checkedConvertersAreShallowMutableCopies() {
        List<Object> nested = new ArrayList<>(List.of(Map.of("name", "tool")));
        Map<String, Object> source = new LinkedHashMap<>();
        source.put("nested", nested);

        Map<String, Object> map = JsonUtils.toStringObjectMap(source);
        List<Map<String, Object>> maps = JsonUtils.toStringObjectMapList(List.of(source));
        List<String> strings = JsonUtils.toList(Arrays.asList("a", null), String.class);

        assertSame(nested, map.get("nested"));
        assertSame(nested, maps.get(0).get("nested"));
        map.put("enabled", true);
        maps.add(Map.of("name", "second"));
        strings.add("b");
        assertEquals(true, map.get("enabled"));
        assertEquals(2, maps.size());
        assertEquals(Arrays.asList("a", null, "b"), strings);
    }

    @Test
    void preservesNullInputs() {
        assertNull(JsonUtils.parseMap(""));
        assertNull(JsonUtils.parseMapList(null));
        assertNull(JsonUtils.toStringObjectMap(null));
        assertNull(JsonUtils.toStringObjectMapList(null));
        assertNull(JsonUtils.toList(null, String.class));
    }

    @Test
    void rejectsUnexpectedJsonShapesAndRuntimeTypes() {
        assertThrows(RuntimeException.class, () -> JsonUtils.parseMap("[]"));
        assertThrows(RuntimeException.class, () -> JsonUtils.parseMapList("{}"));
        assertThrows(ClassCastException.class, () -> JsonUtils.toStringObjectMap(List.of()));
        assertThrows(ClassCastException.class, () -> JsonUtils.toStringObjectMap(Map.of(1, "value")));
        assertThrows(ClassCastException.class, () -> JsonUtils.toStringObjectMapList(List.of("value")));
        assertThrows(ClassCastException.class, () -> JsonUtils.toStringObjectMapList(Map.of()));
        assertThrows(ClassCastException.class, () -> JsonUtils.toList(List.of(1), String.class));
        assertThrows(ClassCastException.class, () -> JsonUtils.toList(Map.of(), String.class));
    }
}
