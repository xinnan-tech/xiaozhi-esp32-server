package xiaozhi.migration;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.stream.Collectors;

import com.google.gson.*;
import com.google.gson.reflect.TypeToken;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import xiaozhi.modules.content.dto.ContentLibraryDTO;
import xiaozhi.modules.content.entity.ContentLibraryEntity;
import xiaozhi.modules.content.service.ContentLibraryService;

/**
 * Data Migration Script for Content Library
 * 
 * This script migrates content metadata from JSON files in the xiaozhi-server directory
 * to the content_library database table.
 * 
 * Usage: Run as a Spring Boot application with migration profile
 * java -jar app.jar --spring.profiles.active=migration
 * 
 * Directory Structure:
 * - xiaozhi-server/music/[Language]/metadata.json (English, Hindi, Kannada, Phonics, Telugu)
 * - xiaozhi-server/stories/[Genre]/metadata.json (Adventure, Bedtime, Educational, Fairy Tales, Fantasy)
 * 
 * @author Data Migration Script Generator
 * @version 1.0
 */
@Slf4j
@Component
public class ContentLibraryMigration implements CommandLineRunner {

    @Autowired
    private ContentLibraryService contentLibraryService;

    private final Gson gson = new GsonBuilder().setPrettyPrinting().create();
    
    // Base path configuration - adjust as needed based on deployment structure
    private static final String BASE_PATH = "/Users/craftech360/Downloads/app/cheeko_server/main/xiaozhi-server";
    private static final String MUSIC_PATH = BASE_PATH + "/music";
    private static final String STORIES_PATH = BASE_PATH + "/stories";
    
    // Batch size for database operations
    private static final int BATCH_SIZE = 100;
    
    // Migration statistics
    private final MigrationStatistics stats = new MigrationStatistics();

    @Override
    public void run(String... args) throws Exception {
        // Check if migration profile is active
        String profiles = System.getProperty("spring.profiles.active", "");
        if (!profiles.contains("migration")) {
            log.info("Migration profile not active, skipping content library migration");
            return;
        }

        log.info("Starting Content Library Migration...");
        log.info("Base path: {}", BASE_PATH);
        
        try {
            // Verify directory structure
            verifyDirectoryStructure();
            
            // Migrate music content
            migrateMusicContent();
            
            // Migrate story content
            migrateStoryContent();
            
            // Print migration summary
            printMigrationSummary();
            
        } catch (Exception e) {
            log.error("Migration failed: {}", e.getMessage(), e);
            throw new RuntimeException("Content library migration failed", e);
        }
    }

    /**
     * Verify that the required directory structure exists
     */
    private void verifyDirectoryStructure() {
        log.info("Verifying directory structure...");
        
        File baseDir = new File(BASE_PATH);
        if (!baseDir.exists()) {
            throw new RuntimeException("Base directory does not exist: " + BASE_PATH);
        }
        
        File musicDir = new File(MUSIC_PATH);
        if (!musicDir.exists()) {
            throw new RuntimeException("Music directory does not exist: " + MUSIC_PATH);
        }
        
        File storiesDir = new File(STORIES_PATH);
        if (!storiesDir.exists()) {
            throw new RuntimeException("Stories directory does not exist: " + STORIES_PATH);
        }
        
        log.info("Directory structure verified successfully");
    }

    /**
     * Migrate music content from JSON metadata files
     */
    private void migrateMusicContent() {
        log.info("Starting music content migration...");
        
        File musicDir = new File(MUSIC_PATH);
        File[] languageDirectories = musicDir.listFiles(File::isDirectory);
        
        if (languageDirectories == null || languageDirectories.length == 0) {
            log.warn("No music language directories found in: {}", MUSIC_PATH);
            return;
        }
        
        List<ContentLibraryDTO> allMusicContent = new ArrayList<>();
        
        for (File languageDir : languageDirectories) {
            String language = languageDir.getName();
            log.info("Processing music language: {}", language);
            
            try {
                List<ContentLibraryDTO> languageContent = processMusicLanguage(language, languageDir);
                allMusicContent.addAll(languageContent);
                stats.addProcessedLanguage(language, languageContent.size());
                
            } catch (Exception e) {
                log.error("Failed to process music language {}: {}", language, e.getMessage(), e);
                stats.addFailedLanguage(language, e.getMessage());
            }
        }
        
        // Batch insert music content
        if (!allMusicContent.isEmpty()) {
            batchInsertContent(allMusicContent, "music");
        }
        
        log.info("Completed music content migration. Processed {} items", allMusicContent.size());
    }

    /**
     * Process music content for a specific language
     */
    private List<ContentLibraryDTO> processMusicLanguage(String language, File languageDir) throws IOException {
        File metadataFile = new File(languageDir, "metadata.json");
        if (!metadataFile.exists()) {
            log.warn("No metadata.json found for language: {}", language);
            return new ArrayList<>();
        }
        
        String jsonContent = Files.readString(metadataFile.toPath());
        
        // Parse JSON content
        JsonObject jsonObject = JsonParser.parseString(jsonContent).getAsJsonObject();
        List<ContentLibraryDTO> contentList = new ArrayList<>();
        
        for (Map.Entry<String, JsonElement> entry : jsonObject.entrySet()) {
            String title = entry.getKey();
            JsonObject contentInfo = entry.getValue().getAsJsonObject();
            
            try {
                ContentLibraryDTO dto = createMusicContentDTO(title, contentInfo, language);
                contentList.add(dto);
                
            } catch (Exception e) {
                log.error("Failed to process music item '{}' in language {}: {}", title, language, e.getMessage());
                stats.addFailedItem(title, e.getMessage());
            }
        }
        
        return contentList;
    }

    /**
     * Create ContentLibraryDTO for music content
     */
    private ContentLibraryDTO createMusicContentDTO(String title, JsonObject contentInfo, String language) {
        ContentLibraryDTO dto = new ContentLibraryDTO();
        
        // Basic information
        dto.setTitle(title);
        dto.setRomanized(getJsonString(contentInfo, "romanized"));
        dto.setFilename(getJsonString(contentInfo, "filename"));
        dto.setContentType(ContentLibraryEntity.ContentType.MUSIC.getValue());
        dto.setCategory(language);
        
        // Parse alternatives array
        JsonArray alternativesArray = contentInfo.getAsJsonArray("alternatives");
        if (alternativesArray != null) {
            List<String> alternatives = new ArrayList<>();
            for (JsonElement element : alternativesArray) {
                alternatives.add(element.getAsString());
            }
            dto.setAlternatives(alternatives);
        } else {
            dto.setAlternatives(new ArrayList<>());
        }
        
        // Additional metadata (these might be null for now, can be populated later)
        dto.setAwsS3Url(getJsonString(contentInfo, "aws_s3_url"));
        dto.setDurationSeconds(getJsonInteger(contentInfo, "duration_seconds"));
        dto.setFileSizeBytes(getJsonLong(contentInfo, "file_size_bytes"));
        
        // Set as active
        dto.setIsActive(true);
        
        return dto;
    }

    /**
     * Migrate story content from JSON metadata files
     */
    private void migrateStoryContent() {
        log.info("Starting story content migration...");
        
        File storiesDir = new File(STORIES_PATH);
        File[] genreDirectories = storiesDir.listFiles(File::isDirectory);
        
        if (genreDirectories == null || genreDirectories.length == 0) {
            log.warn("No story genre directories found in: {}", STORIES_PATH);
            return;
        }
        
        List<ContentLibraryDTO> allStoryContent = new ArrayList<>();
        
        for (File genreDir : genreDirectories) {
            String genre = genreDir.getName();
            log.info("Processing story genre: {}", genre);
            
            try {
                List<ContentLibraryDTO> genreContent = processStoryGenre(genre, genreDir);
                allStoryContent.addAll(genreContent);
                stats.addProcessedGenre(genre, genreContent.size());
                
            } catch (Exception e) {
                log.error("Failed to process story genre {}: {}", genre, e.getMessage(), e);
                stats.addFailedGenre(genre, e.getMessage());
            }
        }
        
        // Batch insert story content
        if (!allStoryContent.isEmpty()) {
            batchInsertContent(allStoryContent, "stories");
        }
        
        log.info("Completed story content migration. Processed {} items", allStoryContent.size());
    }

    /**
     * Process story content for a specific genre
     */
    private List<ContentLibraryDTO> processStoryGenre(String genre, File genreDir) throws IOException {
        File metadataFile = new File(genreDir, "metadata.json");
        if (!metadataFile.exists()) {
            log.warn("No metadata.json found for genre: {}", genre);
            return new ArrayList<>();
        }
        
        String jsonContent = Files.readString(metadataFile.toPath());
        
        // Parse JSON content
        JsonObject jsonObject = JsonParser.parseString(jsonContent).getAsJsonObject();
        List<ContentLibraryDTO> contentList = new ArrayList<>();
        
        for (Map.Entry<String, JsonElement> entry : jsonObject.entrySet()) {
            String title = entry.getKey();
            JsonObject contentInfo = entry.getValue().getAsJsonObject();
            
            try {
                ContentLibraryDTO dto = createStoryContentDTO(title, contentInfo, genre);
                contentList.add(dto);
                
            } catch (Exception e) {
                log.error("Failed to process story item '{}' in genre {}: {}", title, genre, e.getMessage());
                stats.addFailedItem(title, e.getMessage());
            }
        }
        
        return contentList;
    }

    /**
     * Create ContentLibraryDTO for story content
     */
    private ContentLibraryDTO createStoryContentDTO(String title, JsonObject contentInfo, String genre) {
        ContentLibraryDTO dto = new ContentLibraryDTO();
        
        // Basic information
        dto.setTitle(title);
        dto.setRomanized(getJsonString(contentInfo, "romanized"));
        dto.setFilename(getJsonString(contentInfo, "filename"));
        dto.setContentType(ContentLibraryEntity.ContentType.STORY.getValue());
        dto.setCategory(genre);
        
        // Parse alternatives array
        JsonArray alternativesArray = contentInfo.getAsJsonArray("alternatives");
        if (alternativesArray != null) {
            List<String> alternatives = new ArrayList<>();
            for (JsonElement element : alternativesArray) {
                alternatives.add(element.getAsString());
            }
            dto.setAlternatives(alternatives);
        } else {
            dto.setAlternatives(new ArrayList<>());
        }
        
        // Additional metadata (these might be null for now, can be populated later)
        dto.setAwsS3Url(getJsonString(contentInfo, "aws_s3_url"));
        dto.setDurationSeconds(getJsonInteger(contentInfo, "duration_seconds"));
        dto.setFileSizeBytes(getJsonLong(contentInfo, "file_size_bytes"));
        
        // Set as active
        dto.setIsActive(true);
        
        return dto;
    }

    /**
     * Batch insert content into database
     */
    private void batchInsertContent(List<ContentLibraryDTO> contentList, String contentType) {
        log.info("Starting batch insert for {} {} items", contentList.size(), contentType);
        
        // Process in batches to avoid memory issues and improve performance
        List<List<ContentLibraryDTO>> batches = partition(contentList, BATCH_SIZE);
        
        int totalInserted = 0;
        for (int i = 0; i < batches.size(); i++) {
            List<ContentLibraryDTO> batch = batches.get(i);
            
            try {
                int inserted = contentLibraryService.batchInsertContent(batch);
                totalInserted += inserted;
                
                log.info("Batch {}/{} completed: {} items inserted", i + 1, batches.size(), inserted);
                stats.addInsertedCount(inserted);
                
                if (inserted != batch.size()) {
                    log.warn("Batch insert incomplete: expected {}, inserted {}", batch.size(), inserted);
                }
                
            } catch (Exception e) {
                log.error("Failed to insert batch {}/{}: {}", i + 1, batches.size(), e.getMessage(), e);
                stats.addFailedBatch(i + 1, e.getMessage());
            }
        }
        
        log.info("Batch insert completed for {}: {} total items inserted", contentType, totalInserted);
    }

    /**
     * Print migration summary
     */
    private void printMigrationSummary() {
        log.info("================== MIGRATION SUMMARY ==================");
        log.info("Total items processed: {}", stats.getTotalProcessed());
        log.info("Total items inserted: {}", stats.getTotalInserted());
        log.info("Total failed items: {}", stats.getTotalFailed());
        log.info("");
        
        log.info("MUSIC CONTENT:");
        for (String language : stats.getProcessedLanguages().keySet()) {
            log.info("  - {}: {} items", language, stats.getProcessedLanguages().get(language));
        }
        
        log.info("STORY CONTENT:");
        for (String genre : stats.getProcessedGenres().keySet()) {
            log.info("  - {}: {} items", genre, stats.getProcessedGenres().get(genre));
        }
        
        if (!stats.getFailedLanguages().isEmpty()) {
            log.error("FAILED LANGUAGES:");
            stats.getFailedLanguages().forEach((lang, error) -> 
                log.error("  - {}: {}", lang, error));
        }
        
        if (!stats.getFailedGenres().isEmpty()) {
            log.error("FAILED GENRES:");
            stats.getFailedGenres().forEach((genre, error) -> 
                log.error("  - {}: {}", genre, error));
        }
        
        if (!stats.getFailedItems().isEmpty()) {
            log.error("FAILED ITEMS (showing first 10):");
            stats.getFailedItems().entrySet().stream()
                .limit(10)
                .forEach(entry -> log.error("  - {}: {}", entry.getKey(), entry.getValue()));
        }
        
        if (!stats.getFailedBatches().isEmpty()) {
            log.error("FAILED BATCHES:");
            stats.getFailedBatches().forEach((batch, error) -> 
                log.error("  - Batch {}: {}", batch, error));
        }
        
        log.info("======================================================");
    }

    // Helper methods
    
    /**
     * Safely get string value from JSON object
     */
    private String getJsonString(JsonObject jsonObject, String key) {
        JsonElement element = jsonObject.get(key);
        return (element != null && !element.isJsonNull()) ? element.getAsString() : null;
    }
    
    /**
     * Safely get integer value from JSON object
     */
    private Integer getJsonInteger(JsonObject jsonObject, String key) {
        JsonElement element = jsonObject.get(key);
        return (element != null && !element.isJsonNull()) ? element.getAsInt() : null;
    }
    
    /**
     * Safely get long value from JSON object
     */
    private Long getJsonLong(JsonObject jsonObject, String key) {
        JsonElement element = jsonObject.get(key);
        return (element != null && !element.isJsonNull()) ? element.getAsLong() : null;
    }
    
    /**
     * Partition list into smaller batches
     */
    private <T> List<List<T>> partition(List<T> list, int size) {
        List<List<T>> partitions = new ArrayList<>();
        for (int i = 0; i < list.size(); i += size) {
            partitions.add(list.subList(i, Math.min(i + size, list.size())));
        }
        return partitions;
    }

    /**
     * Migration statistics tracker
     */
    private static class MigrationStatistics {
        private final Map<String, Integer> processedLanguages = new HashMap<>();
        private final Map<String, Integer> processedGenres = new HashMap<>();
        private final Map<String, String> failedLanguages = new HashMap<>();
        private final Map<String, String> failedGenres = new HashMap<>();
        private final Map<String, String> failedItems = new HashMap<>();
        private final Map<Integer, String> failedBatches = new HashMap<>();
        private int totalInserted = 0;
        
        public void addProcessedLanguage(String language, int count) {
            processedLanguages.put(language, count);
        }
        
        public void addProcessedGenre(String genre, int count) {
            processedGenres.put(genre, count);
        }
        
        public void addFailedLanguage(String language, String error) {
            failedLanguages.put(language, error);
        }
        
        public void addFailedGenre(String genre, String error) {
            failedGenres.put(genre, error);
        }
        
        public void addFailedItem(String item, String error) {
            failedItems.put(item, error);
        }
        
        public void addFailedBatch(int batchNumber, String error) {
            failedBatches.put(batchNumber, error);
        }
        
        public void addInsertedCount(int count) {
            totalInserted += count;
        }
        
        public int getTotalProcessed() {
            return processedLanguages.values().stream().mapToInt(Integer::intValue).sum() +
                   processedGenres.values().stream().mapToInt(Integer::intValue).sum();
        }
        
        public int getTotalFailed() {
            return failedItems.size();
        }
        
        // Getters
        public Map<String, Integer> getProcessedLanguages() { return processedLanguages; }
        public Map<String, Integer> getProcessedGenres() { return processedGenres; }
        public Map<String, String> getFailedLanguages() { return failedLanguages; }
        public Map<String, String> getFailedGenres() { return failedGenres; }
        public Map<String, String> getFailedItems() { return failedItems; }
        public Map<Integer, String> getFailedBatches() { return failedBatches; }
        public int getTotalInserted() { return totalInserted; }
    }
}