package xiaozhi.common.constant;

import lombok.Getter;

/**
 * Constant
 * Copyright (c) RenRen Open Source All rights reserved.
 * Website: https://www.renren.io
 */
public interface Constant {
    /**
     * Success
     */
    int SUCCESS = 1;
    /**
     * Failed
     */
    int FAIL = 0;
    /**
     * OK
     */
    String OK = "OK";
    /**
     * User ID
     */
    String USER_KEY = "userId";
    /**
     * Menu root node identifier
     */
    Long MENU_ROOT = 0L;
    /**
     * Department root node ID
     */
    Long DEPT_ROOT = 0L;
    /**
     * Root node identifier for data dictionary
     */
    Long DICT_ROOT = 0L;
    /**
     * Ascending
     */
    String ASC = "asc";
    /**
     * Descending
     */
    String DESC = "desc";
    /**
     * Creation time field name
     */
    String CREATE_DATE = "create_date";

    /**
     * Creation time field name
     */
    String ID = "id";

    /**
     * Filter by data permissions
     */
    String SQL_FILTER = "sqlFilter";

    /**
     * Current page
     */
    String PAGE = "page";
    /**
     * Records per page
     */
    String LIMIT = "limit";
    /**
     * Sort field
     */
    String ORDER_FIELD = "orderField";
    /**
     * Sort order
     */
    String ORDER = "order";

    /**
     * Request header authorization token
     */
    String AUTHORIZATION = "Authorization";

    /**
     * Server key
     */
    String SERVER_SECRET = "server.secret";

    /**
     * SM2 Public Key
     */
    String SM2_PUBLIC_KEY = "server.public_key";

    /**
     * SM2 Private Key
     */
    String SM2_PRIVATE_KEY = "server.private_key";

    /**
     * WebSocket address
     */
    String SERVER_WEBSOCKET = "server.websocket";

    /**
     * MQTT gateway config
     */
    String SERVER_MQTT_GATEWAY = "server.mqtt_gateway";

    /**
     * OTA URL
     */
    String SERVER_OTA = "server.ota";

    /**
     * Allow user registration
     */
    String SERVER_ALLOW_USER_REGISTER = "server.allow_user_register";

    /**
     * Control panel address displayed when sending a 6-digit verification code
     */
    String SERVER_FRONTED_URL = "server.fronted_url";

    /**
     * Path separator
     */
    String FILE_EXTENSION_SEG = ".";

    /**
     * MCP endpoint path
     */
    String SERVER_MCP_ENDPOINT = "server.mcp_endpoint";

    /**
     * MCP endpoint path
     */
    String SERVER_VOICE_PRINT = "server.voice_print";

    /**
     * MQTT key
     */
    String SERVER_MQTT_SECRET = "server.mqtt_signature_key";

    /**
     * WebSocket authentication toggle
     */
    String SERVER_AUTH_ENABLED = "server.auth.enabled";

    /**
     * System function menu config
     */
    String SYSTEM_WEB_MENU = "system-web.menu";

    /**
     * No memory
     */
    String MEMORY_NO_MEM = "Memory_nomem";

    /**
     * Report chat history only (no memory summarization)
     */
    String MEMORY_MEM_REPORT_ONLY = "Memory_mem_report_only";

    /**
     * Mem0AI memory
     */
    String MEMORY_MEM0AI = "Memory_mem0ai";

    /**
     * PowerMem Memory
     */
    String MEMORY_POWERMEM = "Memory_powermem";

    /**
     * Volcano Engine dual-channel voice cloning
     */
    String VOICE_CLONE_HUOSHAN_DOUBLE_STREAM = "huoshan_double_stream";

    /**
     * RAG config type
     */
    String RAG_CONFIG_TYPE = "RAG";

    enum SysBaseParam {
        /**
         * ICP license number
         */
        BEIAN_ICP_NUM("server.beian_icp_num"),
        /**
         * GA Filing Number
         */
        BEIAN_GA_NUM("server.beian_ga_num"),
        /**
         * System name
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
     * Training status
     */
    enum TrainStatus {
        /**
         * Not trained
         */
        NOT_TRAINED(0),
        /**
         * Training
         */
        TRAINING(1),
        /**
         * Trained
         */
        TRAINED(2),
        /**
         * Training failed
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
     * System SMS parameters
     */
    enum SysMSMParam {
        /**
         * Twilio account SID
         */
        TWILIO_SMS_ACCOUNT_SID("twilio.sms.account_sid"),
        /**
         * Twilio auth token
         */
        TWILIO_SMS_AUTH_TOKEN("twilio.sms.auth_token"),
        /**
         * Twilio phone number (from)
         */
        TWILIO_SMS_PHONE_NUMBER("twilio.sms.phone_number"),
        /**
         * Twilio SMS template message
         */
        TWILIO_SMS_TEMPLATE_MESSAGE("twilio.sms.template_message"),
        /**
         * Max SMS per phone number per day
         */
        SERVER_SMS_MAX_SEND_COUNT("server.sms_max_send_count"),
        /**
         * Enable mobile registration
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
     * Data status
     */
    enum DataOperation {
        /**
         * Insert
         */
        INSERT("I"),
        /**
         * Modified
         */
        UPDATE("U"),
        /**
         * Deleted
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
        IGNORE(0, "Do Not Log"),
        RECORD_TEXT(1, "Record text"),
        RECORD_TEXT_AUDIO(2, "Log text and audio");

        private final int code;
        private final String name;

        ChatHistoryConfEnum(int code, String name) {
            this.code = code;
            this.name = name;
        }
    }

    /**
     * Version
     */
    public static final String VERSION = "0.9.7";

    /**
     * Invalid firmware URL
     */
    String INVALID_FIRMWARE_URL = "http://xiaozhi.server.com:8002/xiaozhi/otaMag/download/NOT_ACTIVATED_FIRMWARE_THIS_IS_A_INVALID_URL";

    /**
     * Dictionary type
     */
    enum DictType {
        /**
         * Country code
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