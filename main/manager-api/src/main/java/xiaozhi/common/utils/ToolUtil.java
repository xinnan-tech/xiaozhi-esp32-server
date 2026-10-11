package xiaozhi.common.utils;

import java.util.Collection;
import java.util.Map;

/** Lightweight collection and value emptiness helpers retained for legacy callers. */
public final class ToolUtil {
    private ToolUtil() {}

    public static boolean isNotEmpty(Object value) {
        return !isEmpty(value);
    }

    public static boolean isEmpty(Object value) {
        if (value == null) return true;
        if (value instanceof CharSequence) return value.toString().trim().isEmpty();
        if (value instanceof Collection<?>) return ((Collection<?>) value).isEmpty();
        if (value instanceof Map<?, ?>) return ((Map<?, ?>) value).isEmpty();
        if (value instanceof Object[]) return ((Object[]) value).length == 0;
        if (value instanceof int[]) return ((int[]) value).length == 0;
        if (value instanceof long[]) return ((long[]) value).length == 0;
        return false;
    }
}
