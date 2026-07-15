package xiaozhi.modules.agent.service;

import java.io.File;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.Properties;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;

import jakarta.annotation.PostConstruct;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import lombok.extern.slf4j.Slf4j;

/**
 * 成长服务画像客户端:读取成长服务 growth_service.db 的 profile_enrichment 表,
 * 取某设备最新 13 维儿童画像(extension_fields JSON)。
 *
 * 读取策略:把源库(+WAL 若有)复制成本地只读快照(临时目录)再查询。
 * 这样彻底解耦对成长服务日志模式的依赖——无论对方用 WAL 还是 DELETE 模式、无论源库以 :ro 挂载,
 * 快照在可写临时目录,SQLite 总能正常打开并应用 WAL 帧,读到最新画像。
 * 快照带 5 分钟 TTL 缓存,限制复制 IO(周期任务按用户调用也不会频繁拷贝)。
 *
 * 读取失败(库不存在/设备无画像/复制失败)降级返回 null,绝不抛异常阻断主流程。
 */
@Slf4j
@Component
public class GrowthPersonaClient {

    @Value("${growth.profile-db-path:}")
    private String dbPath;

    private static final long SNAPSHOT_TTL_MS = 5 * 60 * 1000L;
    private final Object snapshotLock = new Object();
    private volatile long lastCopyTs = 0L;
    private volatile String snapshotDbPath;

    @PostConstruct
    public void init() {
        String tmp = System.getProperty("java.io.tmpdir");
        File dir = new File(tmp, "growth_persona_snapshot");
        dir.mkdirs();
        snapshotDbPath = new File(dir, "growth_service.db").getAbsolutePath();
    }

    /**
     * 按 deviceId 取最新画像 extension_fields JSON;无则 null。
     */
    public String getProfileJson(String deviceId) {
        if (deviceId == null || deviceId.isBlank() || dbPath == null || dbPath.isBlank()) {
            return null;
        }
        // 优先用快照(复制失败则退而直读源库,最差降级 null)
        try {
            ensureSnapshot();
        } catch (Exception e) {
            log.warn("[growth-persona] 快照复制失败,尝试直读源库:{}", e.getMessage());
        }
        String path = (snapshotDbPath != null && new File(snapshotDbPath).exists()) ? snapshotDbPath : dbPath;

        // 只读连接(SQLITE_OPEN_READONLY=1),busy_timeout 避免并发读短暂锁等待
        String url = "jdbc:sqlite:" + path;
        Properties props = new Properties();
        props.setProperty("open_mode", "1");
        props.setProperty("busy_timeout", "3000");
        String sql = "SELECT extension_fields FROM profile_enrichment WHERE device_id = ? ORDER BY updated_at DESC LIMIT 1";
        try (Connection conn = DriverManager.getConnection(url, props);
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setString(1, deviceId);
            try (ResultSet rs = ps.executeQuery()) {
                if (rs.next()) {
                    return rs.getString("extension_fields");
                }
            }
        } catch (Exception e) {
            log.warn("[growth-persona] 读画像失败 device={}:{}", deviceId, e.getMessage());
        }
        return null;
    }

    /** 复制源库(含 -wal)到本地快照;TTL 内复用 */
    private void ensureSnapshot() throws Exception {
        long now = System.currentTimeMillis();
        if (snapshotDbPath != null && new File(snapshotDbPath).exists() && (now - lastCopyTs) < SNAPSHOT_TTL_MS) {
            return;
        }
        synchronized (snapshotLock) {
            if (snapshotDbPath != null && new File(snapshotDbPath).exists() && (now - lastCopyTs) < SNAPSHOT_TTL_MS) {
                return;
            }
            File src = new File(dbPath);
            if (!src.exists()) {
                return;
            }
            File dst = new File(snapshotDbPath);
            Files.copy(src.toPath(), dst.toPath(), StandardCopyOption.REPLACE_EXISTING);
            // 复制 -wal(若存在),保证 WAL 帧一并带入快照,读到最新画像
            File srcWal = new File(dbPath + "-wal");
            if (srcWal.exists()) {
                Files.copy(srcWal.toPath(), new File(snapshotDbPath + "-wal").toPath(),
                        StandardCopyOption.REPLACE_EXISTING);
            }
            lastCopyTs = System.currentTimeMillis();
            log.debug("[growth-persona] 快照已刷新:{}", snapshotDbPath);
        }
    }
}
