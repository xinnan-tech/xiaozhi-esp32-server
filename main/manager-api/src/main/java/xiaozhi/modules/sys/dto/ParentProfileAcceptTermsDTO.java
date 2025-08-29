package xiaozhi.modules.sys.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import jakarta.validation.constraints.NotNull;

/**
 * Parent Profile Accept Terms DTO
 */
@Data
@Schema(description = "Accept Terms and Privacy Policy Request")
public class ParentProfileAcceptTermsDTO {
    
    @Schema(description = "Terms Accepted")
    @NotNull(message = "Terms acceptance status cannot be null")
    private Boolean termsAccepted;
    
    @Schema(description = "Privacy Policy Accepted")
    @NotNull(message = "Privacy policy acceptance status cannot be null")
    private Boolean privacyAccepted;
}