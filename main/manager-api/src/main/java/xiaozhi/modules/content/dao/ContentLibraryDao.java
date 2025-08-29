package xiaozhi.modules.content.dao;

import java.util.List;
import java.util.Map;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import xiaozhi.modules.content.entity.ContentLibraryEntity;

/**
 * Content Library Data Access Object
 * Handles database operations for content library
 */
@Mapper
public interface ContentLibraryDao extends BaseMapper<ContentLibraryEntity> {

    /**
     * Get paginated content list with filters
     * @param params Query parameters including page, limit, contentType, category, search
     * @return List of content items
     */
    List<ContentLibraryEntity> getContentList(Map<String, Object> params);

    /**
     * Get total count for pagination
     * @param params Query parameters for filtering
     * @return Total count
     */
    int getContentCount(Map<String, Object> params);

    /**
     * Get distinct categories by content type
     * @param contentType music or story
     * @return List of category names
     */
    List<String> getCategoriesByType(@Param("contentType") String contentType);

    /**
     * Search content by title or alternatives
     * @param params Search parameters including query, contentType, offset, limit
     * @return List of matching content items
     */
    List<ContentLibraryEntity> searchContent(Map<String, Object> params);

    /**
     * Get search results count
     * @param params Search parameters including query, contentType
     * @return Total search results count
     */
    int getSearchCount(Map<String, Object> params);

    /**
     * Batch insert content items (for data migration)
     * @param contentList List of content items to insert
     * @return Number of inserted records
     */
    int batchInsert(@Param("list") List<ContentLibraryEntity> contentList);

    /**
     * Check if content exists by filename
     * @param filename Original filename to check
     * @return Content entity if exists, null otherwise
     */
    ContentLibraryEntity findByFilename(@Param("filename") String filename);
}