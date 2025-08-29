package xiaozhi.modules.sys.dto;

import java.util.Date;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import jakarta.validation.constraints.Email;

/**
 * Parent Profile Update DTO
 */
@Data
@Schema(description = "Parent Profile Update Request")
public class ParentProfileUpdateDTO {
    
    @Schema(description = "Full Name")
    private String fullName;
    
    @Schema(description = "Email Address")
    @Email(message = "Email format is invalid")
    private String email;
    
    @Schema(description = "Phone Number")
    private String phoneNumber;
    
    @Schema(description = "Preferred Language")
    private String preferredLanguage;
    
    @Schema(description = "Timezone")
    private String timezone;
    
    @Schema(description = "Notification Preferences (JSON string)")
    private String notificationPreferences;
    
    @Schema(description = "Onboarding Completed")
    private Boolean onboardingCompleted;
    
    @Schema(description = "Terms Accepted At")
    private Date termsAcceptedAt;
    
    @Schema(description = "Privacy Policy Accepted At")
    private Date privacyPolicyAcceptedAt;
}