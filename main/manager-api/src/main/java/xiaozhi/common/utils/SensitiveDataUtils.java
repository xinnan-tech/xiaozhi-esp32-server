package xiaozhi.common.utils;

import cn.hutool.json.JSONObject;
import org.apache.commons.lang3.StringUtils;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

/**
 * 敏感数据处理工具类
 */
public class SensitiveDataUtils {
    
    // 敏感字段列表
    private static final Set<String> SENSITIVE_FIELDS = new HashSet<>(Arrays.asList(
            "api_key", "personal_access_token", "access_token", "token", 
            "secret", "access_key_secret", "secret_key"
    ));
    
    /**
     * 隐藏字符串中间部分
     * @param value 原始字符串
     * @return 隐藏后的字符串
     */
    public static String maskMiddle(String value) {
        if (StringUtils.isBlank(value)) {
            return value;
        }
        
        int length = value.length();
        if (length <= 8) {
            // 字符串太短，返回前2后2，中间用*代替
            return value.substring(0, 2) + "****" + value.substring(length - 2);
        } else {
            // 返回前4后4，中间用*代替
            int maskLength = length - 8;
            StringBuilder maskBuilder = new StringBuilder();
            for (int i = 0; i < maskLength; i++) {
                maskBuilder.append('*');
            }
            return value.substring(0, 4) + maskBuilder.toString() + value.substring(length - 4);
        }
    }
    
    /**
     * 处理JSONObject中的敏感字段
     * @param jsonObject 原始JSONObject
     * @return 处理后的JSONObject副本
     */
    public static JSONObject maskSensitiveFields(JSONObject jsonObject) {
        if (jsonObject == null) {
            return null;
        }
        
        // 创建副本避免修改原始数据
        JSONObject result = new JSONObject();
        
        for (String key : jsonObject.keySet()) {
            Object value = jsonObject.get(key);
            
            if (SENSITIVE_FIELDS.contains(key.toLowerCase()) && value instanceof String) {
                // 处理敏感字段
                result.put(key, maskMiddle((String) value));
            } else if (value instanceof JSONObject) {
                // 递归处理嵌套的JSONObject
                result.put(key, maskSensitiveFields((JSONObject) value));
            } else {
                // 非敏感字段保持不变
                result.put(key, value);
            }
        }
        
        return result;
    }
    
    /**
     * 比较两个JSONObject的敏感字段处理后是否相同
     * @param original 原始JSONObject
     * @param updated 更新后的JSONObject
     * @return 是否相同
     */
    public static boolean isSensitiveDataEqual(JSONObject original, JSONObject updated) {
        if (original == null && updated == null) {
            return true;
        }
        if (original == null || updated == null) {
            return false;
        }
        
        JSONObject maskedOriginal = maskSensitiveFields(original);
        JSONObject maskedUpdated = maskSensitiveFields(updated);
        
        return maskedOriginal.toString().equals(maskedUpdated.toString());
    }
}