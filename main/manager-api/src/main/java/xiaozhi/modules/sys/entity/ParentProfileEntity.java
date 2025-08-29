package xiaozhi.modules.sys.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;

import lombok.Data;
import lombok.EqualsAndHashCode;
import xiaozhi.common.entity.BaseEntity;

/**
 * Parent profile entity for mobile app users
 */
@Data
@EqualsAndHashCode(callSuper = false)
@TableName("parent_profile")
public class ParentProfileEntity extends BaseEntity {
    /**
     * Foreign key to sys_user table
     */
    private Long userId;
    
    /**
     * Supabase user ID for reference
     */
    private String supabaseUserId;
    
    /**
     * Parent full name
     */
    private String fullName;
    
    /**
     * Parent email address
     */
    private String email;
    
    /**
     * Parent phone number
     */
    private String phoneNumber;
    
    /**
     * Preferred language code (en, es, fr, etc.)
     */
    private String preferredLanguage;
    
    /**
     * User timezone
     */
    private String timezone;
    
    /**
     * JSON object with notification settings
     */
    private String notificationPreferences;
    
    /**
     * Whether onboarding is completed
     */
    private Boolean onboardingCompleted;
    
    /**
     * When terms of service were accepted
     */
    private Date termsAcceptedAt;
    
    /**
     * When privacy policy was accepted
     */
    private Date privacyPolicyAcceptedAt;
    
    /**
     * User who last updated this record
     */
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private Long updater;
    
    /**
     * Last update timestamp
     */
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private Date updateDate;
}