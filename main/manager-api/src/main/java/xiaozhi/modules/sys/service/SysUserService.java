package xiaozhi.modules.sys.service;

import xiaozhi.common.service.BaseService;
import xiaozhi.modules.sys.dto.SysUserDTO;
import xiaozhi.modules.sys.entity.SysUserEntity;


/**
 * 系统用户
 */
public interface SysUserService extends BaseService<SysUserEntity> {

    SysUserDTO getByUsername(String username);

    void save(SysUserDTO dto);

    void delete(Long[] ids);

}
