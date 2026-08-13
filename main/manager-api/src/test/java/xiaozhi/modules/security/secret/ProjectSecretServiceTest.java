package xiaozhi.modules.security.secret;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.Base64;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

class ProjectSecretServiceTest {
    @Test
    void productionConstructorIsExplicitlyAutowired() throws Exception {
        assertNotNull(ProjectSecretService.class.getConstructor(String.class).getAnnotation(Autowired.class));
    }

    private static final String MASTER_KEY = Base64.getEncoder().encodeToString(new byte[32]);

    @Test
    void encryptsWithRandomNonceAndRequiresMatchingContext() {
        ProjectSecretService service = new ProjectSecretService(MASTER_KEY);

        String first = service.encrypt("private", "weather-key", "agent-a");
        String second = service.encrypt("private", "weather-key", "agent-a");

        assertTrue(service.isEncrypted(first));
        assertNotEquals(first, second);
        assertEquals("private", service.decrypt(first, "weather-key", "agent-a"));
        assertThrows(IllegalStateException.class,
                () -> service.decrypt(first, "weather-key", "agent-b"));
    }

    @Test
    void allowsLegacyModeOnlyWhenMasterKeyIsAbsent() {
        ProjectSecretService service = new ProjectSecretService("");

        assertFalse(service.isConfigured());
        assertThrows(IllegalStateException.class,
                () -> service.encrypt("private", "weather-key", "agent-a"));
    }

    @Test
    void rejectsWrongLengthMasterKey() {
        String shortKey = Base64.getEncoder().encodeToString(new byte[16]);

        assertThrows(IllegalStateException.class, () -> new ProjectSecretService(shortKey));
    }
}
