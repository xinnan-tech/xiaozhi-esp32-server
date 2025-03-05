package xiaozhi.service;

import xiaozhi.modules.sys.dao.SysUserDao;
import xiaozhi.modules.sys.entity.SysUserEntity;
import jakarta.annotation.Resource;
import org.springframework.stereotype.Service;

/**
 * 测试多数据源
 */
@Service
public class DynamicDataSourceTestService {
    @Resource
    private SysUserDao sysUserDao;

    //@Transactional
    public void updateUser(Long id) {
        SysUserEntity user = new SysUserEntity();
        user.setId(id);
        user.setMobile("13500000000");
        //sysUserDao.updateById(user);
        System.out.println(sysUserDao.selectById(id));
    }
}