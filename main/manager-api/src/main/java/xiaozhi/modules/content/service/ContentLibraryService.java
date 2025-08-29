package xiaozhi.modules.content.service;

import java.util.List;

import xiaozhi.common.page.PageData;
import xiaozhi.modules.content.dto.ContentLibraryDTO;
import xiaozhi.modules.content.dto.ContentSearchDTO;
import xiaozhi.modules.content.entity.ContentLibraryEntity;

/**
 * Content Library Service Interface
 * Handles business logic for content library operations
 */
public interface ContentLibraryService {

    /**
     * Get paginated content list with filters and search
     * @param searchDTO Search and filter parameters
     * @return Paginated content data
     */
    PageData<ContentLibraryDTO> getContentList(ContentSearchDTO searchDTO);

    /**
     * Get all available categories for a content type
     * @param contentType music or story
     * @return List of category names
     */
    List<String> getCategoriesByType(String contentType);

    /**
     * Search content by query string
     * @param searchDTO Search parameters
     * @return Paginated search results
     */
    PageData<ContentLibraryDTO> searchContent(ContentSearchDTO searchDTO);

    /**
     * Get content by ID
     * @param id Content ID
     * @return Content details or null if not found
     */
    ContentLibraryDTO getContentById(String id);

    /**
     * Add new content item (for admin/sync operations)
     * @param contentDTO Content data to add
     * @return Created content ID
     */
    String addContent(ContentLibraryDTO contentDTO);

    /**
     * Update content item
     * @param id Content ID
     * @param contentDTO Updated content data
     * @return Success status
     */
    boolean updateContent(String id, ContentLibraryDTO contentDTO);

    /**
     * Soft delete content (set inactive)
     * @param id Content ID
     * @return Success status
     */
    boolean deleteContent(String id);

    /**
     * Batch insert content items (for data migration)
     * @param contentList List of content items
     * @return Number of successfully inserted items
     */
    int batchInsertContent(List<ContentLibraryDTO> contentList);

    /**
     * Sync content from metadata files (for admin operations)
     * @return Sync result summary
     */
    String syncContentFromMetadata();

    /**
     * Get content statistics
     * @return Statistics including total counts by type and category
     */
    Object getContentStatistics();
}