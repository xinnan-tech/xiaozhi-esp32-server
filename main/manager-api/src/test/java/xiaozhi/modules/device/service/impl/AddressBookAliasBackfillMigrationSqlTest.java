package xiaozhi.modules.device.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
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
 * 迁移脚本 202610231400.sql 的行为测试
 *
 * <p>
 * 这段迁移要往通讯录填名字，填的名字是从设备表拿的。设备表里同一个 MAC 可以有
 * 多行（同一台设备被两个用户各登记一次），这时候同一个 target_mac 会对上好几行，
 * MySQL 自己挑一行，不报错、不打日志。挑到谁跟通讯录这一行属于哪个用户毫无关系，
 * 于是另一个用户的私有名就被填进了别人的通讯录。这类串数据在库和接口返回里都看不出来，
 * 只能造出重名设备再跑一遍迁移，看填进去的是不是自己的东西。
 *
 * <p>
 * 需要一个连得上的 MySQL。连不上就跳过而不是报错，变量是
 * XIAOZHI_TEST_MYSQL_URL、XIAOZHI_TEST_MYSQL_USER、XIAOZHI_TEST_MYSQL_PASSWORD
 */
@DisplayName("通讯录别名回填迁移脚本")
class AddressBookAliasBackfillMigrationSqlTest {

    private static final String SCHEMA = "address_book_alias_backfill_sql_test";

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
        connection.createStatement().execute("DROP SCHEMA IF EXISTS `" + SCHEMA + "`");
        connection.close();
    }

    @BeforeEach
    void recreateTables() throws SQLException, IOException {
        execute("DROP SCHEMA IF EXISTS `" + SCHEMA + "`");
        execute("CREATE SCHEMA `" + SCHEMA + "`");
        // 迁移脚本里的表名不带库名，默认库得先切过去
        connection.setCatalog(SCHEMA);
        // 建表语句照抄真实脚本，见 202503141346.sql:110 和 202605251426.sql:27
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
                  `creator` BIGINT DEFAULT NULL COMMENT '创建人',
                  `create_date` DATETIME DEFAULT CURRENT_TIMESTAMP,
                  `update_date` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  PRIMARY KEY (`mac_address`, `target_mac`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='设备通讯录表'
                """.formatted(SCHEMA));
    }

    @Test
    @DisplayName("同一台设备被两个用户各登记一次，两个用户都拿不到对方起过的名字")
    void twoUsersRegisteringTheSameDeviceLeakNothing() throws SQLException, IOException {
        sameDeviceRegisteredByTwoUsers();
        insertBook("22:33:44:55:66:01", "aa:bb:cc:dd:ee:01", 7L);
        insertBook("22:33:44:55:66:02", "AA:BB:CC:DD:EE:01", 8L);

        runMigration();

        String first = aliasOf("22:33:44:55:66:01");
        String second = aliasOf("22:33:44:55:66:02");
        assertNotEquals("七号房投影", second, "用户 8 的通讯录里出现了用户 7 起过的名字");
        assertNotEquals("公司会议室", first, "用户 7 的通讯录里出现了用户 8 起过的名字");
        // 名字算不出来就不拿设备表里的，用这一行自己的 target_mac 兜底
        assertEquals("尾号为01的设备", first);
        assertEquals("尾号为01的设备", second);
    }

    @Test
    @DisplayName("名字跟着歧义有没有解决走，不跟着数据库随手挑哪一行走")
    void theNameFollowsTheAmbiguityNotWhicheverRowTheDatabaseHandsBack() throws SQLException, IOException {
        sameDeviceRegisteredByTwoUsers();
        insertBook("22:33:44:55:66:01", "aa:bb:cc:dd:ee:01", 7L);

        runMigration();
        assertEquals("尾号为01的设备", aliasOf("22:33:44:55:66:01"),
                "两台设备还在，名字就算不出来，不该先填一个");

        // 少了一台设备之后剩下的就是唯一的一台了，这时候填它的智控台名字才是对的
        execute("DELETE FROM `%s`.`ai_device` WHERE `id` = 'dev-u8'".formatted(SCHEMA));
        setAliasToNull("22:33:44:55:66:01");
        runMigration();

        assertEquals("七号房投影", aliasOf("22:33:44:55:66:01"));
    }

    @Test
    @DisplayName("只差大小写的一组设备算撞上了，大小写写法的行拿到的称呼一样")
    void aGroupDifferingOnlyByCaseCountsAsColliding() throws SQLException, IOException {
        // 四个用户各登记一次，写法两种大小写混着来。连接那句不区分大小写，
        // 这四行在它眼里是同一个 MAC；判重要是逐字节比，每一行都会以为自己独一份
        insertDevice("dev-a", "aa:bb:cc:dd:ee:01", "甲的名字");
        insertDevice("dev-b", "AA:BB:CC:DD:EE:01", "乙的名字");
        insertDevice("dev-c", "aa:BB:cc:DD:ee:01", "丙的名字");
        insertDevice("dev-d", "Aa:bB:cc:dd:eE:01", "丁的名字");
        insertBook("33:44:55:66:77:01", "aa:bb:cc:dd:ee:01", 21L);
        insertBook("33:44:55:66:77:02", "AA:BB:CC:DD:EE:01", 22L);

        runMigration();

        assertEquals("尾号为01的设备", aliasOf("33:44:55:66:77:01"));
        assertEquals("尾号为01的设备", aliasOf("33:44:55:66:77:02"));
    }

    @Test
    @DisplayName("分隔符不一样的两行不算撞车，各填各的")
    void rowsDifferingBySeparatorAreNotTheSameDevice() throws SQLException, IOException {
        // 比较规则只折叠大小写，不折叠分隔符，'-' 和 ':' 在它眼里是两个字符。
        // 所以这两行在连接那句里本来就对不上，各填各的才是对的
        insertDevice("dev-d1", "AA-BB-CC-DD-EE-01", "东厢房");
        insertDevice("dev-d2", "aa:bb:cc:dd:ee:01", "西厢房");
        insertBook("44:55:66:77:88:02", "aa:bb:cc:dd:ee:01", 32L);

        runMigration();

        assertEquals("西厢房", aliasOf("44:55:66:77:88:02"));
    }

    @Test
    @DisplayName("只有一台设备时照旧填智控台起过的名字")
    void unambiguousDeviceStillGetsItsConsoleName() throws SQLException, IOException {
        insertDevice("dev-u9", "11:22:33:44:55:66", "客厅音响");
        insertBook("22:33:44:55:66:03", "11:22:33:44:55:66", 9L);

        runMigration();

        assertEquals("客厅音响", aliasOf("22:33:44:55:66:03"));
    }

    @Test
    @DisplayName("设备登记了但用户没起名，退回尾号称呼")
    void unnamedDeviceFallsBackToTheMacSuffix() throws SQLException, IOException {
        insertDevice("dev-u10", "11:22:33:44:55:77", null);
        insertBook("22:33:44:55:66:04", "11:22:33:44:55:77", 10L);

        runMigration();

        assertEquals("尾号为77的设备", aliasOf("22:33:44:55:66:04"));
    }

    @Test
    @DisplayName("已经有名字的行不被动")
    void rowsThatAlreadyHaveANameAreLeftAlone() throws SQLException, IOException {
        sameDeviceRegisteredByTwoUsers();
        insertBook("22:33:44:55:66:01", "aa:bb:cc:dd:ee:01", 7L);
        execute(("UPDATE `%s`.`ai_device_address_book` SET `alias` = '我自己起的名'"
                + " WHERE `mac_address` = '22:33:44:55:66:01'").formatted(SCHEMA));

        runMigration();

        assertEquals("我自己起的名", aliasOf("22:33:44:55:66:01"));
    }

    @Test
    @DisplayName("末两位是字母时兜底称呼取小写，和运行期算出来的一致")
    void theFallbackNameLowercasesTheLastTwoCharacters() throws SQLException, IOException {
        // 运行期那边 Java 算的是小写末两位。这里跟着取原值的话，
        // 同一个 MAC 迁移出来叫「尾号为AB的设备」，搬进智控台上叫「ab」，
        // 两边对不上，用户按迁移出来的名字呼不到人
        insertDevice("dev-l1", "11:22:33:44:55:AB", null);
        insertBook("55:66:77:88:99:01", "11:22:33:44:55:AB", 41L);

        runMigration();

        assertEquals("尾号为ab的设备", aliasOf("55:66:77:88:99:01"));
    }

    @Test
    @DisplayName("target_mac 短于两位的行维持原样，算不出名字不硬造")
    void targetMacTooShortToNameIsLeftAlone() throws SQLException, IOException {
        insertBook("22:33:44:55:66:06", "a", 12L);

        runMigration();

        assertNull(aliasOf("22:33:44:55:66:06"));
    }

    @Test
    @DisplayName("拿掉撞车判断的话，串用户私名就会真的发生")
    void withoutTheCollisionGuardAnotherUsersNameLeaks() throws SQLException, IOException {
        sameDeviceRegisteredByTwoUsers();
        insertBook("22:33:44:55:66:01", "aa:bb:cc:dd:ee:01", 7L);
        insertBook("22:33:44:55:66:02", "AA:BB:CC:DD:EE:01", 8L);

        // 判重那句去掉就是原来的写法，从真实文件里改出来，改法变了这里会跟着变
        run(readChangelog().replace("HAVING COUNT(*) = 1", "HAVING COUNT(*) >= 1"));

        // 判重去掉之后填进去的只会是设备表里的某个名字，尾号兜底那条路走不到。
        // 至于 MySQL 挑中的是哪一行不确定，所以只断言名字来自那两台设备
        for (String filled : aliasesOf("22:33:44:55:66:01", "22:33:44:55:66:02")) {
            assertTrue(List.of("七号房投影", "公司会议室").contains(filled),
                    "拿掉判重之后本该填进设备表里的私有名，实际填的是 " + filled);
        }
    }

    @Test
    @DisplayName("两个迁移都跑过的状态上，重复组照样不会串名字")
    void nothingLeaksOnTheStateLeftByBothMigrations() throws SQLException, IOException {
        // 3457 那段迁移撞车的组整组不动，跑完还是这两种大小写写法。
        // 3457 的撞车判断是不区分大小写的，这组在它眼里也是一整组，
        // 所以它跑完之后重复的行只会更多不会更少。照这个跑完的样子摆数据，
        // 和先跑 3457 再跑 1400 是一回事
        insertDevice("dev-d1", "aa:bb:cc:dd:ee:01", "东厢房");
        insertDevice("dev-d2", "AA:BB:CC:DD:EE:01", "西厢房");
        insertBook("44:55:66:77:88:01", "aa:bb:cc:dd:ee:01", 31L);
        insertBook("44:55:66:77:88:02", "AA:BB:CC:DD:EE:01", 32L);

        runMigration();

        assertEquals("尾号为01的设备", aliasOf("44:55:66:77:88:01"));
        assertEquals("尾号为01的设备", aliasOf("44:55:66:77:88:02"));
    }

    @Test
    @DisplayName("重复 MAC 的排查语句跑得出那几行")
    void theDuplicateDiagnosticFindsTheCollidingGroups() throws SQLException, IOException {
        sameDeviceRegisteredByTwoUsers();
        insertDevice("dev-u9", "11:22:33:44:55:66", "客厅音响");

        List<String> colliding = queryColumn(diagnostic(), 0);

        assertEquals(1, colliding.size(), "只有一组撞车，诊断语句报出来 " + colliding);
        assertTrue(colliding.get(0).toLowerCase().contains("ee:01"),
                "报出来的不是撞车的那一组：" + colliding);
    }

    // ── 建数 ────────────────────────────────────────────────────────────────

    /** 同一台设备被两个用户各登记一次，MAC 写法还不一样 */
    private void sameDeviceRegisteredByTwoUsers() throws SQLException {
        insertDevice("dev-u7", "aa:bb:cc:dd:ee:01", "七号房投影");
        insertDevice("dev-u8", "AA:BB:CC:DD:EE:01", "公司会议室");
    }

    private void insertDevice(String id, String mac, String alias) throws SQLException {
        execute(("INSERT INTO `%s`.`ai_device` (`id`, `mac_address`, `alias`)"
                + " VALUES ('%s', '%s', %s)")
                .formatted(SCHEMA, id, mac, alias == null ? "NULL" : "'" + alias + "'"));
    }

    private void insertBook(String macAddress, String targetMac, long creator) throws SQLException {
        execute(("INSERT INTO `%s`.`ai_device_address_book`"
                + " (`mac_address`, `target_mac`, `alias`, `creator`) VALUES ('%s', '%s', NULL, %d)")
                .formatted(SCHEMA, macAddress, targetMac, creator));
    }

    private void setAliasToNull(String macAddress) throws SQLException {
        execute(("UPDATE `%s`.`ai_device_address_book` SET `alias` = NULL"
                + " WHERE `mac_address` = '%s'").formatted(SCHEMA, macAddress));
    }

    // ── 查结果 ──────────────────────────────────────────────────────────────

    private String aliasOf(String macAddress) throws SQLException {
        List<String> found = queryColumn("""
                SELECT `alias` FROM `%s`.`ai_device_address_book` WHERE `mac_address` = '%s'
                """.formatted(SCHEMA, macAddress), 0);
        assertFalse(found.isEmpty(), "通讯录里没有 " + macAddress + " 这一行");
        return found.get(0);
    }

    private List<String> aliasesOf(String... macAddresses) throws SQLException {
        String list = String.join("', '", macAddresses);
        return queryColumn("""
                SELECT `alias` FROM `%s`.`ai_device_address_book`
                WHERE `mac_address` IN ('%s') ORDER BY `mac_address`
                """.formatted(SCHEMA, list), 0);
    }

    private List<String> queryColumn(String sql, int column) throws SQLException {
        List<String> values = new ArrayList<>();
        try (Statement statement = connection.createStatement(); ResultSet rows = statement.executeQuery(sql)) {
            while (rows.next()) {
                // JDBC 的列下标从 1 开始
                values.add(rows.getString(column + 1));
            }
        }
        return values;
    }

    // ── 跑迁移 ──────────────────────────────────────────────────────────────

    private void runMigration() throws SQLException, IOException {
        run(readChangelog());
    }

    /** 脚本整段执行，一个事务，中间失败就整体回滚 */
    private void run(String script) throws SQLException {
        connection.setAutoCommit(false);
        try (Statement statement = connection.createStatement()) {
            for (String one : splitStatements(script)) {
                statement.execute(one);
            }
            connection.commit();
        } catch (SQLException e) {
            connection.rollback();
            throw e;
        } finally {
            connection.setAutoCommit(true);
        }
    }

    /** 从文件尾部那段注释里取出排查用的 SQL，逐行抠出来自己跑一遍 */
    private String diagnostic() throws IOException {
        List<String> collected = new ArrayList<>();
        boolean inBlock = false;
        for (String line : readChangelog().split("\n")) {
            if (!line.stripLeading().startsWith("--")) {
                if (!collected.isEmpty()) {
                    break;
                }
                continue;
            }
            if (!inBlock) {
                inBlock = line.contains("COUNT(*) AS `n`");
                if (!inBlock) {
                    continue;
                }
            }
            String body = line.stripLeading().substring(2).strip();
            if (collected.isEmpty() && !body.startsWith("SELECT")) {
                continue;
            }
            collected.add(body);
            if (body.endsWith(";")) {
                break;
            }
        }
        assertFalse(collected.isEmpty(), "脚本里找不到排查重复 MAC 那段 SQL");
        return String.join("\n", collected).replace("`ai_device`", "`" + SCHEMA + "`.`ai_device`");
    }

    private static String readChangelog() throws IOException {
        return Files.readString(
                Path.of("src/main/resources/db/changelog/202610231400.sql"),
                StandardCharsets.UTF_8);
    }

    /** 按分号切句，注释行先去掉，免得注释里的分号把语句切碎 */
    private static List<String> splitStatements(String sql) {
        StringBuilder stripped = new StringBuilder();
        for (String line : sql.split("\n")) {
            if (!line.stripLeading().startsWith("--")) {
                stripped.append(line).append('\n');
            }
        }
        List<String> statements = new ArrayList<>();
        for (String piece : stripped.toString().split(";")) {
            if (!piece.isBlank()) {
                statements.add(piece.strip());
            }
        }
        return statements;
    }

    private void execute(String sql) throws SQLException {
        try (Statement statement = connection.createStatement()) {
            statement.execute(sql);
        }
    }
}