package xiaozhi.modules.security.oauth2;

import java.io.IOException;

import org.apache.commons.lang3.StringUtils;
import org.apache.shiro.authc.AuthenticationException;
import org.apache.shiro.authc.AuthenticationToken;
import org.apache.shiro.web.filter.authc.AuthenticatingFilter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.bind.annotation.RequestMethod;

import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.utils.HttpContextUtils;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.common.utils.Result;

/**
 * oauth2过滤器
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
public class Oauth2Filter extends AuthenticatingFilter {

    private static final Logger logger = LoggerFactory.getLogger(Oauth2Filter.class);

    @Override
    protected AuthenticationToken createToken(ServletRequest request, ServletResponse response) throws Exception {
        // 获取请求token
        String token = getRequestToken((HttpServletRequest) request);

        if (StringUtils.isBlank(token)) {
            logger.warn("createToken:token is empty");
            return null;
        }

        return new Oauth2Token(token);
    }

    @Override
    protected boolean isAccessAllowed(ServletRequest request, ServletResponse response, Object mappedValue) {
        if (((HttpServletRequest) request).getMethod().equals(RequestMethod.OPTIONS.name())) {
            return true;
        }

        return false;
    }

    @Override
    protected boolean onAccessDenied(ServletRequest request, ServletResponse response) throws Exception {
        // 获取请求token，如果token不存在，直接返回401
        String token = getRequestToken((HttpServletRequest) request);

        if (StringUtils.isBlank(token)) {
            logger.warn("onAccessDenied:token is empty");

            HttpServletResponse httpResponse = (HttpServletResponse) response;
            httpResponse.setContentType("application/json;charset=utf-8");
            httpResponse.setHeader("Access-Control-Allow-Credentials", "true");
            httpResponse.setHeader("Access-Control-Allow-Origin", HttpContextUtils.getOrigin());

            String json = JsonUtils.toJsonString(new Result<Void>().error(ErrorCode.UNAUTHORIZED));

            httpResponse.getWriter().print(json);

            return false;
        }

        return executeLogin(request, response);
    }

    @Override
    protected boolean onLoginFailure(AuthenticationToken token, AuthenticationException e, ServletRequest request,
            ServletResponse response) {
        HttpServletResponse httpResponse = (HttpServletResponse) response;
        httpResponse.setContentType("application/json;charset=utf-8");
        httpResponse.setHeader("Access-Control-Allow-Credentials", "true");
        httpResponse.setHeader("Access-Control-Allow-Origin", HttpContextUtils.getOrigin());
        try {
            Throwable throwable = e.getCause() == null ? e : e.getCause();
            Result<Void> r = new Result<Void>().error(ErrorCode.UNAUTHORIZED, throwable.getMessage());

            String json = JsonUtils.toJsonString(r);
            httpResponse.getWriter().print(json);
        } catch (IOException e1) {
        }

        return false;
    }

    /**
     * 获取请求的token
     */
    private String getRequestToken(HttpServletRequest httpRequest) {
        String token = null;
        // 从header中获取token
        String authorization = httpRequest.getHeader(Constant.AUTHORIZATION);
        if (StringUtils.isNotBlank(authorization) && authorization.startsWith("Bearer ")) {
            token = authorization.replace("Bearer ", "");
        }
        return token;
    }
}