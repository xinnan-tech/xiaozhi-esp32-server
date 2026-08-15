package xiaozhi.common.utils;

import org.springframework.context.support.StaticMessageSource;
import org.springframework.test.util.ReflectionTestUtils;

public final class TestMessageSupport {
    private TestMessageSupport() {
    }

    public static void install() {
        StaticMessageSource messageSource = new StaticMessageSource();
        messageSource.setUseCodeAsDefaultMessage(true);
        ReflectionTestUtils.setField(MessageUtils.class, "messageSource", messageSource);
    }
}
