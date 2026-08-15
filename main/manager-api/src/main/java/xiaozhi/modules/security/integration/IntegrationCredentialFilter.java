package xiaozhi.modules.security.integration;

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
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.common.utils.Result;

@Slf4j
@RequiredArgsConstructor
public class IntegrationCredentialFilter extends AuthenticatingFilter {
    public static final String PRINCIPAL_ATTRIBUTE = IntegrationCredentialFilter.class.getName() + ".principal";

    private final IntegrationCredentialService credentialService;

    @Override
    protected org.apache.shiro.authc.AuthenticationToken createToken(
            ServletRequest request, ServletResponse response) {
        return null;
    }

    @Override
    protected boolean isAccessAllowed(ServletRequest request, ServletResponse response, Object mappedValue) {
        return ((HttpServletRequest) request).getMethod().equals(RequestMethod.OPTIONS.name());
    }

    @Override
    protected boolean onAccessDenied(ServletRequest servletRequest, ServletResponse servletResponse) {
        HttpServletRequest request = (HttpServletRequest) servletRequest;
        HttpServletResponse response = (HttpServletResponse) servletResponse;
        String rawToken = bearerToken(request);
        IntegrationPrincipal principal = credentialService.authenticateExplorerCredential(rawToken);
        if (principal == null) {
            log.warn("Integration request rejected: subject={}, method={}, path={}",
                    IntegrationCredentialService.EXPLORER_SUBJECT, request.getMethod(), request.getRequestURI());
            sendUnauthorized(response);
            return false;
        }

        request.setAttribute(PRINCIPAL_ATTRIBUTE, principal);
        try {
            credentialService.recordUse(principal.credentialId());
        } catch (RuntimeException exception) {
            log.warn("Unable to update integration credential usage metadata: credentialId={}",
                    principal.credentialId());
        }
        log.info("Integration request authenticated: subject={}, credentialId={}, method={}, path={}",
                principal.subject(), principal.credentialId(), request.getMethod(), request.getRequestURI());
        return true;
    }

    private String bearerToken(HttpServletRequest request) {
        String authorization = request.getHeader("Authorization");
        if (StringUtils.isBlank(authorization) || !authorization.startsWith("Bearer ")) return null;
        String token = authorization.substring("Bearer ".length()).trim();
        return StringUtils.isBlank(token) ? null : token;
    }

    private void sendUnauthorized(HttpServletResponse response) {
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        response.setContentType("application/json;charset=utf-8");
        try {
            response.getWriter().print(JsonUtils.toJsonString(
                    new Result<Void>().error(ErrorCode.UNAUTHORIZED)));
        } catch (IOException exception) {
            log.warn("Unable to write integration unauthorized response");
        }
    }
}
