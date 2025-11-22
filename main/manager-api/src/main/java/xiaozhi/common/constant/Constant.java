package xiaozhi.common.constant;

import lombok.Getter;

/**
 * 常量
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
public interface Constant {
    /**
     * 成功
     */
    int SUCCESS = 1;
    /**
     * 失败
     */
    int FAIL = 0;
    /**
     * OK
     */
    String OK = "OK";
    /**
     * 用户标识
     */
    String USER_KEY = "userId";
    /**
     * 菜单根节点标识
     */
    Long MENU_ROOT = 0L;
    /**
     * 部门根节点标识
     */
    Long DEPT_ROOT = 0L;
    /**
     * 数据字典根节点标识
     */
    Long DICT_ROOT = 0L;
    /**
     * 升序
     */
    String ASC = "asc";
    /**
     * 降序
     */
    String DESC = "desc";
    /**
     * 创建时间字段名
     */
    String CREATE_DATE = "create_date";

    /**
     * 创建时间字段名
     */
    String ID = "id";

    /**
     * 数据权限过滤
     */
    String SQL_FILTER = "sqlFilter";

    /**
     * 当前页码
     */
    String PAGE = "page";
    /**
     * 每页显示记录数
     */
    String LIMIT = "limit";
    /**
     * 排序字段
     */
    String ORDER_FIELD = "orderField";
    /**
     * 排序方式
     */
    String ORDER = "order";

    /**
     * 请求头授权标识
     */
    String AUTHORIZATION = "Authorization";

    /**
     * 服务器密钥
     */
    String SERVER_SECRET = "server.secret";

    /**
     * SM2公钥
     */
    String SM2_PUBLIC_KEY = "server.public_key";

    /**
     * SM2私钥
     */
    String SM2_PRIVATE_KEY = "server.private_key";

    /**
     * websocket地址
     */
    String SERVER_WEBSOCKET = "server.websocket";

    /**
     * mqtt gateway 配置
     */
    String SERVER_MQTT_GATEWAY = "server.mqtt_gateway";

    /**
     * ota地址
     */
    String SERVER_OTA = "server.ota";

    /**
     * 是否允许用户注册
     */
    String SERVER_ALLOW_USER_REGISTER = "server.allow_user_register";

    /**
     * 下发六位验证码时显示的控制面板地址
     */
    String SERVER_FRONTED_URL = "server.fronted_url";

    /**
     * 路径分割符
     */
    String FILE_EXTENSION_SEG = ".";

    /**
     * mcp接入点路径
     */
    String SERVER_MCP_ENDPOINT = "server.mcp_endpoint";

    /**
     * mcp接入点路径
     */
    String SERVER_VOICE_PRINT = "server.voice_print";

    /**
     * mqtt密钥
     */
    String SERVER_MQTT_SECRET = "server.mqtt_signature_key";

    /**
     * 无记忆
     */
    String MEMORY_NO_MEM = "Memory_nomem";

    /**
     * 火山引擎双声道语音克隆
     */
    String VOICE_CLONE_HUOSHAN_DOUBLE_STREAM = "huoshan_double_stream";

    /**
     * RAG配置类型
     */
    String RAG_CONFIG_TYPE = "RAG";

    enum SysBaseParam {
        /**
         * ICP备案号
         */
        BEIAN_ICP_NUM("server.beian_icp_num"),
        /**
         * GA备案号
         */
        BEIAN_GA_NUM("server.beian_ga_num"),
        /**
         * 系统名称
         */
        SERVER_NAME("server.name");

        private String value;

        SysBaseParam(String value) {
            this.value = value;
        }

        public String getValue() {
            return value;
        }
    }

    /**
     * 训练状态
     */
    enum TrainStatus {
        /**
         * 未训练
         */
        NOT_TRAINED(0),
        /**
         * 训练中
         */
        TRAINING(1),
        /**
         * 已训练
         */
        TRAINED(2),
        /**
         * 训练失败
         */
        TRAIN_FAILED(3);

        private final int code;

        TrainStatus(int code) {
            this.code = code;
        }

        public int getCode() {
            return code;
        }
    }

    /**
     * 系统短信
     */
    enum SysMSMParam {
        /**
         * 阿里云授权keyID
         */
        ALIYUN_SMS_ACCESS_KEY_ID("aliyun.sms.access_key_id"),
        /**
         * 阿里云授权密钥
         */
        ALIYUN_SMS_ACCESS_KEY_SECRET("aliyun.sms.access_key_secret"),
        /**
         * 阿里云短信签名
         */
        ALIYUN_SMS_SIGN_NAME("aliyun.sms.sign_name"),
        /**
         * 阿里云短信模板
         */
        ALIYUN_SMS_SMS_CODE_TEMPLATE_CODE("aliyun.sms.sms_code_template_code"),
        /**
         * 单号码最大短信发送条数
         */
        SERVER_SMS_MAX_SEND_COUNT("server.sms_max_send_count"),
        /**
         * 是否开启手机注册
         */
        SERVER_ENABLE_MOBILE_REGISTER("server.enable_mobile_register");

        private String value;

        SysMSMParam(String value) {
            this.value = value;
        }

        public String getValue() {
            return value;
        }
    }

    /**
     * 数据状态
     */
    enum DataOperation {
        /**
         * 插入
         */
        INSERT("I"),
        /**
         * 已修改
         */
        UPDATE("U"),
        /**
         * 已删除
         */
        DELETE("D");

        private String value;

        DataOperation(String value) {
            this.value = value;
        }

        public String getValue() {
            return value;
        }
    }

    @Getter
    enum ChatHistoryConfEnum {
        IGNORE(0, "不记录"),
        RECORD_TEXT(1, "记录文本"),
        RECORD_TEXT_AUDIO(2, "文本音频都记录");

        private final int code;
        private final String name;

        ChatHistoryConfEnum(int code, String name) {
            this.code = code;
            this.name = name;
        }
    }

    /**
     * 版本号
     */
    public static final String VERSION = "0.8.8";

    /**
     * 无效固件URL
     */
    String INVALID_FIRMWARE_URL = "http://xiaozhi.server.com:8002/xiaozhi/otaMag/download/NOT_ACTIVATED_FIRMWARE_THIS_IS_A_INVALID_URL";

    /**
     * 字典类型
     */
    enum DictType {
        /**
         * 手机区号
         */
        MOBILE_AREA("MOBILE_AREA");

        private String value;

        DictType(String value) {
            this.value = value;
        }

        public String getValue() {
            return value;
        }
    }
}