package xiaozhi.common.utils;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

import cn.hutool.json.JSONObject;

class SensitiveDataUtilsTest {

    @Test
    void isSensitiveField_recognizes_known_field_names() {
        assertTrue(SensitiveDataUtils.isSensitiveField("api_key"));
        assertTrue(SensitiveDataUtils.isSensitiveField("API_KEY"));
        assertTrue(SensitiveDataUtils.isSensitiveField("personal_access_token"));
        assertTrue(SensitiveDataUtils.isSensitiveField("secret"));
        assertTrue(SensitiveDataUtils.isSensitiveField("secret_key"));
    }

    @Test
    void isSensitiveField_rejects_blank_and_unknown_field_names() {
        assertFalse(SensitiveDataUtils.isSensitiveField(""));
        assertFalse(SensitiveDataUtils.isSensitiveField("   "));
        assertFalse(SensitiveDataUtils.isSensitiveField(null));
        assertFalse(SensitiveDataUtils.isSensitiveField("not_a_secret"));
    }

    @Test
    void maskMiddle_returns_input_unchanged_for_short_or_blank_values() {
        assertNull(SensitiveDataUtils.maskMiddle(null));
        assertEquals("", SensitiveDataUtils.maskMiddle(""));
        assertEquals("a", SensitiveDataUtils.maskMiddle("a"));
    }

    @Test
    void maskMiddle_keeps_two_at_each_end_for_short_strings() {
        assertEquals("ab****yz", SensitiveDataUtils.maskMiddle("abcdefyz"));
    }

    @Test
    void maskMiddle_keeps_four_at_each_end_for_long_strings() {
        String masked = SensitiveDataUtils.maskMiddle("verylongapikeyvalue123");
        assertTrue(masked.startsWith("very"));
        assertTrue(masked.endsWith("3123"));
        assertTrue(masked.contains("****"));
        assertEquals("verylongapikeyvalue123".length(), masked.length());
    }

    @Test
    void isMaskedValue_detects_masked_values() {
        assertTrue(SensitiveDataUtils.isMaskedValue("ab****yz"));
        assertTrue(SensitiveDataUtils.isMaskedValue("abc****def****ghi"));
        assertFalse(SensitiveDataUtils.isMaskedValue("plainstring"));
    }

    @Test
    void isMaskedValue_rejects_blank_values() {
        assertFalse(SensitiveDataUtils.isMaskedValue(null));
        assertFalse(SensitiveDataUtils.isMaskedValue(""));
        assertFalse(SensitiveDataUtils.isMaskedValue("   "));
    }

    @Test
    void maskSensitiveFields_masks_known_sensitive_keys_only() {
        JSONObject source = new JSONObject();
        source.set("api_key", "sk-supersecretapikey");
        source.set("name", "alice");

        JSONObject masked = SensitiveDataUtils.maskSensitiveFields(source);

        String apiKey = (String) masked.get("api_key");
        assertTrue(apiKey.contains("****"));
        assertEquals("alice", masked.get("name"));
    }

    @Test
    void maskSensitiveFields_returns_null_when_input_is_null() {
        assertNull(SensitiveDataUtils.maskSensitiveFields(null));
    }
}
