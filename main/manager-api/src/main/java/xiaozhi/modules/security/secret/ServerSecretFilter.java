package xiaozhi.modules.security.secret;

import java.io.IOException;

import org.apache.commons.lang3.StringUtils;
import org.apache.shiro.web.filter.authc.AuthenticatingFilter;
import org.springframework.web.bind.annotation.RequestMethod;

import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.utils.HttpContextUtils;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.sys.service.SysParamsService;

/**
 * Config API 过滤器
 */
@Slf4j
@RequiredArgsConstructor
public class ServerSecretFilter extends AuthenticatingFilter {
    private final SysParamsService sysParamsService;

    @Override
    protected ServerSecretToken createToken(ServletRequest request, ServletResponse response) {
        // 获取请求token
        String token = getRequestToken((HttpServletRequest) request);

        if (StringUtils.isBlank(token)) {
            log.warn("createToken:token is empty");
            return null;
        }

        return new ServerSecretToken(token);
    }

    @Override
    protected boolean isAccessAllowed(ServletRequest request, ServletResponse response, Object mappedValue) {
        // 对OPTIONS请求放行
        if (((HttpServletRequest) request).getMethod().equals(RequestMethod.OPTIONS.name())) {
            return true;
        }
        return false;
    }

    @Override
    protected boolean onAccessDenied(ServletRequest servletRequest, ServletResponse servletResponse) throws Exception {
        // 获取token并校验
        String token = getRequestToken((HttpServletRequest) servletRequest);
        if (StringUtils.isBlank(token)) {
            // token为空，返回401
            this.sendUnauthorizedResponse((HttpServletResponse) servletResponse, "服务器密钥不能为空");
            return false;
        }

        // 验证token是否匹配
        String serverSecret = getServerSecret();
        if (StringUtils.isBlank(serverSecret) || !serverSecret.equals(token)) {
            // token无效，返回401
            this.sendUnauthorizedResponse((HttpServletResponse) servletResponse, "无效的服务器密钥");
            return false;
        }

        return true;
    }

    /**
     * 发送未授权响应
     */
    private void sendUnauthorizedResponse(HttpServletResponse response, String message) {
        response.setContentType("application/json;charset=utf-8");
        response.setHeader("Access-Control-Allow-Credentials", "true");
        response.setHeader("Access-Control-Allow-Origin", HttpContextUtils.getOrigin());

        try {
            String json = JsonUtils.toJsonString(new Result<Void>().error(ErrorCode.UNAUTHORIZED, message));
            response.getWriter().print(json);
        } catch (IOException e) {
            log.error("响应输出失败", e);
        }
    }

    /**
     * 获取请求的token
     */
    private String getRequestToken(HttpServletRequest httpRequest) {
        String token = null;
        // 从header中获取token
        String authorization = httpRequest.getHeader("Authorization");
        if (StringUtils.isNotBlank(authorization) && authorization.startsWith("Bearer ")) {
            token = authorization.replace("Bearer ", "");
        }
        return token;
    }

    private String getServerSecret() {
        return sysParamsService.getValue(Constant.SERVER_SECRET, true);
    }
}
