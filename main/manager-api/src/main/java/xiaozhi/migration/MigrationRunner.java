package xiaozhi.migration;

import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

/**
 * Standalone Migration Runner
 * 
 * This class provides a standalone entry point for running the content library migration
 * without starting the full application.
 * 
 * Usage:
 * 1. Command line: mvn exec:java -Dexec.mainClass="xiaozhi.migration.MigrationRunner" -Dspring.profiles.active=migration
 * 2. IDE: Run this class directly with VM options: -Dspring.profiles.active=migration
 * 3. JAR: java -cp app.jar xiaozhi.migration.MigrationRunner --spring.profiles.active=migration
 * 
 * Environment Variables:
 * - XIAOZHI_SERVER_PATH: Override the default xiaozhi-server path
 * - MIGRATION_BATCH_SIZE: Override the default batch size (default: 100)
 * - MIGRATION_BASE_PATH: Override the base path for migration files
 * 
 * The migration process will:
 * 1. Scan xiaozhi-server/music/[language]/metadata.json files
 * 2. Scan xiaozhi-server/stories/[genre]/metadata.json files
 * 3. Parse JSON content and create ContentLibraryDTO objects
 * 4. Batch insert content into the content_library table
 * 5. Provide detailed logging and statistics
 * 
 * @author Data Migration Script Generator
 * @version 1.0
 */
@Slf4j
@SpringBootApplication
@ComponentScan(basePackages = {
    "xiaozhi.migration",           // Migration components
    "xiaozhi.modules.content",     // Content service components
    "xiaozhi.common",             // Common utilities
    "xiaozhi.config"              // Configuration classes
})
public class MigrationRunner {

    public static void main(String[] args) {
        log.info("=======================================================");
        log.info("XiaoZhi Content Library Migration Runner");
        log.info("=======================================================");
        
        // Set migration profile if not already set
        String profiles = System.getProperty("spring.profiles.active");
        if (profiles == null || !profiles.contains("migration")) {
            System.setProperty("spring.profiles.active", "migration");
            log.info("Setting spring profile to 'migration'");
        }
        
        // Log environment configuration
        logEnvironmentInfo();
        
        try {
            // Create Spring context and run migration
            SpringApplication app = new SpringApplication(MigrationRunner.class);
            
            // Disable web environment for migration
            app.setWebApplicationType(org.springframework.boot.WebApplicationType.NONE);
            
            // Disable banner for cleaner output
            app.setBannerMode(org.springframework.boot.Banner.Mode.OFF);
            
            // Run the application
            var context = app.run(args);
            
            log.info("Migration completed successfully!");
            log.info("Application context will be closed automatically");
            
            // Gracefully shutdown
            SpringApplication.exit(context, () -> 0);
            
        } catch (Exception e) {
            log.error("Migration failed with error: {}", e.getMessage(), e);
            System.exit(1);
        }
    }
    
    /**
     * Log environment configuration for debugging
     */
    private static void logEnvironmentInfo() {
        log.info("Environment Configuration:");
        log.info("  - Java Version: {}", System.getProperty("java.version"));
        log.info("  - Working Directory: {}", System.getProperty("user.dir"));
        log.info("  - Spring Profiles: {}", System.getProperty("spring.profiles.active", "default"));
        
        String xiaozhiPath = System.getenv("XIAOZHI_SERVER_PATH");
        if (xiaozhiPath != null) {
            log.info("  - XiaoZhi Server Path (env): {}", xiaozhiPath);
        }
        
        String batchSize = System.getenv("MIGRATION_BATCH_SIZE");
        if (batchSize != null) {
            log.info("  - Batch Size (env): {}", batchSize);
        }
        
        String basePath = System.getenv("MIGRATION_BASE_PATH");
        if (basePath != null) {
            log.info("  - Base Path (env): {}", basePath);
        }
        
        log.info("=======================================================");
    }
}