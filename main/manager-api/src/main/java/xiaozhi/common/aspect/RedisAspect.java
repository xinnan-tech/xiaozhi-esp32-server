package xiaozhi.common.aspect;

import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;

/**
 * Redis切面处理类
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
@Slf4j
@Aspect
@Component
public class RedisAspect {
    /**
     * 是否开启redis缓存 true开启 false关闭
     */
    @Value("${renren.redis.open}")
    private boolean open;

    @Around("execution(* xiaozhi.common.redis.RedisUtils.*(..))")
    public Object around(ProceedingJoinPoint point) throws Throwable {
        Object result = null;
        if (open) {
            try {
                result = point.proceed();
            } catch (Exception e) {
                log.error("redis error", e);
                throw new RenException(ErrorCode.REDIS_ERROR);
            }
        }
        return result;
    }
}
