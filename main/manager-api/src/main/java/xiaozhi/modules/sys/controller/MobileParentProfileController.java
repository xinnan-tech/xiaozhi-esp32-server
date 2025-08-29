package xiaozhi.modules.sys.controller;

import java.util.HashMap;
import java.util.Map;

import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.utils.Result;
import xiaozhi.common.validator.ValidatorUtils;
import xiaozhi.modules.security.user.SecurityUser;
import xiaozhi.modules.sys.dto.ParentProfileDTO;
import xiaozhi.modules.sys.dto.ParentProfileCreateDTO;
import xiaozhi.modules.sys.dto.ParentProfileUpdateDTO;
import xiaozhi.modules.sys.dto.ParentProfileAcceptTermsDTO;
import xiaozhi.modules.sys.service.ParentProfileService;

/**
 * Mobile Parent Profile Controller
 * Handles parent profile operations for mobile app
 */
@AllArgsConstructor
@RestController
@RequestMapping("/api/mobile/profile")
@Tag(name = "Mobile Parent Profile Management")
@Slf4j
public class MobileParentProfileController {
    
    private final ParentProfileService parentProfileService;

    @GetMapping
    @Operation(summary = "Get parent profile")
    public Result<Map<String, Object>> getProfile() {
        try {
            Long userId = SecurityUser.getUserId();
            ParentProfileDTO profile = parentProfileService.getByUserId(userId);
            
            Map<String, Object> result = new HashMap<>();
            result.put("profile", profile);
            
            return new Result<Map<String, Object>>().ok(result);
        } catch (Exception e) {
            log.error("Error getting parent profile", e);
            return new Result<Map<String, Object>>().error("Failed to get parent profile");
        }
    }

    @PostMapping("/create")
    @Operation(summary = "Create parent profile")
    public Result<Map<String, Object>> createProfile(@RequestBody ParentProfileCreateDTO dto) {
        try {
            // Validate input
            ValidatorUtils.validateEntity(dto);
            
            Long userId = SecurityUser.getUserId();
            
            // Check if profile already exists
            if (parentProfileService.hasParentProfile(userId)) {
                return new Result<Map<String, Object>>().error("Parent profile already exists");
            }
            
            ParentProfileDTO profile = parentProfileService.createProfile(dto, userId);
            
            Map<String, Object> result = new HashMap<>();
            result.put("profile", profile);
            
            log.info("Parent profile created successfully for user: {}", userId);
            return new Result<Map<String, Object>>().ok(result);
        } catch (RenException e) {
            log.error("Error creating parent profile: {}", e.getMessage());
            return new Result<Map<String, Object>>().error(e.getMsg());
        } catch (Exception e) {
            log.error("Error creating parent profile", e);
            return new Result<Map<String, Object>>().error("Failed to create parent profile");
        }
    }

    @PutMapping("/update")
    @Operation(summary = "Update parent profile")
    public Result<Map<String, Object>> updateProfile(@RequestBody ParentProfileUpdateDTO dto) {
        try {
            Long userId = SecurityUser.getUserId();
            
            if (!parentProfileService.hasParentProfile(userId)) {
                return new Result<Map<String, Object>>().error("Parent profile not found");
            }
            
            ParentProfileDTO profile = parentProfileService.updateProfile(dto, userId);
            
            Map<String, Object> result = new HashMap<>();
            result.put("profile", profile);
            
            log.info("Parent profile updated successfully for user: {}", userId);
            return new Result<Map<String, Object>>().ok(result);
        } catch (RenException e) {
            log.error("Error updating parent profile: {}", e.getMessage());
            return new Result<Map<String, Object>>().error(e.getMsg());
        } catch (Exception e) {
            log.error("Error updating parent profile", e);
            return new Result<Map<String, Object>>().error("Failed to update parent profile");
        }
    }

    @PostMapping("/accept-terms")
    @Operation(summary = "Accept terms and privacy policy")
    public Result<Void> acceptTerms(@RequestBody ParentProfileAcceptTermsDTO dto) {
        try {
            // Validate input
            ValidatorUtils.validateEntity(dto);
            
            Long userId = SecurityUser.getUserId();
            
            if (!parentProfileService.hasParentProfile(userId)) {
                return new Result<Void>().error("Parent profile not found");
            }
            
            boolean success = parentProfileService.acceptTerms(dto, userId);
            if (success) {
                log.info("Terms accepted successfully for user: {}", userId);
                return new Result<Void>().ok(null);
            } else {
                return new Result<Void>().error("Failed to accept terms");
            }
        } catch (Exception e) {
            log.error("Error accepting terms", e);
            return new Result<Void>().error("Failed to accept terms");
        }
    }

    @PostMapping("/complete-onboarding")
    @Operation(summary = "Complete onboarding")
    public Result<Void> completeOnboarding() {
        try {
            Long userId = SecurityUser.getUserId();
            
            if (!parentProfileService.hasParentProfile(userId)) {
                return new Result<Void>().error("Parent profile not found");
            }
            
            boolean success = parentProfileService.completeOnboarding(userId);
            if (success) {
                log.info("Onboarding completed successfully for user: {}", userId);
                return new Result<Void>().ok(null);
            } else {
                return new Result<Void>().error("Failed to complete onboarding");
            }
        } catch (Exception e) {
            log.error("Error completing onboarding", e);
            return new Result<Void>().error("Failed to complete onboarding");
        }
    }

    @DeleteMapping
    @Operation(summary = "Delete parent profile")
    public Result<Void> deleteProfile() {
        try {
            Long userId = SecurityUser.getUserId();
            
            if (!parentProfileService.hasParentProfile(userId)) {
                return new Result<Void>().error("Parent profile not found");
            }
            
            boolean success = parentProfileService.deleteByUserId(userId);
            if (success) {
                log.info("Parent profile deleted successfully for user: {}", userId);
                return new Result<Void>().ok(null);
            } else {
                return new Result<Void>().error("Failed to delete parent profile");
            }
        } catch (Exception e) {
            log.error("Error deleting parent profile", e);
            return new Result<Void>().error("Failed to delete parent profile");
        }
    }
}