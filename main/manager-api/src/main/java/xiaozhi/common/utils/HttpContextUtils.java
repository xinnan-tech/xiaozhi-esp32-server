package xiaozhi.common.utils;

import java.util.Date;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.springframework.http.HttpHeaders;
import org.springframework.util.DigestUtils;
import org.springframework.web.context.request.RequestAttributes;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import jakarta.servlet.http.HttpServletRequest;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;

/**
 * Http
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
public class HttpContextUtils {

    public static HttpServletRequest getHttpServletRequest() {
        RequestAttributes requestAttributes = RequestContextHolder.getRequestAttributes();
        if (requestAttributes == null) {
            return null;
        }

        return ((ServletRequestAttributes) requestAttributes).getRequest();
    }

    public static String getToken(String authorization) {
        String token;
        if (StringUtils.isBlank(authorization) && authorization.contains("Bearer ")) {
            throw new RenException(ErrorCode.UNAUTHORIZED);
        }
        token = authorization.replace("Bearer ", "");
        if (StringUtils.isBlank(token)) {
            throw new RenException(ErrorCode.TOKEN_NOT_EMPTY);
        }
        return token;
    }

    public static Map<String, String> getParameterMap(HttpServletRequest request) {
        Enumeration<String> parameters = request.getParameterNames();

        Map<String, String> params = new HashMap<>();
        while (parameters.hasMoreElements()) {
            String parameter = parameters.nextElement();
            String value = request.getParameter(parameter);
            if (StringUtils.isNotBlank(value)) {
                params.put(parameter, value);
            }
        }

        return params;
    }

    public static String getDomain() {
        HttpServletRequest request = getHttpServletRequest();
        StringBuffer url = request.getRequestURL();
        return url.delete(url.length() - request.getRequestURI().length(), url.length()).toString();
    }

    public static String getOrigin() {
        HttpServletRequest request = getHttpServletRequest();
        return request.getHeader(HttpHeaders.ORIGIN);
    }

    public static String getLanguage() {
        // 默认语言
        String defaultLanguage = "zh-CN";
        // request
        HttpServletRequest request = getHttpServletRequest();
        if (request == null) {
            return defaultLanguage;
        }

        // 请求语言
        defaultLanguage = request.getHeader(HttpHeaders.ACCEPT_LANGUAGE);

        return defaultLanguage;
    }

    /**
     * 获取客户端的唯一标识
     *
     * @return
     */
    public static String getClientCode() {
        HttpServletRequest request = getHttpServletRequest();
        if (request == null) {
            return null;
        }
        String reqId = request.getHeader("User-Agent").toLowerCase();
        String ipAddr = IpUtils.getIpAddr(request);
        String date = DateUtils.format(new Date());
        reqId = DigestUtils.md5DigestAsHex((ipAddr + date + reqId).getBytes());
        return reqId;
    }

    public static String getRequestURI() {
        HttpServletRequest request = getHttpServletRequest();
        String url = request.getRequestURI();
        return url;
    }
}