package xiaozhi.modules.device.utils;

import java.util.regex.Pattern;

import org.apache.commons.lang3.StringUtils;

/**
 * 网络工具类
 */
public class NetworkUtil {
    /**
     * MAC地址正则表达式
     */
    private static final Pattern macPattern = Pattern.compile("^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$");

    /**
     * 判断MAC地址是否合法
     */
    public static boolean isMacAddressValid(String mac) {
        if (StringUtils.isBlank(mac)) {
            return false;
        }
        // 正则校验格式
        if (!macPattern.matcher(mac).matches()) {
            return false;
        }
        // 校验MAC地址是否为单播地址
        String normalized = mac.toLowerCase();
        String[] parts = normalized.split("[:-]");
        int firstByte = Integer.parseInt(parts[0], 16);
        return (firstByte & 1) == 0; // 最低位为0表示单播地址，合法
    }

}
