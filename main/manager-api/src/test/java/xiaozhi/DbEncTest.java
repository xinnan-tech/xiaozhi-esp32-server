package xiaozhi;

import org.jasypt.encryption.StringEncryptor;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.junit4.SpringRunner;

/**
 * 单元测试
 */
@RunWith(SpringRunner.class)
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public class DbEncTest {

    @Autowired
    StringEncryptor stringEncryptor;

    @Test
    public void jiami() {
        System.out.println("username:" + stringEncryptor.encrypt("07e43e8d669fb946e31ccd4ef5f32c9f2287619c79b766a5985d2c99ad7b7c7e"));
        System.out.println("password:" + stringEncryptor.encrypt("042e94093fd2c2765ea45cf13ddbfd38e93026df4b6d5e4206ea5ac90956d63ab73e8b82c6daf7829f9aea7e27e1db5bb0a90944c4c4985af44db0ef49c46d6ad6"));
    }
}
