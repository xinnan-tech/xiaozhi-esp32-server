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
     * websocket地址
     */
    String SERVER_WEBSOCKET = "server.websocket";

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
     * 无记忆
     */
    String MEMORY_NO_MEM = "Memory_nomem";

    enum SysBaseParam {
        /**
         * 系统全称
         */
        SYS_NAME("SYS_NAME"),
        /**
         * 系统简称
         */
        SYS_SHORT_NAME("SYS_SHORT_NAME"),
        /**
         * 系统描述
         */
        SYS_DES("SYS_DES"),
        /**
         * 登录失败几次锁定
         */
        LOGIN_LOCK_COUNT("LOGIN_LOCK_COUNT"),
        /**
         * 账号失败锁定分钟数
         */
        LOGIN_LOCK_TIME("LOGIN_LOCK_TIME"),
        /**
         * TOKEN强验证
         */
        SYS_TOKEN_SECURITY("SYS_TOKEN_SECURITY");

        private String value;

        SysBaseParam(String value) {
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
    public static final String VERSION = "0.4.3";
}