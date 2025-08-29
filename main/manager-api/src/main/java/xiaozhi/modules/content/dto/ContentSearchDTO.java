package xiaozhi.modules.content.dto;

import java.io.Serializable;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * Content Search Data Transfer Object
 * Used for content search and filtering requests
 */
@Data
@Schema(description = "Content Search Parameters")
public class ContentSearchDTO implements Serializable {
    private static final long serialVersionUID = 1L;

    @Schema(description = "Search query string", example = "baby shark")
    private String query;

    @Schema(description = "Content type filter", example = "music", allowableValues = {"music", "story", ""})
    private String contentType;

    @Schema(description = "Category filter", example = "English")
    private String category;

    @Schema(description = "Page number (1-based)", example = "1")
    private Integer page = 1;

    @Schema(description = "Number of items per page", example = "20")
    private Integer limit = 20;

    @Schema(description = "Sort field", example = "title", allowableValues = {"title", "category", "created_at"})
    private String sortBy = "created_at";

    @Schema(description = "Sort direction", example = "desc", allowableValues = {"asc", "desc"})
    private String sortDirection = "desc";

    /**
     * Get calculated offset for pagination
     */
    public int getOffset() {
        return (page - 1) * limit;
    }

    /**
     * Validate and set defaults for pagination
     */
    public void validateAndSetDefaults() {
        if (page == null || page < 1) {
            page = 1;
        }
        if (limit == null || limit < 1) {
            limit = 20;
        }
        if (limit > 100) {
            limit = 100; // Maximum limit to prevent abuse
        }
        if (sortBy == null || sortBy.trim().isEmpty()) {
            sortBy = "created_at";
        }
        if (sortDirection == null || (!sortDirection.equals("asc") && !sortDirection.equals("desc"))) {
            sortDirection = "desc";
        }
    }

    /**
     * Check if this is a search request (has query)
     */
    public boolean isSearchRequest() {
        return query != null && !query.trim().isEmpty();
    }

    /**
     * Check if content type filter is applied
     */
    public boolean hasContentTypeFilter() {
        return contentType != null && !contentType.trim().isEmpty();
    }

    /**
     * Check if category filter is applied
     */
    public boolean hasCategoryFilter() {
        return category != null && !category.trim().isEmpty();
    }
}