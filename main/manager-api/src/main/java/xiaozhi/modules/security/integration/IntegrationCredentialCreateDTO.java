package xiaozhi.modules.security.integration;

import java.util.Date;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class IntegrationCredentialCreateDTO {
    @NotBlank
    @Size(max = 100)
    private String name;

    @NotNull
    private Long ownerUserId;

    private Date expiresAt;
}
