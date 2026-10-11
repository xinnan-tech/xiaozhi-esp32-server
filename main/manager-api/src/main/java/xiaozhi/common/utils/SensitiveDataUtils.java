package xiaozhi.common.utils;

import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import org.apache.commons.lang3.StringUtils;

import cn.hutool.json.JSONObject;

/**
 * Utility helpers for sensitive data handling.
 */
public class SensitiveDataUtils {

    // List of sensitive fields.
    private static final Set<String> SENSITIVE_FIELDS = new HashSet<>(Arrays.asList(
            "api_key", "personal_access_token", "access_token", "token",
            "secret", "access_key_secret", "secret_key"));

    /**
     * Check whether the field is sensitive.
     */
    public static boolean isSensitiveField(String fieldName) {
        return StringUtils.isNotBlank(fieldName) && SENSITIVE_FIELDS.contains(fieldName.toLowerCase());
    }

    /**
     * Mask the middle section of a string.
     */
    public static String maskMiddle(String value) {
        if (StringUtils.isBlank(value) || value.length() == 1) {
            return value;
        }

        int length = value.length();
        if (length <= 8) {
            // Short strings keep the first two and last two characters.
            return value.substring(0, 2) + "****" + value.substring(length - 2);
        } else {
            // Long strings keep the first four and last four characters.
            int maskLength = length - 8;
            StringBuilder maskBuilder = new StringBuilder();
            for (int i = 0; i < maskLength; i++) {
                maskBuilder.append('*');
            }
            return value.substring(0, 4) + maskBuilder.toString() + value.substring(length - 4);
        }
    }

    /**
     * Check whether the string is already masked.
     */
    public static boolean isMaskedValue(String value) {
        if (StringUtils.isBlank(value)) {
            return false;
        }
        // A masked value should include at least four consecutive asterisks.
        return value.contains("****");
    }

    /**
     * Mask sensitive fields in a JSONObject.
     */
    public static JSONObject maskSensitiveFields(JSONObject jsonObject) {
        if (jsonObject == null) {
            return null;
        }

        JSONObject result = new JSONObject();

        for (String key : jsonObject.keySet()) {
            Object value = jsonObject.get(key);

            if (SENSITIVE_FIELDS.contains(key.toLowerCase()) && value instanceof String) {
                result.set(key, maskMiddle((String) value));
            } else if (value instanceof JSONObject) {
                result.set(key, maskSensitiveFields((JSONObject) value));
            } else {
                result.set(key, value);
            }
        }

        return result;
    }

    /**
     * Compare the sensitive fields of two JSONObjects.
     * This is primarily used for fields such as api_key.
     */
    public static boolean isSensitiveDataEqual(JSONObject original, JSONObject updated) {
        if (original == null && updated == null) {
            return true;
        }
        if (original == null || updated == null) {
            return false;
        }

        // Extract and compare the supported sensitive fields.
        return compareSpecificSensitiveFields(original, updated, "api_key") &&
                compareSpecificSensitiveFields(original, updated, "personal_access_token") &&
                compareSpecificSensitiveFields(original, updated, "access_token") &&
                compareSpecificSensitiveFields(original, updated, "token") &&
                compareSpecificSensitiveFields(original, updated, "secret") &&
                compareSpecificSensitiveFields(original, updated, "access_key_secret") &&
                compareSpecificSensitiveFields(original, updated, "secret_key");
    }

    /**
     * Compare a specific sensitive field across two JSON objects.
     * Traverse the full JSON tree to find and compare the requested field.
     */
    private static boolean compareSpecificSensitiveFields(JSONObject original, JSONObject updated, String fieldName) {
        // Extract the target sensitive field from the original object.
        Map<String, String> originalFields = new HashMap<>();
        extractSpecificSensitiveField(original, originalFields, fieldName, "");

        // Extract the target sensitive field from the updated object.
        Map<String, String> updatedFields = new HashMap<>();
        extractSpecificSensitiveField(updated, updatedFields, fieldName, "");

        // Different field counts mean entries were added or removed.
        if (originalFields.size() != updatedFields.size()) {
            return false;
        }

        // Compare every field value.
        for (Map.Entry<String, String> entry : originalFields.entrySet()) {
            String key = entry.getKey();
            String originalValue = entry.getValue();
            String updatedValue = updatedFields.get(key);

            if (updatedValue == null || !updatedValue.equals(originalValue)) {
                return false;
            }
        }

        return true;
    }

    /**
     * Recursively extract sensitive fields with the requested name.
     */
    private static void extractSpecificSensitiveField(JSONObject jsonObject, Map<String, String> fieldsMap,
            String targetFieldName, String parentPath) {
        if (jsonObject == null) {
            return;
        }

        for (String key : jsonObject.keySet()) {
            String fullPath = parentPath.isEmpty() ? key : parentPath + "." + key;
            Object value = jsonObject.get(key);

            if (value instanceof JSONObject) {
                // Recurse into nested JSON objects.
                extractSpecificSensitiveField((JSONObject) value, fieldsMap, targetFieldName, fullPath);
            } else if (value instanceof String && key.equalsIgnoreCase(targetFieldName)) {
                // Found the target sensitive field. Save its path and value.
                fieldsMap.put(fullPath, (String) value);
            }
        }
    }
}
