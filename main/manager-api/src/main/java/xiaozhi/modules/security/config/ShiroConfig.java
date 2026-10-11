package xiaozhi.modules.security.config;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;

import org.apache.shiro.session.mgt.SessionManager;
import org.apache.shiro.spring.LifecycleBeanPostProcessor;
import org.apache.shiro.spring.security.interceptor.AuthorizationAttributeSourceAdvisor;
import org.apache.shiro.spring.web.ShiroFilterFactoryBean;
import org.apache.shiro.web.config.ShiroFilterConfiguration;
import org.apache.shiro.web.mgt.DefaultWebSecurityManager;
import org.apache.shiro.web.mgt.WebSecurityManager;
import org.apache.shiro.web.session.mgt.DefaultWebSessionManager;
import org.springframework.beans.factory.config.BeanDefinition;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Lazy;
import org.springframework.context.annotation.Role;

import jakarta.servlet.Filter;
import xiaozhi.modules.security.oauth2.Oauth2Filter;
import xiaozhi.modules.security.oauth2.Oauth2Realm;
import xiaozhi.modules.security.secret.ServerSecretFilter;
import xiaozhi.modules.sys.service.SysParamsService;

/**
 * Shiro configuration file
 * Copyright (c) Renren Open Source All rights reserved.
 * Website: https://www.renren.io
 */
@Configuration
public class ShiroConfig {

    @Bean
    public DefaultWebSessionManager sessionManager() {
        DefaultWebSessionManager sessionManager = new DefaultWebSessionManager();
        sessionManager.setSessionValidationSchedulerEnabled(false);
        sessionManager.setSessionIdUrlRewritingEnabled(false);

        return sessionManager;
    }

    @Bean("securityManager")
    public WebSecurityManager securityManager(Oauth2Realm oAuth2Realm, SessionManager sessionManager) {
        DefaultWebSecurityManager securityManager = new DefaultWebSecurityManager();
        securityManager.setRealm(oAuth2Realm);
        securityManager.setSessionManager(sessionManager);
        securityManager.setRememberMeManager(null);
        return securityManager;
    }

    @Bean("shiroFilter")
    public static ShiroFilterFactoryBean shirFilter(@Lazy WebSecurityManager securityManager,
            @Lazy SysParamsService sysParamsService) {
        ShiroFilterConfiguration config = new ShiroFilterConfiguration();
        config.setFilterOncePerRequest(true);

        ShiroFilterFactoryBean shiroFilter = new ShiroFilterFactoryBean();
        shiroFilter.setSecurityManager(securityManager);
        shiroFilter.setShiroFilterConfiguration(config);

        Map<String, Filter> filters = new HashMap<>();
        // oauth filter
        filters.put("oauth2", new Oauth2Filter());
        // Service secret filter
        filters.put("server", new ServerSecretFilter(sysParamsService));
        shiroFilter.setFilters(filters);

        // Add Shiro built-in filters
        /*
         * anon: Can access without authentication
         * authc: Must be authenticated to access
         * user: Must have remember me functionality to access
         * perms: Must have permission to a resource to access
         * role: Must have a role permission to access
         */
        Map<String, String> filterMap = new LinkedHashMap<>();
        filterMap.put("/ota/**", "anon");
        filterMap.put("/otaMag/download/**", "anon");
        filterMap.put("/webjars/**", "anon");
        filterMap.put("/druid/**", "anon");
        filterMap.put("/v3/api-docs/**", "anon");
        filterMap.put("/doc.html", "anon");
        filterMap.put("/favicon.ico", "anon");
        filterMap.put("/user/captcha", "anon");
        filterMap.put("/user/smsVerification", "anon");
        filterMap.put("/user/login", "anon");
        filterMap.put("/user/pub-config", "anon");
        filterMap.put("/user/register", "anon");
        filterMap.put("/user/retrieve-password", "anon");
        // Use server service filter for config path
        filterMap.put("/config/**", "server");
        filterMap.put("/device/address-book/call", "server");
        filterMap.put("/agent/chat-history/report", "server");
        filterMap.put("/agent/chat-history/download/**", "anon");
        filterMap.put("/agent/chat-summary/**", "server");
        filterMap.put("/agent/chat-title/**", "server");
        filterMap.put("/agent/play/**", "anon");
        filterMap.put("/voiceClone/play/**", "anon");
        filterMap.put("/**", "oauth2");
        shiroFilter.setFilterChainDefinitionMap(filterMap);

        return shiroFilter;
    }

    @Bean("lifecycleBeanPostProcessor")
    public static LifecycleBeanPostProcessor lifecycleBeanPostProcessor() {
        return new LifecycleBeanPostProcessor();
    }

    @Bean
    @Role(BeanDefinition.ROLE_INFRASTRUCTURE)
    public static AuthorizationAttributeSourceAdvisor authorizationAttributeSourceAdvisor(
            @Lazy WebSecurityManager securityManager) {
        AuthorizationAttributeSourceAdvisor advisor = new AuthorizationAttributeSourceAdvisor();
        advisor.setSecurityManager(securityManager);
        return advisor;
    }
}
