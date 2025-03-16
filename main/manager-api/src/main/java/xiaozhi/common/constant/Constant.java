package xiaozhi.common.constant;

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
     * token header
     */
    String TOKEN_HEADER = "token";

    String AUTHORIZATION = "Authorization";

    /**
     * 路径分割符
     */
    String FILE_EXTENSION_SEG = ".";

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
}