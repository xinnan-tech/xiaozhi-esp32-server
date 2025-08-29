package xiaozhi.migration;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;
import org.springframework.context.annotation.Profile;

import xiaozhi.modules.content.service.ContentLibraryService;
import xiaozhi.modules.content.dto.ContentSearchDTO;
import xiaozhi.common.page.PageData;
import xiaozhi.modules.content.dto.ContentLibraryDTO;

import java.util.List;
import java.util.Map;
import java.util.HashMap;

/**
 * Migration Validator
 * 
 * This component validates the migrated content library data to ensure
 * the migration was successful and data integrity is maintained.
 * 
 * Run with: java -jar app.jar --spring.profiles.active=validation
 * 
 * @author Migration Validator
 * @version 1.0
 */
@Slf4j
@Component
@Profile("validation")
public class MigrationValidator implements CommandLineRunner {

    @Autowired
    private ContentLibraryService contentLibraryService;

    @Override
    public void run(String... args) throws Exception {
        log.info("=======================================================");
        log.info("Content Library Migration Validation");
        log.info("=======================================================");
        
        try {
            // Validate content statistics
            validateContentStatistics();
            
            // Validate content categories
            validateCategories();
            
            // Validate sample content
            validateSampleContent();
            
            // Validate search functionality
            validateSearchFunctionality();
            
            log.info("=======================================================");
            log.info("Migration Validation COMPLETED SUCCESSFULLY");
            log.info("=======================================================");
            
        } catch (Exception e) {
            log.error("Migration validation failed: {}", e.getMessage(), e);
            throw e;
        }
    }

    /**
     * Validate content statistics
     */
    private void validateContentStatistics() {
        log.info("Validating content statistics...");
        
        Object statsObj = contentLibraryService.getContentStatistics();
        if (!(statsObj instanceof Map)) {
            throw new RuntimeException("Invalid statistics format returned");
        }
        
        @SuppressWarnings("unchecked")
        Map<String, Object> stats = (Map<String, Object>) statsObj;
        
        Integer totalMusic = (Integer) stats.get("totalMusic");
        Integer totalStories = (Integer) stats.get("totalStories");
        Integer totalContent = (Integer) stats.get("totalContent");
        
        log.info("Content Statistics:");
        log.info("  - Total Music: {}", totalMusic != null ? totalMusic : 0);
        log.info("  - Total Stories: {}", totalStories != null ? totalStories : 0);
        log.info("  - Total Content: {}", totalContent != null ? totalContent : 0);
        
        if (totalContent == null || totalContent == 0) {
            throw new RuntimeException("No content found in database - migration may have failed");
        }
        
        if (totalMusic == null) totalMusic = 0;
        if (totalStories == null) totalStories = 0;
        
        if (!totalContent.equals(totalMusic + totalStories)) {
            throw new RuntimeException("Content count mismatch: total=" + totalContent + 
                    ", music=" + totalMusic + ", stories=" + totalStories);
        }
        
        log.info("✓ Content statistics validation passed");
    }

    /**
     * Validate content categories
     */
    private void validateCategories() {
        log.info("Validating content categories...");
        
        // Expected categories based on migration script
        String[] expectedMusicLanguages = {"English", "Hindi", "Kannada", "Phonics", "Telugu"};
        String[] expectedStoryGenres = {"Adventure", "Bedtime", "Educational", "Fairy Tales", "Fantasy"};
        
        // Get music categories
        List<String> musicCategories = contentLibraryService.getCategoriesByType("music");
        log.info("Found music categories: {}", musicCategories);
        
        // Get story categories
        List<String> storyCategories = contentLibraryService.getCategoriesByType("story");
        log.info("Found story categories: {}", storyCategories);
        
        // Validate music categories
        for (String expectedLang : expectedMusicLanguages) {
            if (!musicCategories.contains(expectedLang)) {
                log.warn("Expected music language '{}' not found", expectedLang);
            } else {
                log.info("✓ Music language '{}' found", expectedLang);
            }
        }
        
        // Validate story categories
        for (String expectedGenre : expectedStoryGenres) {
            if (!storyCategories.contains(expectedGenre)) {
                log.warn("Expected story genre '{}' not found", expectedGenre);
            } else {
                log.info("✓ Story genre '{}' found", expectedGenre);
            }
        }
        
        log.info("✓ Categories validation completed");
    }

    /**
     * Validate sample content
     */
    private void validateSampleContent() {
        log.info("Validating sample content...");
        
        // Test music content
        ContentSearchDTO musicSearch = new ContentSearchDTO();
        musicSearch.setContentType("music");
        musicSearch.setLimit(5);
        
        PageData<ContentLibraryDTO> musicResults = contentLibraryService.getContentList(musicSearch);
        
        if (musicResults.getList() == null || musicResults.getList().isEmpty()) {
            log.warn("No music content found");
        } else {
            log.info("Sample music content ({} items):", musicResults.getList().size());
            for (ContentLibraryDTO content : musicResults.getList()) {
                log.info("  - {} [{}] ({})", content.getTitle(), content.getCategory(), 
                        content.getFilename());
                validateContentItem(content, "music");
            }
        }
        
        // Test story content
        ContentSearchDTO storySearch = new ContentSearchDTO();
        storySearch.setContentType("story");
        storySearch.setLimit(5);
        
        PageData<ContentLibraryDTO> storyResults = contentLibraryService.getContentList(storySearch);
        
        if (storyResults.getList() == null || storyResults.getList().isEmpty()) {
            log.warn("No story content found");
        } else {
            log.info("Sample story content ({} items):", storyResults.getList().size());
            for (ContentLibraryDTO content : storyResults.getList()) {
                log.info("  - {} [{}] ({})", content.getTitle(), content.getCategory(), 
                        content.getFilename());
                validateContentItem(content, "story");
            }
        }
        
        log.info("✓ Sample content validation completed");
    }

    /**
     * Validate individual content item
     */
    private void validateContentItem(ContentLibraryDTO content, String expectedType) {
        if (content.getId() == null || content.getId().isEmpty()) {
            throw new RuntimeException("Content item missing ID: " + content.getTitle());
        }
        
        if (content.getTitle() == null || content.getTitle().isEmpty()) {
            throw new RuntimeException("Content item missing title: " + content.getId());
        }
        
        if (!expectedType.equals(content.getContentType())) {
            throw new RuntimeException("Content type mismatch for " + content.getTitle() + 
                    ": expected " + expectedType + ", got " + content.getContentType());
        }
        
        if (content.getCategory() == null || content.getCategory().isEmpty()) {
            throw new RuntimeException("Content item missing category: " + content.getTitle());
        }
        
        if (content.getAlternatives() == null) {
            log.warn("Content item missing alternatives: {}", content.getTitle());
        }
        
        if (content.getIsActive() == null || !content.getIsActive()) {
            log.warn("Content item not active: {}", content.getTitle());
        }
    }

    /**
     * Validate search functionality
     */
    private void validateSearchFunctionality() {
        log.info("Validating search functionality...");
        
        // Test basic search
        ContentSearchDTO searchDTO = new ContentSearchDTO();
        searchDTO.setQuery("baby");
        searchDTO.setLimit(10);
        
        PageData<ContentLibraryDTO> searchResults = contentLibraryService.searchContent(searchDTO);
        
        if (searchResults.getList() == null) {
            log.warn("Search returned null results");
        } else {
            log.info("Search for 'baby' returned {} results", searchResults.getList().size());
            
            if (!searchResults.getList().isEmpty()) {
                for (ContentLibraryDTO result : searchResults.getList()) {
                    String title = result.getTitle().toLowerCase();
                    List<String> alternatives = result.getAlternatives();
                    
                    boolean containsBaby = title.contains("baby");
                    if (!containsBaby && alternatives != null) {
                        containsBaby = alternatives.stream()
                                .anyMatch(alt -> alt.toLowerCase().contains("baby"));
                    }
                    
                    if (containsBaby) {
                        log.info("✓ Search result matches: {}", result.getTitle());
                    } else {
                        log.warn("Search result may not match query: {}", result.getTitle());
                    }
                }
            }
        }
        
        // Test category filtering
        ContentSearchDTO categorySearch = new ContentSearchDTO();
        categorySearch.setContentType("music");
        categorySearch.setCategory("English");
        categorySearch.setLimit(5);
        
        PageData<ContentLibraryDTO> categoryResults = contentLibraryService.getContentList(categorySearch);
        
        if (categoryResults.getList() == null || categoryResults.getList().isEmpty()) {
            log.warn("No English music content found");
        } else {
            log.info("Found {} English music items", categoryResults.getList().size());
            
            for (ContentLibraryDTO result : categoryResults.getList()) {
                if (!"music".equals(result.getContentType())) {
                    throw new RuntimeException("Category search returned wrong content type: " + 
                            result.getContentType());
                }
                if (!"English".equals(result.getCategory())) {
                    throw new RuntimeException("Category search returned wrong category: " + 
                            result.getCategory());
                }
            }
            log.info("✓ Category filtering works correctly");
        }
        
        log.info("✓ Search functionality validation completed");
    }
}