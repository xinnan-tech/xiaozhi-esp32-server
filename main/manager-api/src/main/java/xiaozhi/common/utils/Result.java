package xiaozhi.common.utils;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import xiaozhi.common.exception.ErrorCode;

import java.io.Serializable;

/**
 * 响应数据
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
@Data
@Schema(description = "响应")
public class Result<T> implements Serializable {

    /**
     * 编码：0表示成功，其他值表示失败
     */
    @Schema(description = "编码：0表示成功，其他值表示失败")
    private int code = 0;
    /**
     * 消息内容
     */
    @Schema(description = "消息内容")
    private String msg = "success";
    /**
     * 响应数据
     */
    @Schema(description = "响应数据")
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