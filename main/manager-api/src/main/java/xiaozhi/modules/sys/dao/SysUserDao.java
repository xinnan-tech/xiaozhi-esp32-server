package xiaozhi.modules.sys.dao;

import org.apache.ibatis.annotations.Mapper;

import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.sys.entity.SysUserEntity;

/**
 * 系统用户
 */
@Mapper
public interface SysUserDao extends BaseDao<SysUserEntity> {

}