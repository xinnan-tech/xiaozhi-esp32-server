package xiaozhi.common.utils;

import org.springframework.context.MessageSource;
import org.springframework.context.i18n.LocaleContextHolder;

/**
 * Internationalization
 * Copyright (c) Renren Open Source All rights reserved.
 * Website: https://www.renren.io
 */
public class MessageUtils {
    private static MessageSource messageSource;

    public static String getMessage(int code) {
        return getMessage(code, new String[0]);
    }

    public static String getMessage(int code, String... params) {
        if (messageSource == null) {
            // Lazy initialization, ensuring Spring context is fully initialized
            messageSource = (MessageSource) SpringContextUtils.getBean("messageSource");
        }
        return messageSource.getMessage(code + "", params, LocaleContextHolder.getLocale());
    }
}
