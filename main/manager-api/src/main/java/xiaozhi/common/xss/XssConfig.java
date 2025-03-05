package xiaozhi.common.xss;

import jakarta.servlet.DispatcherType;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.util.PathMatcher;

/**
 * XSS 配置文件
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
@Configuration
@EnableConfigurationProperties(XssProperties.class)
@ConditionalOnProperty(prefix = "renren.xss", value = "enabled")
public class XssConfig {

    @Bean
    public FilterRegistrationBean<XssFilter> xssFilter(XssProperties properties, PathMatcher pathMatcher) {
        FilterRegistrationBean<XssFilter> bean = new FilterRegistrationBean<>();
        bean.setDispatcherTypes(DispatcherType.REQUEST);
        bean.setFilter(new XssFilter(properties, pathMatcher));
        bean.addUrlPatterns("/*");
        bean.setOrder(Integer.MAX_VALUE);
        bean.setName("xssFilter");

        return bean;
    }
}
