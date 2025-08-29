package xiaozhi.migration;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;

import jakarta.annotation.PostConstruct;
import java.io.File;
import java.util.List;

/**
 * Configuration class for Content Library Migration
 * 
 * This class manages all migration-specific configuration properties
 * and provides validation for paths and settings.
 * 
 * @author Data Migration Configuration
 * @version 1.0
 */
@Data
@Configuration
@Profile("migration")
@ConfigurationProperties(prefix = "migration.content-library")
public class MigrationConfiguration {

    /**
     * Base path for xiaozhi-server directory
     */
    private String basePath = System.getProperty("user.dir") + "/xiaozhi-server";
    
    /**
     * Batch size for database operations
     */
    private int batchSize = 100;
    
    /**
     * Whether to skip migration if content already exists
     */
    private boolean skipIfExists = false;
    
    /**
     * Connection timeout in milliseconds
     */
    private int connectionTimeout = 30000;
    
    /**
     * Read timeout in milliseconds
     */
    private int readTimeout = 60000;
    
    /**
     * Music directory path
     */
    private String musicPath;
    
    /**
     * Stories directory path
     */
    private String storiesPath;
    
    /**
     * Music configuration
     */
    private MusicConfig music = new MusicConfig();
    
    /**
     * Stories configuration
     */
    private StoriesConfig stories = new StoriesConfig();
    
    @PostConstruct
    public void init() {
        // Override with environment variables if present
        String envBasePath = System.getenv("MIGRATION_BASE_PATH");
        if (envBasePath != null && !envBasePath.trim().isEmpty()) {
            this.basePath = envBasePath;
        }
        
        String envBatchSize = System.getenv("MIGRATION_BATCH_SIZE");
        if (envBatchSize != null && !envBatchSize.trim().isEmpty()) {
            try {
                this.batchSize = Integer.parseInt(envBatchSize);
            } catch (NumberFormatException e) {
                throw new IllegalArgumentException("Invalid MIGRATION_BATCH_SIZE value: " + envBatchSize);
            }
        }
        
        // Set derived paths if not already set
        if (musicPath == null) {
            musicPath = basePath + "/music";
        }
        
        if (storiesPath == null) {
            storiesPath = basePath + "/stories";
        }
        
        // Validate configuration
        validateConfiguration();
    }
    
    /**
     * Validate migration configuration
     */
    private void validateConfiguration() {
        validatePath(basePath, "Base path");
        validatePath(musicPath, "Music path");
        validatePath(storiesPath, "Stories path");
        
        if (batchSize <= 0 || batchSize > 1000) {
            throw new IllegalArgumentException("Batch size must be between 1 and 1000, got: " + batchSize);
        }
        
        if (connectionTimeout <= 0) {
            throw new IllegalArgumentException("Connection timeout must be positive, got: " + connectionTimeout);
        }
        
        if (readTimeout <= 0) {
            throw new IllegalArgumentException("Read timeout must be positive, got: " + readTimeout);
        }
    }
    
    /**
     * Validate that a path exists
     */
    private void validatePath(String path, String description) {
        if (path == null || path.trim().isEmpty()) {
            throw new IllegalArgumentException(description + " cannot be empty");
        }
        
        File file = new File(path);
        if (!file.exists()) {
            throw new IllegalArgumentException(description + " does not exist: " + path);
        }
        
        if (!file.isDirectory()) {
            throw new IllegalArgumentException(description + " is not a directory: " + path);
        }
    }
    
    /**
     * Get absolute path for music directory
     */
    public String getAbsoluteMusicPath() {
        return new File(musicPath).getAbsolutePath();
    }
    
    /**
     * Get absolute path for stories directory
     */
    public String getAbsoluteStoriesPath() {
        return new File(storiesPath).getAbsolutePath();
    }
    
    /**
     * Get absolute base path
     */
    public String getAbsoluteBasePath() {
        return new File(basePath).getAbsolutePath();
    }
    
    /**
     * Music content configuration
     */
    @Data
    public static class MusicConfig {
        private String contentType = "music";
        private List<String> supportedLanguages = List.of(
            "English", "Hindi", "Kannada", "Phonics", "Telugu"
        );
    }
    
    /**
     * Stories content configuration
     */
    @Data
    public static class StoriesConfig {
        private String contentType = "story";
        private List<String> supportedGenres = List.of(
            "Adventure", "Bedtime", "Educational", "Fairy Tales", "Fantasy"
        );
    }
    
    /**
     * Check if a language is supported for music content
     */
    public boolean isSupportedMusicLanguage(String language) {
        return music.getSupportedLanguages().contains(language);
    }
    
    /**
     * Check if a genre is supported for story content
     */
    public boolean isSupportedStoryGenre(String genre) {
        return stories.getSupportedGenres().contains(genre);
    }
}