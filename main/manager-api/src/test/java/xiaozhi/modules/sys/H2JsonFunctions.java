package xiaozhi.modules.sys;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/**
 * MySQL-compatible JSON functions for the H2 in-memory changelog replay.
 * Supports object and array navigation: {@code $.a.b}, {@code $[0].label},
 * {@code $.a[2].default}, and unwraps double-encoded JSON string payloads.
 */
public final class H2JsonFunctions {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    private H2JsonFunctions() {
    }

    // ------------------------------------------------------------------ set

    public static String jsonSet(String json, String path1, String value1) throws IOException {
        JsonNode root = setPath(json, path1, value1);
        return OBJECT_MAPPER.writeValueAsString(root);
    }

    public static String jsonSet(String json, String path1, String value1, String path2, String value2) throws IOException {
        JsonNode root = setPath(json, path1, value1);
        root = setPath(root, path2, value2);
        return OBJECT_MAPPER.writeValueAsString(root);
    }

    public static String jsonSet(
        String json,
        String path1,
        String value1,
        String path2,
        String value2,
        String path3,
        String value3
    ) throws IOException {
        JsonNode root = setPath(json, path1, value1);
        root = setPath(root, path2, value2);
        root = setPath(root, path3, value3);
        return OBJECT_MAPPER.writeValueAsString(root);
    }

    public static String jsonSet(
        String json,
        String path1,
        String value1,
        String path2,
        String value2,
        String path3,
        String value3,
        String path4,
        String value4
    ) throws IOException {
        JsonNode root = setPath(json, path1, value1);
        root = setPath(root, path2, value2);
        root = setPath(root, path3, value3);
        root = setPath(root, path4, value4);
        return OBJECT_MAPPER.writeValueAsString(root);
    }

    // --------------------------------------------------------------- remove

    public static String jsonRemove(String json, String path) throws IOException {
        if (json == null || json.isBlank()) {
            return json;
        }
        JsonNode root = parseRoot(json);
        removePath(root, path);
        return OBJECT_MAPPER.writeValueAsString(root);
    }

    public static String jsonRemove(String json, String path1, String path2) throws IOException {
        return jsonRemove(jsonRemove(json, path1), path2);
    }

    public static String jsonRemove(String json, String path1, String path2, String path3) throws IOException {
        return jsonRemove(jsonRemove(json, path1, path2), path3);
    }

    public static String jsonRemove(
        String json, String path1, String path2, String path3, String path4
    ) throws IOException {
        return jsonRemove(jsonRemove(json, path1, path2, path3), path4);
    }

    public static String jsonRemove(
        String json, String path1, String path2, String path3, String path4, String path5
    ) throws IOException {
        return jsonRemove(jsonRemove(json, path1, path2, path3, path4), path5);
    }

    // -------------------------------------------------------------- extract

    public static String jsonExtract(String json, String path) throws IOException {
        if (json == null || json.isBlank()) {
            return null;
        }
        JsonNode current = parseRoot(json);
        for (String token : tokenizePath(path)) {
            if (current == null) {
                return null;
            }
            current = step(current, token);
        }
        if (current == null || current.isNull()) {
            return null;
        }
        if (current.isTextual()) {
            return current.textValue();
        }
        if (current.isNumber() || current.isBoolean()) {
            return current.asText();
        }
        return OBJECT_MAPPER.writeValueAsString(current);
    }

    public static String jsonUnquote(String value) {
        if (value == null) {
            return null;
        }
        if (value.length() >= 2 && value.startsWith("\"") && value.endsWith("\"")) {
            return value.substring(1, value.length() - 1);
        }
        return value;
    }

    public static String filterProviderFields(String json, String keyToRemove) throws IOException {
        if (json == null || json.isBlank()) {
            return json;
        }
        JsonNode node = parseRoot(json);
        if (!(node instanceof ArrayNode arrayNode)) {
            return json;
        }

        ArrayNode filtered = OBJECT_MAPPER.createArrayNode();
        for (JsonNode item : arrayNode) {
            if (!item.isObject()) {
                filtered.add(item);
                continue;
            }
            String key = item.path("key").asText();
            if (!keyToRemove.equals(key)) {
                filtered.add(item);
            }
        }
        return OBJECT_MAPPER.writeValueAsString(filtered);
    }

    // ------------------------------------------------------------- plumbing

    private static JsonNode setPath(Object jsonValue, String path, String value) throws IOException {
        JsonNode root;
        if (jsonValue instanceof JsonNode node) {
            root = node;
        } else {
            String json = jsonValue == null ? null : jsonValue.toString();
            root = (json == null || json.isBlank())
                ? OBJECT_MAPPER.createObjectNode()
                : parseRoot(json);
        }
        List<String> tokens = tokenizePath(path);
        if (tokens.isEmpty()) {
            return root;
        }
        if (!(root instanceof ObjectNode) && !(root instanceof ArrayNode)) {
            root = OBJECT_MAPPER.createObjectNode();
        }
        JsonNode current = root;
        for (int i = 0; i < tokens.size() - 1; i++) {
            String token = tokens.get(i);
            JsonNode next = step(current, token);
            if (next == null || next.isNull()) {
                JsonNode created = isIndexToken(tokens.get(i + 1))
                    ? OBJECT_MAPPER.createArrayNode()
                    : OBJECT_MAPPER.createObjectNode();
                attach(current, token, created);
                next = created;
            }
            current = next;
        }
        attach(current, tokens.get(tokens.size() - 1), coerceJsonValue(value));
        return root;
    }

    private static void removePath(JsonNode root, String path) {
        List<String> tokens = tokenizePath(path);
        if (tokens.isEmpty()) {
            return;
        }
        JsonNode current = root;
        for (int i = 0; i < tokens.size() - 1; i++) {
            current = step(current, tokens.get(i));
            if (current == null) {
                return;
            }
        }
        String last = tokens.get(tokens.size() - 1);
        if (current instanceof ObjectNode objectNode) {
            objectNode.remove(last);
        } else if (current instanceof ArrayNode arrayNode && isIndexToken(last)) {
            int index = Integer.parseInt(last);
            if (index >= 0 && index < arrayNode.size()) {
                arrayNode.remove(index);
            }
        }
    }

    /** Parse a JSON document, unwrapping double-encoded string payloads. */
    private static JsonNode parseRoot(String json) throws IOException {
        JsonNode node = OBJECT_MAPPER.readTree(json);
        // A VARCHAR column may hold a quoted JSON string ("[{...}]"); unwrap once.
        if (node.isTextual()) {
            String inner = node.textValue().trim();
            if (inner.startsWith("{") || inner.startsWith("[")) {
                try {
                    return OBJECT_MAPPER.readTree(inner);
                } catch (Exception ignored) {
                    return node;
                }
            }
        }
        return node;
    }

    private static JsonNode step(JsonNode current, String token) {
        if (current == null || current.isNull() || token == null) {
            return null;
        }
        if (current instanceof ArrayNode arrayNode) {
            if (isIndexToken(token)) {
                int index = Integer.parseInt(token);
                return index >= 0 && index < arrayNode.size() ? arrayNode.get(index) : null;
            }
            return null;
        }
        if (current.isTextual()) {
            // transparently descend into a double-encoded JSON string member
            try {
                JsonNode inner = parseRoot(current.textValue());
                if (inner != current) {
                    return step(inner, token);
                }
            } catch (Exception ignored) {
                return null;
            }
            return null;
        }
        return current.get(token);
    }

    private static void attach(JsonNode container, String token, JsonNode value) {
        if (container instanceof ObjectNode objectNode) {
            objectNode.set(token, value);
        } else if (container instanceof ArrayNode arrayNode && isIndexToken(token)) {
            int index = Integer.parseInt(token);
            while (arrayNode.size() <= index) {
                arrayNode.addNull();
            }
            if (index >= 0) {
                arrayNode.set(index, value);
            }
        }
    }

    private static boolean isIndexToken(String token) {
        return token != null && !token.isEmpty() && token.chars().allMatch(Character::isDigit);
    }

    /** Split {@code $.a[0].b} into [a, 0, b]; {@code $[3].default} into [3, default]. */
    private static List<String> tokenizePath(String path) {
        List<String> tokens = new ArrayList<>();
        if (path == null || path.isEmpty()) {
            return tokens;
        }
        String p = path;
        if (p.startsWith("$")) {
            p = p.substring(1);
        }
        StringBuilder current = new StringBuilder();
        for (int i = 0; i < p.length(); i++) {
            char c = p.charAt(i);
            if (c == '.') {
                if (current.length() > 0) {
                    tokens.add(current.toString());
                    current.setLength(0);
                }
            } else if (c == '[') {
                if (current.length() > 0) {
                    tokens.add(current.toString());
                    current.setLength(0);
                }
                int end = p.indexOf(']', i);
                if (end < 0) {
                    end = p.length();
                }
                String inside = p.substring(i + 1, end).replace("\"", "").trim();
                if (!inside.isEmpty()) {
                    tokens.add(inside);
                }
                i = end;
            } else {
                current.append(c);
            }
        }
        if (current.length() > 0) {
            tokens.add(current.toString());
        }
        return tokens;
    }

    private static JsonNode coerceJsonValue(String value) throws IOException {
        if (value == null) {
            return OBJECT_MAPPER.nullNode();
        }
        String trimmed = value.trim();
        if ((trimmed.startsWith("{") && trimmed.endsWith("}")) || (trimmed.startsWith("[") && trimmed.endsWith("]"))) {
            return OBJECT_MAPPER.readTree(trimmed);
        }
        if ("null".equalsIgnoreCase(trimmed)) {
            return OBJECT_MAPPER.nullNode();
        }
        if ("true".equalsIgnoreCase(trimmed) || "false".equalsIgnoreCase(trimmed)) {
            return OBJECT_MAPPER.valueToTree(Boolean.parseBoolean(trimmed));
        }
        if (trimmed.matches("-?\\d+")) {
            try {
                return OBJECT_MAPPER.valueToTree(Integer.parseInt(trimmed));
            } catch (NumberFormatException ignored) {
                return OBJECT_MAPPER.valueToTree(Long.parseLong(trimmed));
            }
        }
        if (trimmed.matches("-?\\d+\\.\\d+")) {
            return OBJECT_MAPPER.valueToTree(Double.parseDouble(trimmed));
        }
        return OBJECT_MAPPER.valueToTree(value);
    }
}
