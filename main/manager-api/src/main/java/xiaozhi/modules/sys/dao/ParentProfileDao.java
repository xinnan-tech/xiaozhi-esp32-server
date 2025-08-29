package xiaozhi.modules.sys.dao;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.sys.entity.ParentProfileEntity;

/**
 * Parent Profile DAO
 */
@Mapper
public interface ParentProfileDao extends BaseDao<ParentProfileEntity> {
    
    /**
     * Get parent profile by user ID
     * @param userId User ID
     * @return Parent profile entity
     */
    ParentProfileEntity getByUserId(@Param("userId") Long userId);
    
    /**
     * Get parent profile by Supabase user ID
     * @param supabaseUserId Supabase user ID
     * @return Parent profile entity
     */
    ParentProfileEntity getBySupabaseUserId(@Param("supabaseUserId") String supabaseUserId);
    
    /**
     * Update terms acceptance
     * @param userId User ID
     * @param termsAcceptedAt Terms accepted timestamp
     * @param privacyPolicyAcceptedAt Privacy policy accepted timestamp
     * @return Number of affected rows
     */
    int updateTermsAcceptance(@Param("userId") Long userId, 
                             @Param("termsAcceptedAt") java.util.Date termsAcceptedAt, 
                             @Param("privacyPolicyAcceptedAt") java.util.Date privacyPolicyAcceptedAt);
    
    /**
     * Update onboarding completion status
     * @param userId User ID
     * @param onboardingCompleted Onboarding completed status
     * @return Number of affected rows
     */
    int updateOnboardingStatus(@Param("userId") Long userId, 
                              @Param("onboardingCompleted") Boolean onboardingCompleted);
}