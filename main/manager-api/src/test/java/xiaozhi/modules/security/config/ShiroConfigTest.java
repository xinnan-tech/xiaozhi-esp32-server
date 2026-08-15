package xiaozhi.modules.security.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;

import java.lang.reflect.Method;
import java.lang.reflect.Modifier;

import org.apache.shiro.session.mgt.SessionManager;
import org.apache.shiro.spring.web.ShiroFilterFactoryBean;
import org.apache.shiro.web.mgt.WebSecurityManager;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.config.BeanDefinition;
import org.springframework.beans.factory.config.BeanPostProcessor;
import org.springframework.context.annotation.Lazy;
import org.springframework.context.annotation.Role;

import xiaozhi.modules.security.oauth2.Oauth2Realm;
import xiaozhi.modules.security.integration.IntegrationCredentialService;
import xiaozhi.modules.sys.service.SysParamsService;

class ShiroConfigTest {

    @Test
    void beanPostProcessorFactoriesDoNotInstantiateShiroConfigOrBusinessDependenciesEarly() throws Exception {
        Method lifecycleFactory = ShiroConfig.class.getDeclaredMethod("lifecycleBeanPostProcessor");
        Method filterFactory = ShiroConfig.class.getDeclaredMethod(
                "shirFilter", WebSecurityManager.class, SysParamsService.class,
                IntegrationCredentialService.class);

        assertTrue(Modifier.isStatic(lifecycleFactory.getModifiers()));
        assertTrue(BeanPostProcessor.class.isAssignableFrom(ShiroFilterFactoryBean.class));
        assertTrue(Modifier.isStatic(filterFactory.getModifiers()));
        Lazy securityManagerLazy = filterFactory.getParameters()[0].getAnnotation(Lazy.class);
        Lazy sysParamsServiceLazy = filterFactory.getParameters()[1].getAnnotation(Lazy.class);
        Lazy integrationCredentialServiceLazy = filterFactory.getParameters()[2].getAnnotation(Lazy.class);
        assertNotNull(securityManagerLazy);
        assertNotNull(sysParamsServiceLazy);
        assertTrue(securityManagerLazy.value());
        assertTrue(sysParamsServiceLazy.value());
        assertNotNull(integrationCredentialServiceLazy);
        assertTrue(integrationCredentialServiceLazy.value());
    }

    @Test
    void authorizationAdvisorIsInfrastructureAndDefersItsSecurityManager() throws Exception {
        Method advisorFactory = ShiroConfig.class.getDeclaredMethod(
                "authorizationAttributeSourceAdvisor", WebSecurityManager.class);

        assertTrue(Modifier.isStatic(advisorFactory.getModifiers()));
        Lazy securityManagerLazy = advisorFactory.getParameters()[0].getAnnotation(Lazy.class);
        assertNotNull(securityManagerLazy);
        assertTrue(securityManagerLazy.value());
        assertEquals(BeanDefinition.ROLE_INFRASTRUCTURE, advisorFactory.getAnnotation(Role.class).value());
    }

    @Test
    void securityManagerRetainsTheWebSecurityContractRequiredByShiroFilter() throws Exception {
        Method securityManagerFactory = ShiroConfig.class.getDeclaredMethod(
                "securityManager", Oauth2Realm.class, SessionManager.class);

        assertEquals(WebSecurityManager.class, securityManagerFactory.getReturnType());
    }

    @Test
    void integrationCredentialIsConfinedToDedicatedExplorerRoutes() {
        ShiroFilterFactoryBean filter = ShiroConfig.shirFilter(
                mock(WebSecurityManager.class),
                mock(SysParamsService.class),
                mock(IntegrationCredentialService.class));

        assertEquals("integration", filter.getFilterChainDefinitionMap().get("/integration/explorer/**"));
        assertEquals("oauth2", filter.getFilterChainDefinitionMap().get("/**"));
        assertEquals(null, filter.getFilterChainDefinitionMap().get("/agent/**"));
        assertEquals(null, filter.getFilterChainDefinitionMap().get("/device/**"));
        assertEquals(null, filter.getFilterChainDefinitionMap().get("/admin/**"));
    }
}
