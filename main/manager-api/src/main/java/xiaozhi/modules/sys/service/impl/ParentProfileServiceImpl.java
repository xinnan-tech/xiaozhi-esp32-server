package xiaozhi.modules.sys.service.impl;

import java.util.Date;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;

import lombok.AllArgsConstructor;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.service.impl.CrudServiceImpl;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.modules.sys.dao.ParentProfileDao;
import xiaozhi.modules.sys.dto.ParentProfileDTO;
import xiaozhi.modules.sys.dto.ParentProfileCreateDTO;
import xiaozhi.modules.sys.dto.ParentProfileUpdateDTO;
import xiaozhi.modules.sys.dto.ParentProfileAcceptTermsDTO;
import xiaozhi.modules.sys.entity.ParentProfileEntity;
import xiaozhi.modules.sys.service.ParentProfileService;

/**
 * Parent Profile Service Implementation
 */
@AllArgsConstructor
@Service
public class ParentProfileServiceImpl extends CrudServiceImpl<ParentProfileDao, ParentProfileEntity, ParentProfileDTO> 
        implements ParentProfileService {
    
    private final ParentProfileDao parentProfileDao;
    
    @Override
    public QueryWrapper<ParentProfileEntity> getWrapper(Map<String, Object> params) {
        QueryWrapper<ParentProfileEntity> wrapper = new QueryWrapper<>();
        // Add any filtering logic based on params if needed
        return wrapper;
    }

    @Override
    public ParentProfileDTO getByUserId(Long userId) {
        ParentProfileEntity entity = parentProfileDao.getByUserId(userId);
        return ConvertUtils.sourceToTarget(entity, ParentProfileDTO.class);
    }

    @Override
    public ParentProfileDTO getBySupabaseUserId(String supabaseUserId) {
        if (StringUtils.isBlank(supabaseUserId)) {
            return null;
        }
        ParentProfileEntity entity = parentProfileDao.getBySupabaseUserId(supabaseUserId);
        return ConvertUtils.sourceToTarget(entity, ParentProfileDTO.class);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public ParentProfileDTO createProfile(ParentProfileCreateDTO dto, Long userId) {
        // Check if profile already exists
        if (hasParentProfile(userId)) {
            throw new RenException("Parent profile already exists for this user");
        }
        
        // Convert DTO to Entity
        ParentProfileEntity entity = ConvertUtils.sourceToTarget(dto, ParentProfileEntity.class);
        entity.setUserId(userId);
        entity.setCreator(userId);
        entity.setCreateDate(new Date());
        entity.setUpdater(userId);
        entity.setUpdateDate(new Date());
        
        // Set defaults
        if (StringUtils.isBlank(entity.getPreferredLanguage())) {
            entity.setPreferredLanguage("en");
        }
        if (StringUtils.isBlank(entity.getTimezone())) {
            entity.setTimezone("UTC");
        }
        if (entity.getOnboardingCompleted() == null) {
            entity.setOnboardingCompleted(false);
        }
        
        // Save entity
        parentProfileDao.insert(entity);
        
        return ConvertUtils.sourceToTarget(entity, ParentProfileDTO.class);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public ParentProfileDTO updateProfile(ParentProfileUpdateDTO dto, Long userId) {
        ParentProfileEntity entity = parentProfileDao.getByUserId(userId);
        if (entity == null) {
            throw new RenException("Parent profile not found");
        }
        
        // Update fields if provided
        if (StringUtils.isNotBlank(dto.getFullName())) {
            entity.setFullName(dto.getFullName());
        }
        if (StringUtils.isNotBlank(dto.getEmail())) {
            entity.setEmail(dto.getEmail());
        }
        if (StringUtils.isNotBlank(dto.getPhoneNumber())) {
            entity.setPhoneNumber(dto.getPhoneNumber());
        }
        if (StringUtils.isNotBlank(dto.getPreferredLanguage())) {
            entity.setPreferredLanguage(dto.getPreferredLanguage());
        }
        if (StringUtils.isNotBlank(dto.getTimezone())) {
            entity.setTimezone(dto.getTimezone());
        }
        if (StringUtils.isNotBlank(dto.getNotificationPreferences())) {
            entity.setNotificationPreferences(dto.getNotificationPreferences());
        }
        if (dto.getOnboardingCompleted() != null) {
            entity.setOnboardingCompleted(dto.getOnboardingCompleted());
        }
        if (dto.getTermsAcceptedAt() != null) {
            entity.setTermsAcceptedAt(dto.getTermsAcceptedAt());
        }
        if (dto.getPrivacyPolicyAcceptedAt() != null) {
            entity.setPrivacyPolicyAcceptedAt(dto.getPrivacyPolicyAcceptedAt());
        }
        
        entity.setUpdater(userId);
        entity.setUpdateDate(new Date());
        
        // Update entity
        this.updateById(entity);
        
        return ConvertUtils.sourceToTarget(entity, ParentProfileDTO.class);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean acceptTerms(ParentProfileAcceptTermsDTO dto, Long userId) {
        Date now = new Date();
        Date termsDate = dto.getTermsAccepted() ? now : null;
        Date privacyDate = dto.getPrivacyAccepted() ? now : null;
        
        int updated = parentProfileDao.updateTermsAcceptance(userId, termsDate, privacyDate);
        return updated > 0;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean completeOnboarding(Long userId) {
        int updated = parentProfileDao.updateOnboardingStatus(userId, true);
        return updated > 0;
    }

    @Override
    public boolean hasParentProfile(Long userId) {
        ParentProfileEntity entity = parentProfileDao.getByUserId(userId);
        return entity != null;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean deleteByUserId(Long userId) {
        QueryWrapper<ParentProfileEntity> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("user_id", userId);
        
        int deleted = parentProfileDao.delete(queryWrapper);
        return deleted > 0;
    }
}