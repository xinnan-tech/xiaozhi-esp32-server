package xiaozhi;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import io.github.cdimascio.dotenv.Dotenv;

@SpringBootApplication
public class AdminApplication {

    public static void main(String[] args) {
        Dotenv dotenv = Dotenv.load();
        System.setProperty("DB_USERNAME", dotenv.get("DB_USERNAME", "root"));
        System.setProperty("DB_PASSWORD", dotenv.get("DB_PASSWORD", "123456"));
        System.setProperty("DB_DRIVER", dotenv.get("DB_DRIVER", "com.mysql.cj.jdbc.Driver"));
        System.setProperty("DB_URL", dotenv.get("DB_URL", "jdbc:mariadb://127.0.0.1:3306/xiaozhi_esp32_server?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai&nullCatalogMeansCurrent=true"));
        System.setProperty("REDIS_HOST", dotenv.get("REDIS_HOST", "127.0.0.1"));
        System.setProperty("REDIS_PASSWORD", dotenv.get("REDIS_PASSWORD", ""));
        System.setProperty("REDIS_PORT", dotenv.get("REDIS_PORT", "6379"));
        System.setProperty("REDIS_DATABASE", dotenv.get("REDIS_DATABASE", ""));
        System.setProperty("KNIFE4J_USERNAME", dotenv.get("KNIFE4J_USERNAME", "renren"));
        System.setProperty("KNIFE4J_PASSWORD", dotenv.get("KNIFE4J_PASSWORD", "2ZABCDEUgF"));

        SpringApplication.run(AdminApplication.class, args);
        System.out.println("http://localhost:8002/xiaozhi/doc.html");
    }
}