package xiaozhi.modules.sys.enums;

import org.apache.commons.lang3.StringUtils;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

/**
 * 服务端调用响应枚举
 */
public enum ServerActionResponseEnum {
    SUCCESS("success"), FAIL("fail");

    private final String value;

    ServerActionResponseEnum(String value) {
        this.value = value;
    }

    @JsonValue
    public String getValue() {
        return value;
    }

    @JsonCreator
    public static ServerActionResponseEnum fromValue(String value) {
        ServerActionResponseEnum byValue = getByValue(value);
        if (byValue == null) {
            throw new IllegalArgumentException("Unknown enum value: " + value);
        }
        return byValue;
    }

    public static ServerActionResponseEnum getByValue(String value) {
        if (StringUtils.isBlank(value)) {
            return null;
        }
        for (ServerActionResponseEnum action : ServerActionResponseEnum.values()) {
            if (action.value.equals(value)) {
                return action;
            }
        }
        return null;
    }
}
