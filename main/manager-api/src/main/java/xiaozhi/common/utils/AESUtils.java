package xiaozhi.common.utils;

import java.nio.charset.StandardCharsets;
import java.util.Base64;

import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;

public class AESUtils {

    private static final String ALGORITHM = "AES";
    private static final String TRANSFORMATION = "AES/ECB/PKCS5Padding";

    /**
     * AES加密
     * 
     * @param key       密钥（16位、24位或32位）
     * @param plainText 待加密字符串
     * @return 加密后的Base64字符串
     */
    public static String encrypt(String key, String plainText) {
        try {
            // 确保密钥长度为16、24或32位
            byte[] keyBytes = padKey(key.getBytes(StandardCharsets.UTF_8));
            SecretKeySpec secretKey = new SecretKeySpec(keyBytes, ALGORITHM);

            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.ENCRYPT_MODE, secretKey);

            byte[] encryptedBytes = cipher.doFinal(plainText.getBytes(StandardCharsets.UTF_8));
            return Base64.getEncoder().encodeToString(encryptedBytes);
        } catch (Exception e) {
            throw new RuntimeException("AES加密失败", e);
        }
    }

    /**
     * AES解密
     * 
     * @param key           密钥（16位、24位或32位）
     * @param encryptedText 待解密的Base64字符串
     * @return 解密后的字符串
     */
    public static String decrypt(String key, String encryptedText) {
        try {
            // 确保密钥长度为16、24或32位
            byte[] keyBytes = padKey(key.getBytes(StandardCharsets.UTF_8));
            SecretKeySpec secretKey = new SecretKeySpec(keyBytes, ALGORITHM);

            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.DECRYPT_MODE, secretKey);

            byte[] encryptedBytes = Base64.getDecoder().decode(encryptedText);
            byte[] decryptedBytes = cipher.doFinal(encryptedBytes);
            return new String(decryptedBytes, StandardCharsets.UTF_8);
        } catch (Exception e) {
            throw new RuntimeException("AES解密失败", e);
        }
    }

    /**
     * 填充密钥到指定长度（16、24或32位）
     * 
     * @param keyBytes 原始密钥字节数组
     * @return 填充后的密钥字节数组
     */
    private static byte[] padKey(byte[] keyBytes) {
        int keyLength = keyBytes.length;
        if (keyLength == 16 || keyLength == 24 || keyLength == 32) {
            return keyBytes;
        }

        // 如果密钥长度不足，用0填充；如果超过，截取前32位
        byte[] paddedKey = new byte[32];
        System.arraycopy(keyBytes, 0, paddedKey, 0, Math.min(keyLength, 32));
        return paddedKey;
    }
}
