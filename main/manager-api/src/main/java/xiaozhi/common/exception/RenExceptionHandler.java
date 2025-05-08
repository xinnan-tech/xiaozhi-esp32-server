package xiaozhi.common.exception;

import org.apache.shiro.authz.UnauthorizedException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.utils.Result;

/**
 * 异常处理器
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
@Slf4j
@AllArgsConstructor
@RestControllerAdvice
public class RenExceptionHandler {

    /**
     * 处理自定义异常
     */
    @ExceptionHandler(RenException.class)
    public Result<Void> handleRenException(RenException ex) {
        Result<Void> result = new Result<>();
        result.error(ex.getCode(), ex.getMsg());

        return result;
    }

    @ExceptionHandler(DuplicateKeyException.class)
    public Result<Void> handleDuplicateKeyException(DuplicateKeyException ex) {
        Result<Void> result = new Result<>();
        result.error(ErrorCode.DB_RECORD_EXISTS);

        return result;
    }

    @ExceptionHandler(UnauthorizedException.class)
    public Result<Void> handleUnauthorizedException(UnauthorizedException ex) {
        Result<Void> result = new Result<>();
        result.error(ErrorCode.FORBIDDEN);

        return result;
    }

    @ExceptionHandler(Exception.class)
    public Result<Void> handleException(Exception ex) {
        log.error(ex.getMessage(), ex);

        return new Result<Void>().error();
    }

    @ExceptionHandler(NoResourceFoundException.class)
    public Result<Void> handleNoResourceFoundException(NoResourceFoundException ex) {
        log.warn("Resource not found: {}", ex.getMessage());
        return new Result<Void>().error(404, "资源不存在");
    }

}