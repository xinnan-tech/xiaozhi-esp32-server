package xiaozhi.modules.knowledge.dao;

import org.apache.ibatis.annotations.Mapper;
import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.knowledge.entity.DocumentEntity;

/**
 * 文档 DAO
 */
@Mapper
public interface DocumentDao extends BaseDao<DocumentEntity> {
}
