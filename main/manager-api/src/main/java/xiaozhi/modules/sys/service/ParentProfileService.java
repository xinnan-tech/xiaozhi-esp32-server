package xiaozhi.modules.sys.service;

import xiaozhi.common.service.CrudService;
import xiaozhi.modules.sys.dto.ParentProfileDTO;
import xiaozhi.modules.sys.dto.ParentProfileCreateDTO;
import xiaozhi.modules.sys.dto.ParentProfileUpdateDTO;
import xiaozhi.modules.sys.dto.ParentProfileAcceptTermsDTO;
import xiaozhi.modules.sys.entity.ParentProfileEntity;

/**
 * Parent Profile Service
 */
public interface ParentProfileService extends CrudService<ParentProfileEntity, ParentProfileDTO> {
    
    /**
     * Get parent profile by user ID
     * @param userId User ID
     * @return Parent profile DTO
     */
    ParentProfileDTO getByUserId(Long userId);
    
    /**
     * Get parent profile by Supabase user ID
     * @param supabaseUserId Supabase user ID
     * @return Parent profile DTO
     */
    ParentProfileDTO getBySupabaseUserId(String supabaseUserId);
    
    /**
     * Create parent profile
     * @param dto Create DTO
     * @param userId User ID
     * @return Created parent profile DTO
     */
    ParentProfileDTO createProfile(ParentProfileCreateDTO dto, Long userId);
    
    /**
     * Update parent profile
     * @param dto Update DTO
     * @param userId User ID
     * @return Updated parent profile DTO
     */
    ParentProfileDTO updateProfile(ParentProfileUpdateDTO dto, Long userId);
    
    /**
     * Accept terms and privacy policy
     * @param dto Accept terms DTO
     * @param userId User ID
     * @return Success status
     */
    boolean acceptTerms(ParentProfileAcceptTermsDTO dto, Long userId);
    
    /**
     * Complete onboarding
     * @param userId User ID
     * @return Success status
     */
    boolean completeOnboarding(Long userId);
    
    /**
     * Check if parent profile exists for user
     * @param userId User ID
     * @return True if profile exists
     */
    boolean hasParentProfile(Long userId);
    
    /**
     * Delete parent profile by user ID
     * @param userId User ID
     * @return Success status
     */
    boolean deleteByUserId(Long userId);
}