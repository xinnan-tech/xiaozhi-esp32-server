package xiaozhi.common.utils;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import cn.hutool.core.util.ArrayUtil;
import cn.hutool.core.util.StrUtil;

/**
 * JSON 工具类
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
public class JsonUtils {
    private static final ObjectMapper objectMapper = new ObjectMapper();
    private static final TypeReference<Map<String, Object>> STRING_OBJECT_MAP = new TypeReference<>() {
    };
    private static final TypeReference<List<Map<String, Object>>> STRING_OBJECT_MAP_LIST = new TypeReference<>() {
    };

    public static String toJsonString(Object object) {
        try {
            return objectMapper.writeValueAsString(object);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    public static <T> T parseObject(String text, Class<T> clazz) {
        if (StrUtil.isEmpty(text)) {
            return null;
        }
        try {
            return objectMapper.readValue(text, clazz);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    public static <T> T parseObject(byte[] bytes, Class<T> clazz) {
        if (ArrayUtil.isEmpty(bytes)) {
            return null;
        }
        try {
            return objectMapper.readValue(bytes, clazz);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    public static <T> T parseObject(String text, TypeReference<T> typeReference) {
        try {
            return objectMapper.readValue(text, typeReference);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    public static <T> List<T> parseArray(String text, Class<T> clazz) {
        if (StrUtil.isEmpty(text)) {
            return new ArrayList<>();
        }
        try {
            return objectMapper.readValue(text,
                    objectMapper.getTypeFactory().constructCollectionType(List.class, clazz));
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    public static Map<String, Object> parseMap(String text) {
        if (StrUtil.isEmpty(text)) {
            return null;
        }
        return parseObject(text, STRING_OBJECT_MAP);
    }

    public static List<Map<String, Object>> parseMapList(String text) {
        if (StrUtil.isEmpty(text)) {
            return null;
        }
        return parseObject(text, STRING_OBJECT_MAP_LIST);
    }

    public static Map<String, Object> toStringObjectMap(Object value) {
        if (value == null) {
            return null;
        }
        if (!(value instanceof Map<?, ?> map)) {
            throw new ClassCastException("Expected Map but got " + value.getClass().getName());
        }

        Map<String, Object> result = new LinkedHashMap<>(map.size());
        for (Map.Entry<?, ?> entry : map.entrySet()) {
            result.put(String.class.cast(entry.getKey()), entry.getValue());
        }
        return result;
    }

    public static List<Map<String, Object>> toStringObjectMapList(Object value) {
        if (value == null) {
            return null;
        }

        List<?> list = List.class.cast(value);
        List<Map<String, Object>> result = new ArrayList<>(list.size());
        for (Object item : list) {
            result.add(toStringObjectMap(item));
        }
        return result;
    }

    public static <T> List<T> toList(Object value, Class<T> elementType) {
        if (value == null) {
            return null;
        }

        List<?> list = List.class.cast(value);
        List<T> result = new ArrayList<>(list.size());
        for (Object item : list) {
            result.add(elementType.cast(item));
        }
        return result;
    }

}
