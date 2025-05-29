package xiaozhi.common.exception;

import java.util.List;
import java.util.Objects;

import org.apache.shiro.authz.UnauthorizedException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.validation.ObjectError;
import org.springframework.web.bind.MethodArgumentNotValidException;
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

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public Result<Void> handleMethodArgumentNotValidException(MethodArgumentNotValidException ex) {
        List<ObjectError> allErrors = ex.getBindingResult().getAllErrors();
        String errorMsg = allErrors.stream()
                .filter(Objects::nonNull)
                .map(err -> {
                    String msg = err.getDefaultMessage();
                    return (msg != null && !msg.trim().isEmpty()) ? msg : null;
                })
                .filter(Objects::nonNull)
                .findFirst()
                .orElse("请求参数错误！");

        return new Result<Void>().error(ErrorCode.PARAM_VALUE_NULL, errorMsg);
    }

}