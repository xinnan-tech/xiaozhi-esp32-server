package xiaozhi.common.utils;

import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.temporal.ChronoUnit;
import java.util.Date;

/**
 * 日期处理
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
public class DateUtils {
    /**
     * 时间格式(yyyy-MM-dd)
     */
    public final static String DATE_PATTERN = "yyyy-MM-dd";
    /**
     * 时间格式(yyyy-MM-dd HH:mm:ss)
     */
    public final static String DATE_TIME_PATTERN = "yyyy-MM-dd HH:mm:ss";

    /**
     * 日期格式化 日期格式为：yyyy-MM-dd
     *
     * @param date 日期
     * @return 返回yyyy-MM-dd格式日期
     */
    public static String format(Date date) {
        return format(date, DATE_PATTERN);
    }

    /**
     * 日期格式化 日期格式为：yyyy-MM-dd
     *
     * @param date    日期
     * @param pattern 格式，如：DateUtils.DATE_TIME_PATTERN
     * @return 返回yyyy-MM-dd格式日期
     */
    public static String format(Date date, String pattern) {
        if (date != null) {
            SimpleDateFormat df = new SimpleDateFormat(pattern);
            return df.format(date);
        }
        return null;
    }

    /**
     * 日期解析
     *
     * @param date    日期
     * @param pattern 格式，如：DateUtils.DATE_TIME_PATTERN
     * @return 返回Date
     */
    public static Date parse(String date, String pattern) {
        try {
            return new SimpleDateFormat(pattern).parse(date);
        } catch (ParseException e) {
            e.printStackTrace();
        }
        return null;
    }

    /**
     * 获取简短的时间字符串：10秒前返回刚刚，多少秒前，几小时前，超过一周返回年月日时分秒
     * @param date
     * @return
     */
    public static String getShortTime(Date date) {
        if (date == null) {
            return null;
        }
        // 将 Date 转换为 Instant
        LocalDateTime localDateTime = date.toInstant()
                // 获取系统默认时区
                .atZone(ZoneId.systemDefault())
                // 转换为 LocalDateTime
                .toLocalDateTime();
        // 当前时间
        LocalDateTime now = LocalDateTime.now();
        // 时间差，单位为秒
        long secondsBetween = ChronoUnit.SECONDS.between(localDateTime, now);

        if (secondsBetween <= 10) {
            return "刚刚";
        } else if (secondsBetween < 60) {
            return secondsBetween + "秒前";
        } else if (secondsBetween < 60 * 60) {
            return secondsBetween / 60 + "分钟前";
        } else if (secondsBetween < 86400) {
            return secondsBetween / 3600 + "小时前";
        } else if (secondsBetween < 604800) {
            return secondsBetween / 86400 + "天前";
        } else {
            // 超过一周，显示完整日期时间
            return format(date,DATE_TIME_PATTERN);
        }
    }
}
