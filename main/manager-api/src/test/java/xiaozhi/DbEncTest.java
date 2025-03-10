package xiaozhi;
import org.jasypt.encryption.StringEncryptor;
// 如果使用 JUnit 5
import org.junit.jupiter.api.Test;
// 如果使用 JUnit 4，需要确保项目中添加了 JUnit 4 的依赖
// import org.junit.Test;
// 由于原导入语句无法解析，若使用 JUnit 5，移除该导入
// 若后续代码需要使用 JUnit 4 的 @RunWith 注解，需确保项目添加 JUnit 4 依赖
// 这里假设使用 JUnit 5，移除该导入
// import org.junit.runner.RunWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
// import org.springframework.test.context.junit4.SpringRunner;

/**
 * 单元测试
 */
// 由于原代码使用了 JUnit 5 的导入，这里移除 JUnit 4 的 @RunWith 注解
// 若后续需要使用 JUnit 4 的功能，需确保项目添加 JUnit 4 依赖
// @RunWith(SpringRunner.class)
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
