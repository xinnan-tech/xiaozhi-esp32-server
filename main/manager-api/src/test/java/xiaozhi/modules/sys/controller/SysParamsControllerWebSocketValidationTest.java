package xiaozhi.modules.sys.controller;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.mock;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.context.ApplicationContext;
import org.springframework.context.support.GenericApplicationContext;
import org.springframework.context.support.ResourceBundleMessageSource;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.RestTemplate;

import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.utils.MessageUtils;
import xiaozhi.common.utils.SpringContextUtils;
import xiaozhi.modules.config.service.ConfigService;
import xiaozhi.modules.sys.service.SysParamsService;

/**
 * WebSocket 地址校验（#2228）。
 *
 * <p>
 * 关键点：连不上的地址只能当告警，不能拦着不让保存。
 * 连接测试是从 manager-api 自己的网络发起的，视角和设备不一样：
 * 服务器连不上不代表设备连不上（公网地址、NAT 回环），服务器连得上也不代表设备连得上（docker 内网地址）。
 */
class SysParamsControllerWebSocketValidationTest {

    /** RFC 5737 保留的文档用地址，保证不可达 */
    private static final String UNREACHABLE_URL = "ws://192.0.2.1:8000/xiaozhi/v1/";

    private SysParamsController controller;
    private ApplicationContextHolder holder;

    @BeforeEach
    void setUp() {
        // RenException 构造时会去 Spring 上下文里取 messageSource，
        // 单测里没有上下文，所以自己塞一个，用完还原
        holder = new ApplicationContextHolder();

        controller = new SysParamsController(mock(SysParamsService.class), mock(ConfigService.class),
                mock(RestTemplate.class));
    }

    @AfterEach
    void tearDown() {
        holder.restore();
    }

    @Test
    void localhostIsRejected() {
        RenException e = assertThrows(RenException.class,
                () -> controller.validateWebSocketUrls(Constant.SERVER_WEBSOCKET, "ws://localhost:8000/xiaozhi/v1/"));
        assertEquals(ErrorCode.WEBSOCKET_URL_LOCALHOST, e.getCode());
    }

    @Test
    void loopbackAddressIsRejected() {
        RenException e = assertThrows(RenException.class,
                () -> controller.validateWebSocketUrls(Constant.SERVER_WEBSOCKET, "ws://127.0.0.1:8000/xiaozhi/v1/"));
        assertEquals(ErrorCode.WEBSOCKET_URL_LOCALHOST, e.getCode());
    }

    @Test
    void malformedUrlIsRejected() {
        RenException e = assertThrows(RenException.class,
                () -> controller.validateWebSocketUrls(Constant.SERVER_WEBSOCKET, "http://192.0.2.1/xiaozhi/v1/"));
        assertEquals(ErrorCode.WEBSOCKET_URL_FORMAT_ERROR, e.getCode());
    }

    @Test
    void unreachableAddressIsOnlyWarnedAbout() {
        // 以前这里会抛 WEBSOCKET_CONNECTION_FAILED，设备能访问的公网地址一个都填不进去（#2228）
        assertDoesNotThrow(() -> controller.validateWebSocketUrls(Constant.SERVER_WEBSOCKET, UNREACHABLE_URL));
    }

    @Test
    void unreachableAddressInListIsOnlyWarnedAbout() {
        String urls = "ws://192.0.2.1:8000/xiaozhi/v1/;ws://192.0.2.2:8000/xiaozhi/v1/";
        assertDoesNotThrow(() -> controller.validateWebSocketUrls(Constant.SERVER_WEBSOCKET, urls));
    }

    @Test
    void otherParamCodesAreNotValidated() {
        assertDoesNotThrow(() -> controller.validateWebSocketUrls("server.ota", UNREACHABLE_URL));
        assertDoesNotThrow(() -> controller.validateWebSocketUrls("server.ota", "not a url at all"));
    }

    /**
     * 借用一个最小上下文，让 RenException 能取到 i18n 文案；测完把原来的还原回去。
     */
    private static final class ApplicationContextHolder {
        private final ApplicationContext previous;
        private final GenericApplicationContext context = new GenericApplicationContext();

        ApplicationContextHolder() {
            this.previous = SpringContextUtils.applicationContext;

            ResourceBundleMessageSource source = new ResourceBundleMessageSource();
            source.setBasename("i18n/messages");
            source.setDefaultEncoding("UTF-8");
            context.registerBean("messageSource", ResourceBundleMessageSource.class, () -> source);
            context.refresh();

            SpringContextUtils.applicationContext = context;
            // MessageUtils 会把 messageSource 缓存下来，测完要清掉，别污染别的测试
            ReflectionTestUtils.setField(MessageUtils.class, "messageSource", null);
        }

        void restore() {
            SpringContextUtils.applicationContext = previous;
            ReflectionTestUtils.setField(MessageUtils.class, "messageSource", null);
            context.close();
        }
    }
}
