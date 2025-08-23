package xiaozhi.modules.sys.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Email;

/**
 * Parent Profile Create DTO
 */
@Data
@Schema(description = "Parent Profile Create Request")
public class ParentProfileCreateDTO {
    
    @Schema(description = "Supabase User ID")
    private String supabaseUserId;
    
    @Schema(description = "Full Name")
    @NotBlank(message = "Full name cannot be blank")
    private String fullName;
    
    @Schema(description = "Email Address")
    @Email(message = "Email format is invalid")
    private String email;
    
    @Schema(description = "Phone Number")
    @NotBlank(message = "Phone number cannot be blank")
    private String phoneNumber;
    
    @Schema(description = "Preferred Language", example = "en")
    private String preferredLanguage = "en";
    
    @Schema(description = "Timezone", example = "UTC")
    private String timezone = "UTC";
    
    @Schema(description = "Notification Preferences (JSON string)", 
           example = "{\"push\":true,\"email\":true,\"daily_summary\":true}")
    private String notificationPreferences;
    
    @Schema(description = "Onboarding Completed")
    private Boolean onboardingCompleted = false;
}