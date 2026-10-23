package xiaozhi.modules.device.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * 迁移脚本 202610231200.sql 的行为测试
 *
 * <p>
 * 这段迁移真正要保证的是刷完之后不会出现两行归一成同一个值。判重条件被去掉、
 * 连接条件写错、大写判断漏了 BINARY，后果都是同一台设备之后彻底读不出来，
 * 而且没有任何报错可查。子串匹配一个都测不出来，只能在真库上跑一遍看结果。
 *
 * <p>
 * 需要一个连得上的 MySQL。连不上就跳过而不是报错，变量是
 * XIAOZHI_TEST_MYSQL_URL、XIAOZHI_TEST_MYSQL_USER、XIAOZHI_TEST_MYSQL_PASSWORD
 */
@DisplayName("MAC 归一迁移脚本")
class MacAddressMigrationSqlTest {

    private static final String SCHEMA = "mac_migration_sql_test";

    private static Connection connection;

    @BeforeAll
    static void openConnection() {
        String url = System.getenv("XIAOZHI_TEST_MYSQL_URL");
        Assumptions.assumeTrue(url != null && !url.isBlank(),
                "没给 XIAOZHI_TEST_MYSQL_URL，跳过真库迁移测试");
        try {
            connection = DriverManager.getConnection(url,
                    System.getenv().getOrDefault("XIAOZHI_TEST_MYSQL_USER", "root"),
                    System.getenv().getOrDefault("XIAOZHI_TEST_MYSQL_PASSWORD", ""));
        } catch (SQLException e) {
            Assumptions.abort("连不上 " + url + "：" + e.getMessage());
        }
    }

    @AfterAll
    static void closeConnection() throws SQLException {
        if (connection == null) {
            return;
        }
        for (String statement : splitStatements("DROP SCHEMA IF EXISTS `" + SCHEMA + "`")) {
            connection.createStatement().execute(statement);
        }
        connection.close();
    }

    @BeforeEach
    void recreateTables() throws SQLException {
        execute("DROP SCHEMA IF EXISTS `" + SCHEMA + "`");
        execute("CREATE SCHEMA `" + SCHEMA + "`");
        // 迁移脚本里的表名不带库名，默认库得先切过去
        connection.setCatalog(SCHEMA);
        // 建表语句照抄真实脚本，见 202503141346.sql:110 和 202605251426.sql:27。
        // schema 变了这里要跟着改，否则测的是一个库线上不存在的形状
        execute("""
                CREATE TABLE `%s`.`ai_device` (
                  `id` VARCHAR(32) NOT NULL COMMENT '设备唯一标识',
                  `user_id` BIGINT COMMENT '关联用户 ID',
                  `mac_address` VARCHAR(50) COMMENT 'MAC 地址',
                  `alias` VARCHAR(64) DEFAULT NULL COMMENT '设备别名',
                  `create_date` DATETIME COMMENT '创建时间',
                  `update_date` DATETIME COMMENT '更新时间',
                  PRIMARY KEY (`id`),
                  INDEX `idx_ai_device_created_at` (`mac_address`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备信息表'
                """.formatted(SCHEMA));
        execute("""
                CREATE TABLE `%s`.`ai_device_address_book` (
                  `mac_address` VARCHAR(64) NOT NULL COMMENT '本设备MAC地址',
                  `target_mac` VARCHAR(64) NOT NULL COMMENT '对方设备MAC地址',
                  `alias` VARCHAR(64) DEFAULT NULL COMMENT '别名',
                  `has_permission` TINYINT(1) DEFAULT TRUE COMMENT '是否有权限呼叫',
                  PRIMARY KEY (`mac_address`, `target_mac`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='设备通讯录表'
                """.formatted(SCHEMA));
    }

    @Test
    @DisplayName("有重复组时，只刷归一后不撞车的那些行")
    void collidingGroupIsSkippedButUniqueRowsStillNormalize() throws SQLException {
        // 同一台设备被填过两种写法，这两行归一后会撞上，整组一个都不动
        insertDevice("d1", "AA-BB-CC-DD-EE-01");
        insertDevice("d2", "aabbccddee01");
        // 独立的设备，不该因为别处有重复组被连累
        insertDevice("x1", "11-22-33-44-55-66");
        // 已经是冒号分隔的大写写法，和小写归一值逐字节不同，得刷
        insertDevice("u1", "AA:BB:CC:DD:EE:99");
        // 32 位伪 MAC 正则不匹配，原样不动，和 Java 那边 normalizeDeviceId 一致
        insertDevice("p1", "aabbccddeeff00112233445566778899");

        runMigration();

        assertEquals("AA-BB-CC-DD-EE-01", deviceMac("d1"), "重复组该整组不动");
        assertEquals("aabbccddee01", deviceMac("d2"), "重复组该整组不动");
        assertEquals("11:22:33:44:55:66", deviceMac("x1"));
        assertEquals("aa:bb:cc:dd:ee:99", deviceMac("u1"));
        assertEquals("aabbccddeeff00112233445566778899", deviceMac("p1"));
    }

    @Test
    @DisplayName("没有重复时全部刷成归一值")
    void everyUniqueRowNormalizes() throws SQLException {
        insertDevice("u1", "AA:BB:CC:DD:EE:99");
        insertDevice("u2", "aa-bb-cc-dd-ee-98");
        insertDevice("u3", "AABBCCDDEE97");
        insertDevice("u4", "aa_bb_cc_dd_ee_96");
        insertDevice("u5", "AA-BB-CC-DD-EE-95");

        runMigration();

        assertEquals("aa:bb:cc:dd:ee:99", deviceMac("u1"));
        assertEquals("aa:bb:cc:dd:ee:98", deviceMac("u2"));
        assertEquals("aa:bb:cc:dd:ee:97", deviceMac("u3"));
        assertEquals("aa:bb:cc:dd:ee:96", deviceMac("u4"));
        assertEquals("aa:bb:cc:dd:ee:95", deviceMac("u5"));
    }

    @Test
    @DisplayName("整库都是重复组时一行都不动")
    void allCollidingRowsStayUntouched() throws SQLException {
        insertDevice("d1", "AA-BB-CC-DD-EE-01");
        insertDevice("d2", "aabbccddee01");
        insertDevice("d3", "AA:BB:CC:DD:EE:01");

        runMigration();

        assertEquals("AA-BB-CC-DD-EE-01", deviceMac("d1"));
        assertEquals("aabbccddee01", deviceMac("d2"));
        assertEquals("AA:BB:CC:DD:EE:01", deviceMac("d3"));
    }

    @Test
    @DisplayName("值已经是对的时空跑，重跑安全")
    void rerunningTheMigrationChangesNothing() throws SQLException {
        insertDevice("u1", "AA:BB:CC:DD:EE:99");
        insertDevice("d1", "AA-BB-CC-DD-EE-01");
        insertDevice("d2", "aabbccddee01");
        runMigration();

        runMigration();

        assertEquals("aa:bb:cc:dd:ee:99", deviceMac("u1"));
        assertEquals("AA-BB-CC-DD-EE-01", deviceMac("d1"));
        assertEquals("aabbccddee01", deviceMac("d2"));
    }

    @Test
    @DisplayName("通讯录两列各自判重：owner 撞车不动 owner，target 照刷")
    void addressBookColumnsAreGuardedIndependently() throws SQLException {
        // owner 有两种写法会撞，这两行的 owner 不动
        insertBook("row1", "AA-BB-CC-DD-EE-01", "11-22-33-44-55-66");
        insertBook("row2", "aabbccddee01", "11:22:33:44:55:77");
        // 这两行的 owner 各不相同，但 target 是同一台的两种写法：
        // owner 照刷，target 整组不动
        insertBook("row3", "22-22-33-44-55-88", "AA-BB-CC-DD-EE-02");
        insertBook("row4", "33-33-44-55-88-99", "aabbccddee02");

        runMigration();

        assertEquals("AA-BB-CC-DD-EE-01", bookMac("row1"), "owner 撞车的整组不动");
        assertEquals("aabbccddee01", bookMac("row2"), "owner 撞车的整组不动");
        assertEquals("11:22:33:44:55:66", bookTarget("row1"), "target 唯一就该刷");
        assertEquals("11:22:33:44:55:77", bookTarget("row2"), "target 唯一就该刷");

        assertEquals("22:22:33:44:55:88", bookMac("row3"), "owner 唯一就该刷");
        assertEquals("AA-BB-CC-DD-EE-02", bookTarget("row3"), "target 撞车的整组不动");
        assertEquals("33:33:44:55:88:99", bookMac("row4"));
        assertEquals("aabbccddee02", bookTarget("row4"));
    }

    @Test
    @DisplayName("判重条件没了，通讯录会撞主键把整段迁移卡住")
    void withoutTheDuplicateGuardTheAddressBookWouldCollideOnItsPrimaryKey() throws SQLException {
        // 主键是 (owner, target)，两行得撞在这一对上：owner 和 target 都归一成同一个值
        insertBook("row1", "AA-BB-CC-DD-EE-01", "11-22-33-44-55-66");
        insertBook("row2", "aabbccddee01", "112233445566");

        // 从真脚本上把判重摘掉再跑。脚本里已经没判重的话替换就是空操作，
        // 跑的还是没有保护的版本，这个用例照样成立
        String unguarded = readChangelog("202610231200.sql")
                .replace("\nJOIN cnt ON cnt.`nmac` = norm.`nmac`\n", "\n")
                .replace("\nJOIN cnt ON cnt.`ntmac` = norm.`ntmac`\n", "\n")
                .replace("WHERE cnt.`n` = 1", "WHERE 1 = 1");

        SQLException failure = assertThrows(SQLException.class, () -> run(unguarded));

        assertEquals("23000", failure.getSQLState(),
                "撞的是主键唯一性，没撞上说明这组数据造得不对：" + failure.getMessage());
    }

    @Test
    @DisplayName("排查重复的那条 SQL 报出被跳过的组")
    void duplicateDiagnosticListsTheSkippedGroup() throws SQLException {
        insertDevice("d1", "AA-BB-CC-DD-EE-01");
        insertDevice("d2", "aabbccddee01");
        insertDevice("x1", "11-22-33-44-55-66");
        runMigration();

        assertEquals(List.of("aa:bb:cc:dd:ee:01"),
                queryColumn(diagnostic("③ 刷完之后跑这个"), 0),
                "只该报出被判重跳过的那个组，刷完了的行不该出现在名单里");
    }

    @Test
    @DisplayName("漏刷检查报出还留在原写法的行")
    void leftoverCheckFindsRowsStillInOriginalSpelling() throws SQLException {
        insertDevice("d1", "AA-BB-CC-DD-EE-01");
        insertDevice("d2", "aabbccddee01");
        insertDevice("x1", "11-22-33-44-55-66");
        insertDevice("u1", "AA:BB:CC:DD:EE:99");
        runMigration();

        assertEquals(List.of("AA-BB-CC-DD-EE-01", "aabbccddee01"),
                queryColumn(diagnostic("漏刷检查"), 1),
                "刷完只剩判重跳过的那两行是原写法，x1、u1 都该刷掉");
    }

    @Test
    @DisplayName("漏刷检查能报出该刷没刷出来的行")
    void leftoverCheckFindsRowsTheMigrationNeverTouched() throws SQLException {
        insertDevice("d1", "AA-BB-CC-DD-EE-01");
        insertDevice("d2", "aabbccddee01");
        insertDevice("x1", "11-22-33-44-55-66");

        assertEquals(List.of("d1", "d2", "x1"),
                queryColumn(diagnostic("漏刷检查"), 0),
                "整段迁移一行没动时漏刷检查要全报出来，不然迁移只做了一半没人知道");
    }

    /** 按 Liquibase 的 sqlFile 那样读脚本：去注释，按分号切，在一个事务里逐句执行 */
    private void runMigration() throws SQLException {
        run(readChangelog("202610231200.sql"));
    }

    private void run(String script) throws SQLException {
        connection.setAutoCommit(false);
        try {
            for (String statement : splitStatements(script)) {
                execute(statement);
            }
            connection.commit();
        } catch (SQLException e) {
            connection.rollback();
            throw e;
        } finally {
            connection.setAutoCommit(true);
        }
    }

    private void insertDevice(String id, String mac) throws SQLException {
        execute("INSERT INTO `%s`.`ai_device` (`id`, `mac_address`) VALUES ('%s', '%s')"
                .formatted(SCHEMA, id, mac));
    }

    /** alias 放行标识，mac_address 刷完就变了，靠它才找得到原来那一行 */
    private void insertBook(String rowTag, String mac, String target) throws SQLException {
        execute(("INSERT INTO `%s`.`ai_device_address_book` (`mac_address`, `target_mac`, `alias`)"
                + " VALUES ('%s', '%s', '%s')").formatted(SCHEMA, mac, target, rowTag));
    }

    private String deviceMac(String id) throws SQLException {
        return queryOne("SELECT `mac_address` FROM `%s`.`ai_device` WHERE `id` = '%s'".formatted(SCHEMA, id));
    }

    private String bookMac(String rowTag) throws SQLException {
        return queryOne("SELECT `mac_address` FROM `%s`.`ai_device_address_book` WHERE `alias` = '%s'"
                .formatted(SCHEMA, rowTag));
    }

    private String bookTarget(String rowTag) throws SQLException {
        return queryOne("SELECT `target_mac` FROM `%s`.`ai_device_address_book` WHERE `alias` = '%s'"
                .formatted(SCHEMA, rowTag));
    }

    private String queryOne(String sql) throws SQLException {
        try (Statement statement = connection.createStatement();
                ResultSet rows = statement.executeQuery(sql)) {
            assertTrue(rows.next(), "查不到行：" + sql);
            return rows.getString(1);
        }
    }

    private void execute(String sql) throws SQLException {
        for (String statement : splitStatements(sql)) {
            try (Statement s = connection.createStatement()) {
                s.execute(statement);
            }
        }
    }

    /** 去注释后按分号切。脚本里除了分号没有别的分句符 */
    private static List<String> splitStatements(String sql) {
        StringBuilder body = new StringBuilder();
        for (String line : sql.split("\n")) {
            if (!line.stripLeading().startsWith("--")) {
                body.append(line).append('\n');
            }
        }
        List<String> statements = new ArrayList<>();
        for (String piece : body.toString().split(";")) {
            if (!piece.isBlank()) {
                statements.add(piece.strip());
            }
        }
        return statements;
    }

    private static String readChangelog(String fileName) {
        try {
            return Files.readString(
                    Path.of("src", "main", "resources", "db", "changelog", fileName),
                    StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new IllegalStateException("读不到 " + fileName, e);
        }
    }

    /**
     * 把脚本里注释掉的那段排查 SQL 整条取出来
     *
     * <p>
     * 脚本里那一段是给人手工跑的，跑不走就等于没写。取出来在真库上执行一遍，
     * 段里的 SQL 坏了、引用了不存在的列，这里会直接报错
     */
    private static String diagnostic(String marker) {
        List<String> collected = new ArrayList<>();
        boolean inBlock = false;
        for (String line : readChangelog("202610231200.sql").split("\n")) {
            if (!line.stripLeading().startsWith("--")) {
                if (!collected.isEmpty()) {
                    break;
                }
                continue;
            }
            if (!inBlock) {
                inBlock = line.contains(marker);
                if (!inBlock) {
                    continue;
                }
            }
            String body = line.stripLeading().substring(2).strip();
            if (collected.isEmpty() && !body.startsWith("SELECT")) {
                // 说明文字，去掉行首的 -- 之后就不是注释了，不能拼进语句里
                continue;
            }
            collected.add(body);
            if (body.endsWith(";")) {
                break;
            }
        }
        assertFalse(collected.isEmpty(), "脚本里找不到 " + marker + " 那段排查 SQL");
        return String.join("\n", collected);
    }

    private List<String> queryColumn(String sql, int column) throws SQLException {
        List<String> values = new ArrayList<>();
        try (Statement statement = connection.createStatement();
                ResultSet rows = statement.executeQuery(sql)) {
            while (rows.next()) {
                values.add(rows.getString(column + 1));
            }
        }
        return values;
    }
}
