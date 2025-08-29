package xiaozhi.modules.content.controller;

import java.util.List;

import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import xiaozhi.common.page.PageData;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.content.dto.ContentLibraryDTO;
import xiaozhi.modules.content.dto.ContentSearchDTO;
import xiaozhi.modules.content.service.ContentLibraryService;

/**
 * Content Library REST API Controller
 * Handles music and story content operations
 */
@RestController
@RequestMapping("/content/library")
@AllArgsConstructor
@Tag(name = "Content Library", description = "Music and Story Content Management")
public class ContentLibraryController {

    private final ContentLibraryService contentLibraryService;

    @GetMapping
    @Operation(summary = "Get content list with filters and pagination", description = "Retrieves paginated content with optional filters")
    public Result<PageData<ContentLibraryDTO>> getContentList(
            @Parameter(description = "Search query") @RequestParam(required = false) String query,
            @Parameter(description = "Content type filter") @RequestParam(required = false) String contentType,
            @Parameter(description = "Category filter") @RequestParam(required = false) String category,
            @Parameter(description = "Page number (1-based)") @RequestParam(defaultValue = "1") Integer page,
            @Parameter(description = "Items per page") @RequestParam(defaultValue = "20") Integer limit,
            @Parameter(description = "Sort field") @RequestParam(defaultValue = "created_at") String sortBy,
            @Parameter(description = "Sort direction") @RequestParam(defaultValue = "desc") String sortDirection) {
        
        ContentSearchDTO searchDTO = new ContentSearchDTO();
        searchDTO.setQuery(query);
        searchDTO.setContentType(contentType);
        searchDTO.setCategory(category);
        searchDTO.setPage(page);
        searchDTO.setLimit(limit);
        searchDTO.setSortBy(sortBy);
        searchDTO.setSortDirection(sortDirection);
        
        PageData<ContentLibraryDTO> result = contentLibraryService.getContentList(searchDTO);
        return new Result<PageData<ContentLibraryDTO>>().ok(result);
    }

    @GetMapping("/search")
    @Operation(summary = "Search content", description = "Full-text search across content titles and alternatives")
    public Result<PageData<ContentLibraryDTO>> searchContent(
            @Parameter(description = "Search query", required = true) @RequestParam String query,
            @Parameter(description = "Content type filter") @RequestParam(required = false) String contentType,
            @Parameter(description = "Page number (1-based)") @RequestParam(defaultValue = "1") Integer page,
            @Parameter(description = "Items per page") @RequestParam(defaultValue = "20") Integer limit) {
        
        ContentSearchDTO searchDTO = new ContentSearchDTO();
        searchDTO.setQuery(query);
        searchDTO.setContentType(contentType);
        searchDTO.setPage(page);
        searchDTO.setLimit(limit);
        
        PageData<ContentLibraryDTO> result = contentLibraryService.searchContent(searchDTO);
        return new Result<PageData<ContentLibraryDTO>>().ok(result);
    }

    @GetMapping("/categories")
    @Operation(summary = "Get categories by content type", description = "Retrieves available categories for music or stories")
    public Result<List<String>> getCategories(
            @Parameter(description = "Content type (music or story)", required = true) @RequestParam String contentType) {
        
        List<String> categories = contentLibraryService.getCategoriesByType(contentType);
        return new Result<List<String>>().ok(categories);
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get content by ID", description = "Retrieves detailed content information")
    public Result<ContentLibraryDTO> getContentById(
            @Parameter(description = "Content ID", required = true) @PathVariable String id) {
        
        ContentLibraryDTO content = contentLibraryService.getContentById(id);
        if (content == null) {
            return new Result<ContentLibraryDTO>().error("Content not found");
        }
        return new Result<ContentLibraryDTO>().ok(content);
    }

    @GetMapping("/statistics")
    @Operation(summary = "Get content statistics", description = "Retrieves content counts and category statistics")
    public Result<Object> getStatistics() {
        Object stats = contentLibraryService.getContentStatistics();
        return new Result<Object>().ok(stats);
    }

    @PostMapping
    @Operation(summary = "Add new content", description = "Creates new content item (admin operation)")
    public Result<String> addContent(@RequestBody ContentLibraryDTO contentDTO) {
        String contentId = contentLibraryService.addContent(contentDTO);
        if (contentId == null) {
            return new Result<String>().error("Failed to create content");
        }
        return new Result<String>().ok(contentId);
    }

    @PutMapping("/{id}")
    @Operation(summary = "Update content", description = "Updates existing content item")
    public Result<Boolean> updateContent(
            @Parameter(description = "Content ID", required = true) @PathVariable String id,
            @RequestBody ContentLibraryDTO contentDTO) {
        
        boolean success = contentLibraryService.updateContent(id, contentDTO);
        if (!success) {
            return new Result<Boolean>().error("Failed to update content");
        }
        return new Result<Boolean>().ok(true);
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Delete content", description = "Soft deletes content item (sets inactive)")
    public Result<Boolean> deleteContent(
            @Parameter(description = "Content ID", required = true) @PathVariable String id) {
        
        boolean success = contentLibraryService.deleteContent(id);
        if (!success) {
            return new Result<Boolean>().error("Failed to delete content");
        }
        return new Result<Boolean>().ok(true);
    }

    @PostMapping("/batch")
    @Operation(summary = "Batch insert content", description = "Bulk creates content items (data migration)")
    public Result<Integer> batchInsertContent(@RequestBody List<ContentLibraryDTO> contentList) {
        int insertedCount = contentLibraryService.batchInsertContent(contentList);
        return new Result<Integer>().ok(insertedCount);
    }

    @PostMapping("/sync")
    @Operation(summary = "Sync from metadata", description = "Synchronizes content from JSON metadata files")
    public Result<String> syncFromMetadata() {
        String result = contentLibraryService.syncContentFromMetadata();
        return new Result<String>().ok(result);
    }
}