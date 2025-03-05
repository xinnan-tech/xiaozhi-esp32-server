package xiaozhi.common.annotation;

import java.lang.annotation.*;

/**
 * 操作日志注解
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface LogOperation {

    String value() default "";
}
