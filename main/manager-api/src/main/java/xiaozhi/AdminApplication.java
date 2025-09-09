package xiaozhi;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.core.env.Environment;
import org.springframework.context.ConfigurableApplicationContext;

@SpringBootApplication
public class AdminApplication {

    public static void main(String[] args) {
        // Log profile before Spring Boot starts
        String activeProfile = System.getenv("SPRING_PROFILES_ACTIVE");
        if (activeProfile != null && !activeProfile.isEmpty()) {
            System.out.println("\n========================================");
            System.out.println("Starting with profile: " + activeProfile.toUpperCase());
            System.out.println("========================================\n");
        }
        
        ConfigurableApplicationContext context = SpringApplication.run(AdminApplication.class, args);
        Environment env = context.getEnvironment();
        String[] profiles = env.getActiveProfiles();
        
        if (profiles.length > 0) {
            System.out.println("\n========================================");
            System.out.println("Active Profile: " + profiles[0].toUpperCase());
            System.out.println("Configuration: application-" + profiles[0] + ".yml");
            System.out.println("========================================");
        } else {
            System.out.println("\n========================================");
            System.out.println("No active profile set - using default configuration");
            System.out.println("========================================");
        }
        
        System.out.println("Server started: http://localhost:8002/xiaozhi/doc.html\n");
    }
}