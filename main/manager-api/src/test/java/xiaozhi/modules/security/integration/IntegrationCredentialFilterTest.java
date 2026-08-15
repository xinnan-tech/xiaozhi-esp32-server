package xiaozhi.modules.security.integration;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.mockito.Mockito.doThrow;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import xiaozhi.common.utils.TestMessageSupport;

class IntegrationCredentialFilterTest {
    @BeforeEach
    void installMessages() {
        TestMessageSupport.install();
    }

    @Test
    void usageMetadataFailureDoesNotInterruptAnAuthenticatedClassroomRequest() {
        String token = "xzi_0123456789abcdef0123456789abcdef.test-secret-material-never-production";
        IntegrationCredentialService service = mock(IntegrationCredentialService.class);
        IntegrationPrincipal principal = new IntegrationPrincipal("credential-1", "explorer", 41L);
        when(service.authenticateExplorerCredential(token)).thenReturn(principal);
        doThrow(new IllegalStateException("database metadata write failed"))
                .when(service).recordUse("credential-1");
        IntegrationCredentialFilter filter = new IntegrationCredentialFilter(service);
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/integration/explorer/agent/a1");
        request.addHeader("Authorization", "Bearer " + token);

        assertTrue(filter.onAccessDenied(request, new MockHttpServletResponse()));
        assertSame(principal, request.getAttribute(IntegrationCredentialFilter.PRINCIPAL_ATTRIBUTE));
    }

    @Test
    void acceptsOnlyAValidBearerCredentialWithoutEchoingIt() throws Exception {
        String token = "xzi_0123456789abcdef0123456789abcdef.test-secret-material-never-production";
        IntegrationCredentialService service = mock(IntegrationCredentialService.class);
        IntegrationPrincipal principal = new IntegrationPrincipal("credential-1", "explorer", 41L);
        when(service.authenticateExplorerCredential(token)).thenReturn(principal);
        IntegrationCredentialFilter filter = new IntegrationCredentialFilter(service);
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/integration/explorer/agent/a1");
        request.addHeader("Authorization", "Bearer " + token);
        MockHttpServletResponse response = new MockHttpServletResponse();

        assertTrue(filter.onAccessDenied(request, response));
        assertSame(principal, request.getAttribute(IntegrationCredentialFilter.PRINCIPAL_ATTRIBUTE));
        verify(service).recordUse("credential-1");
        assertFalse(response.getContentAsString().contains(token));
    }

    @Test
    void rejectsInvalidCredentialWithHttp401AndNoCredentialMaterial() throws Exception {
        String token = "invalid-secret-never-production";
        IntegrationCredentialService service = mock(IntegrationCredentialService.class);
        when(service.authenticateExplorerCredential(token)).thenReturn(null);
        IntegrationCredentialFilter filter = new IntegrationCredentialFilter(service);
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/integration/explorer/agent/a1");
        request.addHeader("Authorization", "Bearer " + token);
        MockHttpServletResponse response = new MockHttpServletResponse();

        assertFalse(filter.onAccessDenied(request, response));
        assertEquals(401, response.getStatus());
        assertFalse(response.getContentAsString().contains(token));
    }
}
