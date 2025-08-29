package xiaozhi.modules.content.service.impl;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

import org.springframework.stereotype.Service;

import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;

import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.page.PageData;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.modules.content.dao.ContentLibraryDao;
import xiaozhi.modules.content.dto.ContentLibraryDTO;
import xiaozhi.modules.content.dto.ContentSearchDTO;
import xiaozhi.modules.content.entity.ContentLibraryEntity;
import xiaozhi.modules.content.service.ContentLibraryService;

/**
 * Content Library Service Implementation
 */
@Service
@AllArgsConstructor
@Slf4j
public class ContentLibraryServiceImpl implements ContentLibraryService {

    private final ContentLibraryDao contentLibraryDao;
    private final Gson gson;

    @Override
    public PageData<ContentLibraryDTO> getContentList(ContentSearchDTO searchDTO) {
        searchDTO.validateAndSetDefaults();
        
        // Build query parameters
        Map<String, Object> params = new HashMap<>();
        params.put("contentType", searchDTO.getContentType());
        params.put("category", searchDTO.getCategory());
        params.put("search", searchDTO.getQuery());
        params.put("offset", searchDTO.getOffset());
        params.put("limit", searchDTO.getLimit());

        // Get content list and total count
        List<ContentLibraryEntity> entities = contentLibraryDao.getContentList(params);
        int total = contentLibraryDao.getContentCount(params);

        // Convert to DTOs
        List<ContentLibraryDTO> dtoList = entities.stream()
                .map(this::convertToDTO)
                .collect(Collectors.toList());

        // Create paginated result
        return new PageData<>(dtoList, total);
    }

    @Override
    public List<String> getCategoriesByType(String contentType) {
        if (contentType == null || contentType.trim().isEmpty()) {
            throw new IllegalArgumentException("Content type cannot be empty");
        }
        return contentLibraryDao.getCategoriesByType(contentType);
    }

    @Override
    public PageData<ContentLibraryDTO> searchContent(ContentSearchDTO searchDTO) {
        searchDTO.validateAndSetDefaults();
        
        if (!searchDTO.isSearchRequest()) {
            // If no search query, return regular content list
            return getContentList(searchDTO);
        }

        // Build search parameters
        Map<String, Object> params = new HashMap<>();
        params.put("query", searchDTO.getQuery().trim());
        params.put("contentType", searchDTO.getContentType());
        params.put("offset", searchDTO.getOffset());
        params.put("limit", searchDTO.getLimit());

        // Get search results and total count
        List<ContentLibraryEntity> entities = contentLibraryDao.searchContent(params);
        int total = contentLibraryDao.getSearchCount(params);

        // Convert to DTOs
        List<ContentLibraryDTO> dtoList = entities.stream()
                .map(this::convertToDTO)
                .collect(Collectors.toList());

        // Create paginated result
        return new PageData<>(dtoList, total);
    }

    @Override
    public ContentLibraryDTO getContentById(String id) {
        ContentLibraryEntity entity = contentLibraryDao.selectById(id);
        return entity != null ? convertToDTO(entity) : null;
    }

    @Override
    public String addContent(ContentLibraryDTO contentDTO) {
        ContentLibraryEntity entity = convertToEntity(contentDTO);
        entity.setId(UUID.randomUUID().toString());
        entity.setIsActive(1);
        
        int result = contentLibraryDao.insert(entity);
        return result > 0 ? entity.getId() : null;
    }

    @Override
    public boolean updateContent(String id, ContentLibraryDTO contentDTO) {
        ContentLibraryEntity entity = convertToEntity(contentDTO);
        entity.setId(id);
        
        int result = contentLibraryDao.updateById(entity);
        return result > 0;
    }

    @Override
    public boolean deleteContent(String id) {
        ContentLibraryEntity entity = new ContentLibraryEntity();
        entity.setId(id);
        entity.setIsActive(0);
        
        int result = contentLibraryDao.updateById(entity);
        return result > 0;
    }

    @Override
    public int batchInsertContent(List<ContentLibraryDTO> contentList) {
        if (contentList == null || contentList.isEmpty()) {
            return 0;
        }

        List<ContentLibraryEntity> entities = contentList.stream()
                .map(dto -> {
                    ContentLibraryEntity entity = convertToEntity(dto);
                    entity.setId(UUID.randomUUID().toString());
                    entity.setIsActive(1);
                    return entity;
                })
                .collect(Collectors.toList());

        return contentLibraryDao.batchInsert(entities);
    }

    @Override
    public String syncContentFromMetadata() {
        // TODO: Implement metadata sync from JSON files
        // This would parse the music/*.json and stories/*.json files
        // and populate the database
        log.info("Sync from metadata files - TODO: Implement");
        return "Sync functionality not yet implemented";
    }

    @Override
    public Object getContentStatistics() {
        Map<String, Object> stats = new HashMap<>();
        
        // Get counts by content type
        Map<String, Object> musicParams = new HashMap<>();
        musicParams.put("contentType", "music");
        int musicCount = contentLibraryDao.getContentCount(musicParams);
        
        Map<String, Object> storyParams = new HashMap<>();
        storyParams.put("contentType", "story");
        int storyCount = contentLibraryDao.getContentCount(storyParams);
        
        stats.put("totalMusic", musicCount);
        stats.put("totalStories", storyCount);
        stats.put("totalContent", musicCount + storyCount);
        
        // Get categories
        List<String> musicCategories = getCategoriesByType("music");
        List<String> storyCategories = getCategoriesByType("story");
        
        stats.put("musicCategories", musicCategories);
        stats.put("storyCategories", storyCategories);
        
        return stats;
    }

    /**
     * Convert Entity to DTO
     */
    private ContentLibraryDTO convertToDTO(ContentLibraryEntity entity) {
        ContentLibraryDTO dto = ConvertUtils.sourceToTarget(entity, ContentLibraryDTO.class);
        
        // Convert alternatives JSON string to List
        if (entity.getAlternatives() != null && !entity.getAlternatives().trim().isEmpty()) {
            try {
                List<String> alternatives = gson.fromJson(entity.getAlternatives(), 
                        new TypeToken<List<String>>(){}.getType());
                dto.setAlternatives(alternatives);
            } catch (Exception e) {
                log.warn("Failed to parse alternatives JSON for content {}: {}", entity.getId(), e.getMessage());
                dto.setAlternatives(List.of());
            }
        } else {
            dto.setAlternatives(List.of());
        }
        
        // Set calculated fields
        dto.setIsActive(entity.getIsActive() == 1);
        dto.setFormattedDuration(dto.getFormattedDuration());
        dto.setFormattedFileSize(dto.getFormattedFileSize());
        
        return dto;
    }

    /**
     * Convert DTO to Entity
     */
    private ContentLibraryEntity convertToEntity(ContentLibraryDTO dto) {
        ContentLibraryEntity entity = ConvertUtils.sourceToTarget(dto, ContentLibraryEntity.class);
        
        // Convert alternatives List to JSON string
        if (dto.getAlternatives() != null && !dto.getAlternatives().isEmpty()) {
            entity.setAlternatives(gson.toJson(dto.getAlternatives()));
        }
        
        // Set active status
        entity.setIsActive(dto.getIsActive() != null && dto.getIsActive() ? 1 : 0);
        
        return entity;
    }
}