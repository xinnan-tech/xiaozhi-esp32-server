package xiaozhi.common.exception;

/**
 * 错误编码，由5位数字组成，前2位为模块编码，后3位为业务编码
 * <p>
 * 如：10001（10代表系统模块，001代表业务代码）
 * </p>
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
public interface ErrorCode {
    int INTERNAL_SERVER_ERROR = 500;
    int UNAUTHORIZED = 401;
    int FORBIDDEN = 403;

    int NOT_NULL = 10001;
    int DB_RECORD_EXISTS = 10002;
    int PARAMS_GET_ERROR = 10003;
    int ACCOUNT_PASSWORD_ERROR = 10004;
    int ACCOUNT_DISABLE = 10005;
    int IDENTIFIER_NOT_NULL = 10006;
    int CAPTCHA_ERROR = 10007;
    int SUB_MENU_EXIST = 10008;
    int PASSWORD_ERROR = 10009;

    int SUPERIOR_DEPT_ERROR = 10011;
    int SUPERIOR_MENU_ERROR = 10012;
    int DATA_SCOPE_PARAMS_ERROR = 10013;
    int DEPT_SUB_DELETE_ERROR = 10014;
    int DEPT_USER_DELETE_ERROR = 10015;

    int UPLOAD_FILE_EMPTY = 10019;
    int TOKEN_NOT_EMPTY = 10020;
    int TOKEN_INVALID = 10021;
    int ACCOUNT_LOCK = 10022;

    int OSS_UPLOAD_FILE_ERROR = 10024;

    int REDIS_ERROR = 10027;
    int JOB_ERROR = 10028;
    int INVALID_SYMBOL = 10029;
    int PASSWORD_LENGTH_ERROR = 10030;
    int PASSWORD_WEAK_ERROR = 10031;
    int DEL_MYSELF_ERROR = 10032;
    int DEVICE_CAPTCHA_ERROR = 10033;

    // 参数校验相关错误码
    int PARAM_VALUE_NULL = 10034;
    int PARAM_TYPE_NULL = 10035;
    int PARAM_TYPE_INVALID = 10036;
    int PARAM_NUMBER_INVALID = 10037;
    int PARAM_BOOLEAN_INVALID = 10038;
    int PARAM_ARRAY_INVALID = 10039;
}
