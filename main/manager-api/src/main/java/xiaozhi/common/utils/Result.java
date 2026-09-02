package xiaozhi.common.utils;

import java.io.Serializable;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import xiaozhi.common.exception.ErrorCode;

/**
 * Response Data
 * Copyright (c) Renren Open Source All rights reserved.
 * Website: https://www.renren.io
 */
@Data
@Schema(description = "响应")
public class Result<T> implements Serializable {

    /**
     * Code: 0 indicates success, other values indicate failure
     */
    @Schema(description = "Code: 0 indicates success, other values indicate failure")
    private int code = 0;
    /**
     * Message content
     */
    @Schema(description = "Message content")
    private String msg = "success";
    /**
     * Response data
     */
    @Schema(description = "Response data")
    private T data;

    public Result<T> ok(T data) {
        this.setData(data);
        return this;
    }

    public Result<T> error() {
        this.code = ErrorCode.INTERNAL_SERVER_ERROR;
        this.msg = MessageUtils.getMessage(this.code);
        return this;
    }

    public Result<T> error(int code) {
        this.code = code;
        this.msg = MessageUtils.getMessage(this.code);
        return this;
    }

    public Result<T> error(int code, String msg) {
        this.code = code;
        this.msg = msg;
        return this;
    }

    public Result<T> error(String msg) {
        this.code = ErrorCode.INTERNAL_SERVER_ERROR;
        this.msg = msg;
        return this;
    }

}