package xiaozhi.modules.sys.dto;

import java.util.Date;

import com.fasterxml.jackson.annotation.JsonProperty;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import lombok.EqualsAndHashCode;
import xiaozhi.common.validator.group.AddGroup;
import xiaozhi.common.validator.group.DefaultGroup;
import xiaozhi.common.validator.group.UpdateGroup;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

/**
 * Parent Profile DTO
 */
@Data
@EqualsAndHashCode(callSuper = false)
@Schema(description = "Parent Profile")
public class ParentProfileDTO {
    
    @Schema(description = "Profile ID")
    @NotNull(message = "Profile ID cannot be null", groups = UpdateGroup.class)
    private Long id;
    
    @Schema(description = "User ID")
    @NotNull(message = "User ID cannot be null", groups = {AddGroup.class, UpdateGroup.class})
    private Long userId;
    
    @Schema(description = "Supabase User ID")
    private String supabaseUserId;
    
    @Schema(description = "Full Name")
    @NotBlank(message = "Full name cannot be blank", groups = {AddGroup.class, DefaultGroup.class})
    private String fullName;
    
    @Schema(description = "Email Address")
    private String email;
    
    @Schema(description = "Phone Number")
    @NotBlank(message = "Phone number cannot be blank", groups = {AddGroup.class, DefaultGroup.class})
    private String phoneNumber;
    
    @Schema(description = "Preferred Language")
    private String preferredLanguage;
    
    @Schema(description = "Timezone")
    private String timezone;
    
    @Schema(description = "Notification Preferences (JSON)")
    private String notificationPreferences;
    
    @Schema(description = "Onboarding Completed")
    private Boolean onboardingCompleted;
    
    @Schema(description = "Terms Accepted At")
    @JsonProperty("termsAcceptedAt")
    private Date termsAcceptedAt;
    
    @Schema(description = "Privacy Policy Accepted At")
    @JsonProperty("privacyPolicyAcceptedAt")
    private Date privacyPolicyAcceptedAt;
    
    @Schema(description = "Creator")
    private Long creator;
    
    @Schema(description = "Create Date")
    @JsonProperty("createdAt")
    private Date createDate;
    
    @Schema(description = "Updater")
    private Long updater;
    
    @Schema(description = "Update Date")
    @JsonProperty("updatedAt")
    private Date updateDate;
}