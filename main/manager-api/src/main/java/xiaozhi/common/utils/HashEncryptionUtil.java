package xiaozhi.common.utils;

import lombok.extern.slf4j.Slf4j;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/**
 * 哈希加密算法的工具类
 * @author zjy
 */
@Slf4j
public class HashEncryptionUtil {
    /**
     * 使用md5进行加密
     * @param context 被加密的内容
     * @return 哈希值
     */
    public static String Md5hexDigest(String context){
        return hexDigest(context,"MD5");
    }

    /**
     * 指定哈希算法进行加密
     * @param context 被加密的内容
     * @param algorithm 哈希算法
     * @return 哈希值
     */
   public static String hexDigest(String context,String algorithm ){
       // 获取MD5算法实例
       MessageDigest md = null;
       try {
           md = MessageDigest.getInstance(algorithm);
       } catch (NoSuchAlgorithmException e) {
           log.error("加密失败的算法：{}",algorithm);
           throw new RuntimeException("加密失败，"+ algorithm +"哈希算法系统不支持");
       }
       // 计算智能体id的MD5值
       byte[] messageDigest = md.digest(context.getBytes());
       // 将字节数组转换为十六进制字符串
       StringBuilder hexString = new StringBuilder();
       for (byte b : messageDigest) {
           String hex = Integer.toHexString(0xFF & b);
           if (hex.length() == 1) {
               hexString.append('0');
           }
           hexString.append(hex);
       }
       return hexString.toString();
   }

}
