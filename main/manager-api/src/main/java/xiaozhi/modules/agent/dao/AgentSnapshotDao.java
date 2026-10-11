package xiaozhi.modules.agent.dao;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.agent.entity.AgentSnapshotEntity;

@Mapper
public interface AgentSnapshotDao extends BaseDao<AgentSnapshotEntity> {
    Integer selectMaxVersionNo(@Param("agentId") String agentId);

    AgentSnapshotEntity selectLatestSnapshot(@Param("agentId") String agentId);

    AgentSnapshotEntity selectNextSnapshot(@Param("agentId") String agentId, @Param("versionNo") Integer versionNo);

    int insertWithNextVersion(@Param("snapshot") AgentSnapshotEntity snapshot);

    int deleteOlderThanKeepLimit(@Param("agentId") String agentId, @Param("keepLimit") int keepLimit);

    List<AgentSnapshotEntity> selectLegacyRedactionBatch(@Param("afterId") String afterId,
            @Param("limit") int limit,
            @Param("targetRedactionVersion") int targetRedactionVersion);

    int updateRedactedSnapshots(@Param("snapshots") List<AgentSnapshotEntity> snapshots,
            @Param("redactionVersion") int redactionVersion);
}
