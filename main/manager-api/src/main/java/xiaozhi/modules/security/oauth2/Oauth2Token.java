package xiaozhi.modules.security.oauth2;

import org.apache.shiro.authc.AuthenticationToken;

/**
 * token
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
public class Oauth2Token implements AuthenticationToken {
    private String token;

    public Oauth2Token(String token) {
        this.token = token;
    }

    @Override
    public String getPrincipal() {
        return token;
    }

    @Override
    public Object getCredentials() {
        return token;
    }
}
