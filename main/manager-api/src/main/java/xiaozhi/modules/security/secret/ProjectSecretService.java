package xiaozhi.modules.security.secret;

import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.SecureRandom;
import java.util.Base64;

import javax.crypto.Cipher;
import javax.crypto.Mac;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * Encrypts project secrets with purpose-separated keys derived from one master key.
 */
@Component
public class ProjectSecretService {
    private static final String PREFIX = "enc:v1:a256gcm:";
    private static final byte[] HKDF_SALT = "xiaozhi-project-secret-v1".getBytes(StandardCharsets.UTF_8);
    private static final int NONCE_LENGTH = 12;
    private static final int TAG_LENGTH_BITS = 128;

    private final byte[] masterKey;
    private final SecureRandom secureRandom;

    public ProjectSecretService(@Value("${xiaozhi.secret.master-key:}") String encodedMasterKey) {
        this(encodedMasterKey, new SecureRandom());
    }

    ProjectSecretService(String encodedMasterKey, SecureRandom secureRandom) {
        this.secureRandom = secureRandom;
        if (StringUtils.isBlank(encodedMasterKey)) {
            this.masterKey = null;
            return;
        }
        try {
            this.masterKey = Base64.getDecoder().decode(encodedMasterKey.trim());
        } catch (IllegalArgumentException exception) {
            throw new IllegalStateException("xiaozhi.secret.master-key must be valid Base64", exception);
        }
        if (this.masterKey.length != 32) {
            throw new IllegalStateException("xiaozhi.secret.master-key must decode to exactly 32 bytes");
        }
    }

    public boolean isConfigured() {
        return masterKey != null;
    }

    public boolean isEncrypted(String value) {
        return value != null && value.startsWith(PREFIX);
    }

    public String encrypt(String plaintext, String purpose, String aad) {
        requireConfigured();
        if (plaintext == null) {
            return null;
        }
        byte[] nonce = new byte[NONCE_LENGTH];
        secureRandom.nextBytes(nonce);
        try {
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(deriveKey(purpose), "AES"),
                    new GCMParameterSpec(TAG_LENGTH_BITS, nonce));
            cipher.updateAAD(requireText(aad, "aad").getBytes(StandardCharsets.UTF_8));
            byte[] ciphertext = cipher.doFinal(plaintext.getBytes(StandardCharsets.UTF_8));
            Base64.Encoder encoder = Base64.getUrlEncoder().withoutPadding();
            return PREFIX + encoder.encodeToString(nonce) + ":" + encoder.encodeToString(ciphertext);
        } catch (GeneralSecurityException exception) {
            throw new IllegalStateException("Project secret encryption failed", exception);
        }
    }

    public String decrypt(String envelope, String purpose, String aad) {
        requireConfigured();
        if (!isEncrypted(envelope)) {
            throw new IllegalArgumentException("Unsupported project secret envelope");
        }
        String payload = envelope.substring(PREFIX.length());
        String[] parts = payload.split(":", 2);
        if (parts.length != 2) {
            throw new IllegalArgumentException("Malformed project secret envelope");
        }
        try {
            Base64.Decoder decoder = Base64.getUrlDecoder();
            byte[] nonce = decoder.decode(parts[0]);
            if (nonce.length != NONCE_LENGTH) {
                throw new IllegalArgumentException("Malformed project secret nonce");
            }
            byte[] ciphertext = decoder.decode(parts[1]);
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(deriveKey(purpose), "AES"),
                    new GCMParameterSpec(TAG_LENGTH_BITS, nonce));
            cipher.updateAAD(requireText(aad, "aad").getBytes(StandardCharsets.UTF_8));
            return new String(cipher.doFinal(ciphertext), StandardCharsets.UTF_8);
        } catch (IllegalArgumentException exception) {
            throw exception;
        } catch (GeneralSecurityException exception) {
            throw new IllegalStateException("Project secret decryption failed", exception);
        }
    }

    private byte[] deriveKey(String purpose) throws GeneralSecurityException {
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(HKDF_SALT, "HmacSHA256"));
        byte[] pseudorandomKey = mac.doFinal(masterKey);

        mac.init(new SecretKeySpec(pseudorandomKey, "HmacSHA256"));
        mac.update(requireText(purpose, "purpose").getBytes(StandardCharsets.UTF_8));
        mac.update((byte) 1);
        return mac.doFinal();
    }

    private void requireConfigured() {
        if (!isConfigured()) {
            throw new IllegalStateException("xiaozhi.secret.master-key is not configured");
        }
    }

    private static String requireText(String value, String name) {
        if (StringUtils.isBlank(value)) {
            throw new IllegalArgumentException(name + " must not be blank");
        }
        return value;
    }
}
