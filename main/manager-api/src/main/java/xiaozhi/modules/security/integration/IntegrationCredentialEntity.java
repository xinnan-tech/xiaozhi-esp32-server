package xiaozhi.modules.security.integration;

import java.io.Serializable;
import java.util.Date;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import lombok.Data;

@Data
@TableName("sys_integration_credential")
public class IntegrationCredentialEntity implements Serializable {
    @TableId(type = IdType.INPUT)
    private String id;
    private String name;
    private String subject;
    private Long ownerUserId;
    private String tokenHash;
    private Integer enabled;
    private Date expiresAt;
    private Date lastUsedAt;
    private Date revokedAt;
    private Long creator;
    private Date createDate;
    private Long updater;
    private Date updateDate;
}
