package xiaozhi.modules.sys;

import liquibase.Contexts;
import liquibase.LabelExpression;
import liquibase.Liquibase;
import liquibase.database.Database;
import liquibase.database.DatabaseFactory;
import liquibase.database.jvm.JdbcConnection;
import liquibase.resource.DirectoryResourceAccessor;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

class LiquibaseWesternizationIntegrationTest {

    private static final String JDBC_URL =
        "jdbc:h2:mem:liquibase_westernization;MODE=MySQL;DB_CLOSE_DELAY=-1;DB_CLOSE_ON_EXIT=FALSE";
    private static final Pattern HAN_PATTERN = Pattern.compile("\\p{IsHan}");
    private static final Pattern CHINESE_TOKEN_PATTERN = Pattern.compile("zh" + "-CN|zh" + "-HK|zh_cn|" + "\u4e2d\u6587|\u5c0f\u667a|\u5929\u6c14|\u65b0\u95fb|\u89d2\u8272|\u6a21\u677f");
    @Test
    void shouldApplyAllChangelogsAndProduceWesternizedSeedData() throws Exception {
        try (Connection migrationConnection = DriverManager.getConnection(JDBC_URL, "sa", "")) {
            applyLiquibase(migrationConnection);
        }

        try (Connection verificationConnection = DriverManager.getConnection(JDBC_URL, "sa", "")) {
            writeSeedDump(verificationConnection);

            assertLatestChangeSetApplied(verificationConnection);
            assertRequiredSeedCoverage(verificationConnection);
            assertWesternizationRules(verificationConnection);
        }
    }

    private void applyLiquibase(Connection connection) throws Exception {
        Path changelogRoot = prepareH2ChangelogWorkspace();
        createH2CompatibilityAliases(connection);
        try (JdbcConnection jdbcConnection = new JdbcConnection(connection)) {
            Database database = DatabaseFactory.getInstance()
                .findCorrectDatabaseImplementation(jdbcConnection);
            Liquibase liquibase = new Liquibase(
                "db.changelog-master.yaml",
                new DirectoryResourceAccessor(changelogRoot),
                database
            );
            liquibase.update(new Contexts(), new LabelExpression());
        }
    }

    private void createH2CompatibilityAliases(Connection connection) throws SQLException {
        try (Statement statement = connection.createStatement()) {
            statement.execute(
                "CREATE ALIAS IF NOT EXISTS JSON_SET FOR " +
                    "'xiaozhi.modules.sys.H2JsonFunctions.jsonSet'"
            );
            statement.execute(
                "CREATE ALIAS IF NOT EXISTS JSON_REMOVE FOR " +
                    "'xiaozhi.modules.sys.H2JsonFunctions.jsonRemove'"
            );
            statement.execute(
                "CREATE ALIAS IF NOT EXISTS JSON_EXTRACT FOR " +
                    "'xiaozhi.modules.sys.H2JsonFunctions.jsonExtract'"
            );
            statement.execute(
                "CREATE ALIAS IF NOT EXISTS JSON_UNQUOTE FOR " +
                    "'xiaozhi.modules.sys.H2JsonFunctions.jsonUnquote'"
            );
            statement.execute(
                "CREATE ALIAS IF NOT EXISTS FILTER_PROVIDER_FIELDS FOR " +
                    "'xiaozhi.modules.sys.H2JsonFunctions.filterProviderFields'"
            );
        }
    }

    private Path prepareH2ChangelogWorkspace() throws IOException {
        Path sourceRoot = Path.of("src", "main", "resources", "db", "changelog").toAbsolutePath().normalize();
        Path workspace = Path.of("target", "liquibase-h2-changelog").toAbsolutePath().normalize();

        if (Files.exists(workspace)) {
            try (var paths = Files.walk(workspace)) {
                paths.sorted((left, right) -> right.getNameCount() - left.getNameCount())
                    .forEach(path -> {
                        try {
                            Files.delete(path);
                        } catch (IOException e) {
                            throw new RuntimeException(e);
                        }
                    });
            }
        }

        Files.createDirectories(workspace);
        try (var paths = Files.walk(sourceRoot)) {
            paths.forEach(source -> {
                try {
                    Path relative = sourceRoot.relativize(source);
                    Path target = workspace.resolve(relative.toString());
                    if (Files.isDirectory(source)) {
                        Files.createDirectories(target);
                    } else if (source.getFileName().toString().endsWith(".yaml")) {
                        String yaml = Files.readString(source);
                        yaml = yaml.replace("path: classpath:db/changelog/", "path: ");
                        Files.writeString(target, yaml, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING);
                    } else if (source.getFileName().toString().endsWith(".sql")) {
                        String sql = normalizeSqlForH2(Files.readString(source), source.getFileName().toString());
                        Files.writeString(target, sql, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING);
                    } else {
                        Files.copy(source, target, StandardCopyOption.REPLACE_EXISTING);
                    }
                } catch (IOException e) {
                    throw new RuntimeException(e);
                }
            });
        }

        return workspace;
    }

    private String normalizeSqlForH2(String sql, String fileName) {
        String normalized = sql;
        normalized = normalized.replaceAll("(?im)(INDEX\\s+`[^`]+`\\s*\\([^\\n]+\\))\\s+COMMENT\\s+'[^']*'", "$1");
        normalized = normalized.replaceAll("(?im)(UNIQUE\\s+KEY\\s+`[^`]+`\\s*\\([^\\n]+\\))\\s+COMMENT\\s+'[^']*'", "$1");
        normalized = normalized.replaceAll("(?im)(KEY\\s+`[^`]+`\\s*\\([^\\n]+\\))\\s+COMMENT\\s+'[^']*'", "$1");
        normalized = normalized.replaceAll("(?im)\\)\\s*ENGINE=.*?;", ");");
        normalized = normalized.replaceAll("(?i)\\s+ON\\s+UPDATE\\s+CURRENT_TIMESTAMP(?:\\(\\d+\\))?", "");
        normalized = normalized.replaceAll("(?im)^\\s*START\\s+TRANSACTION\\s*;?\\s*$", "");
        normalized = normalized.replaceAll("(?im)^\\s*COMMIT\\s*;?\\s*$", "");
        normalized = normalized.replaceAll("(?i)\\s+AFTER\\s+`[^`]+`", "");
        normalized = rewriteConditionalInsertBlocks(normalized);
        normalized = rewriteConditionalAddColumnBlocks(normalized);
        normalized = normalized.replace("TINYINT UNSIGNED", "TINYINT");
        normalized = normalized.replace("INT UNSIGNED", "INT");
        normalized = normalized.replace("BIGINT UNSIGNED", "BIGINT");
        normalized = normalized.replace("tinyint unsigned", "tinyint");
        normalized = normalized.replace("int unsigned", "int");
        normalized = normalized.replace("bigint unsigned", "bigint");
        normalized = rewriteCreateTableIndexNames(normalized);
        if ("202605251426.sql".equals(fileName)) {
            normalized = normalized.replaceAll(
                "(?s)UPDATE sys_params\\s*SET param_value = CAST\\(\\s*JSON_SET\\(.*?\\) AS CHAR\\s*\\)\\s*WHERE param_code = 'system-web\\.menu'\\s*AND NOT JSON_CONTAINS_PATH\\([^;]+;",
                Matcher.quoteReplacement("""
UPDATE sys_params
SET param_value = JSON_SET(
    CAST(param_value AS VARCHAR),
    '$.addressBook',
    '{"name":"feature.addressBook.name","enabled":false,"description":"feature.addressBook.description"}'
)
WHERE param_code = 'system-web.menu'
  AND JSON_EXTRACT(CAST(param_value AS VARCHAR), '$.addressBook') IS NULL;
""")
            );
        }
        if ("202606131400.sql".equals(fileName)) {
            return """
UPDATE sys_params
SET param_value = JSON_SET(
    CAST(param_value AS VARCHAR),
    '$.features.addressBook',
    JSON_UNQUOTE(JSON_EXTRACT(CAST(param_value AS VARCHAR), '$.addressBook'))
)
WHERE param_code = 'system-web.menu'
  AND JSON_EXTRACT(CAST(param_value AS VARCHAR), '$.addressBook') IS NOT NULL
  AND JSON_EXTRACT(CAST(param_value AS VARCHAR), '$.features.addressBook') IS NULL;

UPDATE sys_params
SET param_value = JSON_REMOVE(CAST(param_value AS VARCHAR), '$.addressBook')
WHERE param_code = 'system-web.menu'
  AND JSON_EXTRACT(CAST(param_value AS VARCHAR), '$.addressBook') IS NOT NULL;

UPDATE sys_params
SET param_value = JSON_SET(
    CAST(param_value AS VARCHAR),
    '$.features.addressBook',
    '{"name":"feature.addressBook.name","enabled":true,"description":"feature.addressBook.description"}'
)
WHERE param_code = 'system-web.menu'
  AND JSON_EXTRACT(CAST(param_value AS VARCHAR), '$.features.addressBook') IS NULL;

UPDATE sys_params
SET param_value = JSON_SET(
    CAST(param_value AS VARCHAR),
    '$.features.voiceClone.enabled', 'true',
    '$.features.knowledgeBase.enabled', 'true',
    '$.features.addressBook.enabled', 'true'
)
WHERE param_code = 'system-web.menu';

UPDATE sys_params
SET param_value = JSON_SET(
    CAST(param_value AS VARCHAR),
    '$.groups.featureManagement',
    '["voiceprintRecognition","voiceClone","knowledgeBase","mcpAccessPoint","addressBook"]'
)
WHERE param_code = 'system-web.menu';
""";
        }
        if ("202606131500.sql".equals(fileName)) {
            return """
UPDATE ai_model_config
SET is_enabled = 1
WHERE id IN (
    'LLM_OpenAILLM',
    'TTS_EdgeTTS',
    'VAD_SileroVAD',
    'ASR_VoskASR',
    'ASR_GroqASR',
    'ASR_OpenaiASR',
    'Intent_function_call',
    'Memory_nomem',
    'VLLM_OpenAILLMVLLM'
)
  AND is_enabled = 0;

UPDATE ai_model_config
SET config_json = JSON_SET(CAST(config_json AS VARCHAR), '$.llm', 'LLM_OpenAILLM')
WHERE id = 'Memory_mem_local_short'
  AND JSON_UNQUOTE(JSON_EXTRACT(CAST(config_json AS VARCHAR), '$.llm')) = 'LLM_ChatGLMLLM';

UPDATE sys_params
SET param_value = JSON_SET(
    CAST(param_value AS VARCHAR),
    '$.features.vad.enabled', 'true',
    '$.features.asr.enabled', 'true'
)
WHERE param_code = 'system-web.menu';
""";
        }
        if ("202601141645.sql".equals(fileName)) {
            normalized = normalized.replaceAll(
                "(?s)UPDATE `ai_model_provider` ap\\s+JOIN \\(.*?\\) filtered ON ap\\.id = filtered\\.id\\s+SET ap\\.fields = filtered\\.new_fields;",
                Matcher.quoteReplacement("""
UPDATE `ai_model_provider` ap
SET ap.fields = FILTER_PROVIDER_FIELDS(ap.`fields`, 'sample_rate')
WHERE ap.`model_type` = 'TTS';
""")
            );
        }
        if ("202603091051.sql".equals(fileName)) {
            normalized = normalized.replaceAll(
                "(?s)SET @col_exists = .*?COLUMN_NAME = 'sort'\\);\\s*" +
                    "SET @sql = IF\\(@col_exists > 0 AND \\(SELECT COUNT\\(\\*\\) FROM ai_agent_tag_relation WHERE sort = 0\\) > 0,\\s*" +
                    "'UPDATE ai_agent_tag_relation r INNER JOIN \\(SELECT id, ROW_NUMBER\\(\\) OVER \\(PARTITION BY agent_id ORDER BY created_at\\) AS row_num FROM ai_agent_tag_relation\\) t ON r\\.id = t\\.id SET r\\.sort = t\\.row_num',\\s*" +
                    "'SELECT ''No need to update or column does not exist'' AS msg'\\);\\s*" +
                    "PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;",
                Matcher.quoteReplacement("""
UPDATE ai_agent_tag_relation r
SET sort = (
    SELECT ranked.row_num
    FROM (
        SELECT id, ROW_NUMBER() OVER (PARTITION BY agent_id ORDER BY created_at) AS row_num
        FROM ai_agent_tag_relation
    ) ranked
    WHERE ranked.id = r.id
)
WHERE r.sort = 0;
""")
            );
        }
        if (fileName.compareTo("202506091720.sql") >= 0) {
            normalized = normalized.replace(
                "INSERT INTO `ai_tts_voice` VALUES",
                "INSERT INTO `ai_tts_voice` (`id`, `tts_model_id`, `name`, `tts_voice`, `languages`, `voice_demo`, `remark`, `reference_audio`, `reference_text`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES"
            );
        }
        normalized = splitMultiAddColumnAlterStatements(normalized);
        normalized = normalizeJsonSetCalls(normalized);
        normalized = convertDoubleQuotedStringLiterals(normalized);
        return normalized;
    }

    /**
     * H2 (unlike MySQL) parses "..." as an identifier, not a string literal.
     * Walk the SQL with a small state machine so only true double-quoted string
     * literals are rewritten to single-quoted form; single-quoted payloads and
     * backtick identifiers are copied through untouched.
     */
    private String convertDoubleQuotedStringLiterals(String sql) {
        StringBuilder out = new StringBuilder(sql.length());
        int i = 0;
        int n = sql.length();
        while (i < n) {
            char c = sql.charAt(i);
            if (c == '-' && i + 1 < n && sql.charAt(i + 1) == '-') {
                int end = sql.indexOf('\n', i);
                if (end < 0) {
                    end = n;
                }
                out.append(sql, i, end);
                i = end;
                continue;
            }
            if (c == '/' && i + 1 < n && sql.charAt(i + 1) == '*') {
                int end = sql.indexOf("*/", i + 2);
                if (end < 0) {
                    end = n;
                } else {
                    end += 2;
                }
                out.append(sql, i, end);
                i = end;
                continue;
            }
            if (c == '`') {
                int end = sql.indexOf('`', i + 1);
                if (end < 0) {
                    end = n - 1;
                }
                out.append(sql, i, end + 1);
                i = end + 1;
                continue;
            }
            if (c == '\'') {
                int j = i + 1;
                StringBuilder body = new StringBuilder("'");
                while (j < n) {
                    char d = sql.charAt(j);
                    if (d == '\\' && j + 1 < n) {
                        body.append(d).append(sql.charAt(j + 1));
                        j += 2;
                        continue;
                    }
                    if (d == '\'') {
                        if (j + 1 < n && sql.charAt(j + 1) == '\'') {
                            body.append("''");
                            j += 2;
                            continue;
                        }
                        body.append('\'');
                        j++;
                        break;
                    }
                    body.append(d);
                    j++;
                }
                out.append(body);
                i = j;
                continue;
            }
            if (c == '"') {
                StringBuilder content = new StringBuilder();
                int j = i + 1;
                boolean closed = false;
                while (j < n) {
                    char d = sql.charAt(j);
                    if (d == '\\' && j + 1 < n) {
                        if (sql.charAt(j + 1) == '"') {
                            content.append('"');
                        } else {
                            content.append(d).append(sql.charAt(j + 1));
                        }
                        j += 2;
                        continue;
                    }
                    if (d == '"') {
                        if (j + 1 < n && sql.charAt(j + 1) == '"') {
                            content.append('"');
                            j += 2;
                            continue;
                        }
                        closed = true;
                        j++;
                        break;
                    }
                    content.append(d);
                    j++;
                }
                if (!closed) {
                    // unterminated; copy through unchanged
                    out.append(sql, i, j);
                    i = j;
                    continue;
                }
                out.append('\'').append(content.toString().replace("'", "''")).append('\'');
                i = j;
                continue;
            }
            out.append(c);
            i++;
        }
        return out.toString();
    }

    /**
     * H2 does not support multiple clauses in one ALTER TABLE, so split any
     * top-level comma inside ALTER TABLE ... ; into separate statements.
     * Commas inside parentheses or quotes are ignored.
     */
    private String splitMultiAddColumnAlterStatements(String sql) {
        StringBuilder out = new StringBuilder(sql.length());
        int i = 0;
        int n = sql.length();
        while (i < n) {
            // Never touch line comments (e.g. "-- rollback ALTER TABLE ..."):
            // splitting them would turn commented SQL into live statements.
            int lineEnd = sql.indexOf('\n', i);
            if (lineEnd < 0) {
                lineEnd = n;
            }
            String line = sql.substring(i, Math.min(lineEnd, n));
            if (line.isBlank() || line.stripLeading().startsWith("--")) {
                out.append(sql, i, Math.min(lineEnd + 1, n));
                i = Math.min(lineEnd + 1, n);
                continue;
            }
            int alterAt = sql.regionMatches(true, i, "ALTER TABLE", 0, 11) ? i : findAlter(sql, i);
            if (alterAt < 0) {
                out.append(sql, i, n);
                break;
            }
            if (alterAt > i && sql.substring(i, alterAt).contains("\n--")) {
                // an ALTER found on a line after a comment line: defer to line loop
                int nextBreak = sql.indexOf('\n', i) + 1;
                out.append(sql, i, nextBreak);
                i = nextBreak;
                continue;
            }
            // locate the terminating semicolon of this statement (quote-aware)
            int end = statementEnd(sql, alterAt);
            String stmt = sql.substring(alterAt, end + 1);
            String split = splitAlterStatement(stmt);
            out.append(sql, i, alterAt).append(split);
            i = end + 1;
        }
        return out.toString();
    }

    private int findAlter(String sql, int from) {
        boolean lineStart = from == 0 || sql.charAt(from - 1) == '\n';
        for (int j = from; j + 11 <= sql.length(); j++) {
            char c = sql.charAt(j);
            if (c == '\n') {
                lineStart = true;
                continue;
            }
            if (lineStart && !Character.isWhitespace(c) && sql.regionMatches(j, "--", 0, 2)) {
                int eol = sql.indexOf('\n', j);
                j = (eol < 0) ? sql.length() : eol - 1;  // skip whole comment line
                continue;
            }
            if (lineStart && !Character.isWhitespace(c)) {
                lineStart = false;
            }
            if (sql.regionMatches(true, j, "ALTER TABLE", 0, 11)
                    && (j == 0 || sql.charAt(j - 1) == '\n' || Character.isWhitespace(sql.charAt(j - 1)))) {
                return j;
            }
        }
        return -1;
    }

    private int statementEnd(String sql, int from) {
        boolean inSingle = false;
        boolean inDouble = false;
        boolean inBacktick = false;
        for (int j = from; j < sql.length(); j++) {
            char c = sql.charAt(j);
            if (c == '\\' && (inSingle || inDouble)) {
                j++;
                continue;
            }
            if (c == '\'' && !inDouble && !inBacktick) {
                inSingle = !inSingle;
            } else if (c == '"' && !inSingle && !inBacktick) {
                inDouble = !inDouble;
            } else if (c == '`' && !inSingle && !inDouble) {
                inBacktick = !inBacktick;
            } else if (c == ';' && !inSingle && !inDouble && !inBacktick) {
                return j;
            }
        }
        return sql.length() - 1;
    }

    private String splitAlterStatement(String stmt) {
        // strip trailing semicolon
        String body = stmt.trim();
        if (body.endsWith(";")) {
            body = body.substring(0, body.length() - 1);
        }
        List<String> parts = new ArrayList<>();
        int depth = 0;
        boolean inSingle = false;
        boolean inDouble = false;
        boolean inBacktick = false;
        StringBuilder current = new StringBuilder();
        for (int j = 0; j < body.length(); j++) {
            char c = body.charAt(j);
            if (c == '\\' && (inSingle || inDouble)) {
                current.append(c);
                if (j + 1 < body.length()) {
                    current.append(body.charAt(++j));
                }
                continue;
            }
            if (c == '\'' && !inDouble && !inBacktick) {
                inSingle = !inSingle;
            } else if (c == '"' && !inSingle && !inBacktick) {
                inDouble = !inDouble;
            } else if (c == '`' && !inSingle && !inDouble) {
                inBacktick = !inBacktick;
            } else if (!inSingle && !inDouble && !inBacktick) {
                if (c == '(') {
                    depth++;
                } else if (c == ')') {
                    depth--;
                } else if (c == ',' && depth == 0) {
                    parts.add(current.toString());
                    current.setLength(0);
                    continue;
                }
            }
            current.append(c);
        }
        parts.add(current.toString());
        if (parts.size() <= 1) {
            return stmt;
        }
        Matcher header = Pattern.compile("(?is)^(ALTER\\s+TABLE\\s+`?\\w+`?)\\s*(.*)$")
            .matcher(parts.get(0).trim());
        if (!header.matches()) {
            return stmt;
        }
        String table = header.group(1);
        StringBuilder rebuilt = new StringBuilder();
        List<String> clauses = new ArrayList<>();
        if (!header.group(2).isBlank()) {
            clauses.add(header.group(2).trim());
        }
        for (int p = 1; p < parts.size(); p++) {
            if (!parts.get(p).trim().isEmpty()) {
                clauses.add(parts.get(p).trim());
            }
        }
        if (clauses.size() <= 1) {
            return stmt;
        }
        for (String clause : clauses) {
            rebuilt.append(table).append(' ').append(clause).append(";\n");
        }
        return rebuilt.toString();
    }

    private String normalizeJsonSetCalls(String sql) {
        String marker = "JSON_SET(";
        StringBuilder normalized = new StringBuilder();
        int cursor = 0;
        while (true) {
            int start = sql.indexOf(marker, cursor);
            if (start < 0) {
                normalized.append(sql.substring(cursor));
                return normalized.toString();
            }
            normalized.append(sql, cursor, start);
            int end = findMatchingParenthesis(sql, start + marker.length() - 1);
            String body = sql.substring(start + marker.length(), end);
            normalized.append("JSON_SET(").append(rewriteJsonSetBody(body)).append(")");
            cursor = end + 1;
        }
    }

    private String rewriteConditionalInsertBlocks(String sql) {
        Pattern pattern = Pattern.compile(
            "(?s)SET @data_exists = \\(SELECT COUNT\\(\\*\\) FROM ([^)]+)\\);\\s*" +
                "SET @sql = IF\\(@data_exists = 0,\\s*'(INSERT INTO .*?)',\\s*'SELECT .*?' AS msg'\\);\\s*" +
                "PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;"
        );

        Matcher matcher = pattern.matcher(sql);
        StringBuffer rewritten = new StringBuffer();
        while (matcher.find()) {
            String tableClause = matcher.group(1).trim();
            String insertStatement = matcher.group(2).replace("''", "'").replaceAll("\\s+", " ");
            Pattern valuesPattern = Pattern.compile(
                "(?is)^INSERT INTO\\s+(`[^`]+`\\s*\\([^)]+\\))\\s*VALUES\\s*(\\(.+\\))\\s*$"
            );
            Matcher valuesMatcher = valuesPattern.matcher(insertStatement.trim());
            String replacement;
            if (valuesMatcher.matches()) {
                String valuesBody = valuesMatcher.group(2);
                replacement =
                    "INSERT INTO " + valuesMatcher.group(1) +
                        " SELECT " + valuesBody.substring(1, valuesBody.length() - 1) +
                        " WHERE NOT EXISTS (SELECT 1 FROM " + tableClause + ");";
            } else {
                replacement = insertStatement + ";";
            }
            matcher.appendReplacement(rewritten, Matcher.quoteReplacement(replacement));
        }
        matcher.appendTail(rewritten);
        return rewritten.toString();
    }

    private String rewriteConditionalAddColumnBlocks(String sql) {
        Pattern pattern = Pattern.compile(
            "(?s)SET @col_exists = .*?;\\s*" +
                "SET @sql = IF\\(@col_exists = 0, '(ALTER TABLE .*?)', 'SELECT .*?' AS msg'\\);\\s*" +
                "PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;"
        );

        Matcher matcher = pattern.matcher(sql);
        StringBuffer rewritten = new StringBuffer();
        while (matcher.find()) {
            String statement = matcher.group(1).replace("''", "'");
            statement = statement.replaceAll("(?i)\\s+COMMENT\\s+'[^']*'", "");
            statement = statement.replaceAll("(?i)\\s+AFTER\\s+`[^`]+`", "");
            statement = statement.replaceFirst("(?i)ADD\\s+COLUMN\\s+", "ADD COLUMN IF NOT EXISTS ");
            matcher.appendReplacement(rewritten, Matcher.quoteReplacement(statement + ";"));
        }
        matcher.appendTail(rewritten);
        return rewritten.toString();
    }

    private String rewriteCreateTableIndexNames(String sql) {
        Pattern tablePattern = Pattern.compile("(?is)CREATE\\s+TABLE\\s+IF\\s+NOT\\s+EXISTS\\s+`?(\\w+)`?\\s*\\((.*?)\\);");
        Matcher matcher = tablePattern.matcher(sql);
        StringBuffer rewritten = new StringBuffer();
        while (matcher.find()) {
            String tableName = matcher.group(1);
            String tableBody = matcher.group(2);
            tableBody = tableBody.replaceAll(
                "(?im)(\\bINDEX\\s+)`?(\\w+)`?(\\s*\\()",
                "$1" + tableName + "_$2$3"
            );
            matcher.appendReplacement(
                rewritten,
                Matcher.quoteReplacement("CREATE TABLE IF NOT EXISTS " + tableName + " (" + tableBody + ");")
            );
        }
        matcher.appendTail(rewritten);
        return rewritten.toString();
    }

    private String rewriteJsonSetBody(String body) {
        List<String> parts = splitTopLevelCommaSeparated(body);
        for (int i = 2; i < parts.size(); i += 2) {
            String value = parts.get(i).trim();
            parts.set(i, "CAST(" + value + " AS VARCHAR)");
        }
        return String.join(", ", parts);
    }

    private int findMatchingParenthesis(String sql, int openParenIndex) {
        int depth = 0;
        boolean inSingleQuote = false;
        boolean inDoubleQuote = false;
        for (int i = openParenIndex; i < sql.length(); i++) {
            char c = sql.charAt(i);
            if (c == '\'' && !inDoubleQuote && !isEscaped(sql, i)) {
                inSingleQuote = !inSingleQuote;
                continue;
            }
            if (c == '"' && !inSingleQuote && !isEscaped(sql, i)) {
                inDoubleQuote = !inDoubleQuote;
                continue;
            }
            if (inSingleQuote || inDoubleQuote) {
                continue;
            }
            if (c == '(') {
                depth++;
            } else if (c == ')') {
                depth--;
                if (depth == 0) {
                    return i;
                }
            }
        }
        throw new IllegalArgumentException("Unbalanced JSON_SET expression in rewritten changelog SQL");
    }

    private List<String> splitTopLevelCommaSeparated(String value) {
        List<String> parts = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        int depth = 0;
        boolean inSingleQuote = false;
        boolean inDoubleQuote = false;

        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (c == '\'' && !inDoubleQuote && !isEscaped(value, i)) {
                inSingleQuote = !inSingleQuote;
                current.append(c);
                continue;
            }
            if (c == '"' && !inSingleQuote && !isEscaped(value, i)) {
                inDoubleQuote = !inDoubleQuote;
                current.append(c);
                continue;
            }
            if (!inSingleQuote && !inDoubleQuote) {
                if (c == '(') {
                    depth++;
                } else if (c == ')') {
                    depth--;
                } else if (c == ',' && depth == 0) {
                    parts.add(current.toString().trim());
                    current.setLength(0);
                    continue;
                }
            }
            current.append(c);
        }
        parts.add(current.toString().trim());
        return parts;
    }

    private boolean isEscaped(String value, int index) {
        int backslashCount = 0;
        for (int i = index - 1; i >= 0 && value.charAt(i) == '\\'; i--) {
            backslashCount++;
        }
        return backslashCount % 2 == 1;
    }

    private void writeSeedDump(Connection connection) throws IOException, SQLException {
        Path dumpPath = Path.of("target", "liquibase-h2-seed-dump.txt");
        Files.createDirectories(dumpPath.getParent());

        List<String> lines = new ArrayList<>();
        dumpTable(connection, lines, "DATABASECHANGELOG",
            "SELECT ID, AUTHOR, FILENAME, ORDEREXECUTED FROM DATABASECHANGELOG ORDER BY ORDEREXECUTED");
        dumpTable(connection, lines, "sys_params",
            "SELECT param_code, param_value, remark FROM sys_params ORDER BY param_code");
        dumpTable(connection, lines, "sys_dict_type",
            "SELECT id, dict_type, dict_name, remark FROM sys_dict_type ORDER BY id");
        dumpTable(connection, lines, "sys_dict_data",
            "SELECT id, dict_type_id, dict_label, dict_value, remark FROM sys_dict_data ORDER BY id");
        dumpTable(connection, lines, "ai_model_provider",
            "SELECT id, model_type, provider_code, name, fields FROM ai_model_provider ORDER BY id");
        dumpTable(connection, lines, "ai_model_config",
            "SELECT id, model_type, model_code, model_name, is_enabled, config_json, remark FROM ai_model_config ORDER BY id");
        dumpTable(connection, lines, "ai_agent_template",
            "SELECT id, agent_code, agent_name, lang_code, language, sort FROM ai_agent_template ORDER BY sort, id");
        dumpTable(connection, lines, "ai_tts_voice",
            "SELECT id, tts_model_id, name, tts_voice, languages FROM ai_tts_voice ORDER BY tts_model_id, sort, id");

        Files.write(
            dumpPath,
            lines,
            StandardOpenOption.CREATE,
            StandardOpenOption.TRUNCATE_EXISTING,
            StandardOpenOption.WRITE
        );
    }

    private void dumpTable(Connection connection, List<String> lines, String title, String sql) throws SQLException {
        lines.add("== " + title + " ==");
        try (Statement statement = connection.createStatement();
             ResultSet resultSet = statement.executeQuery(sql)) {
            ResultSetMetaData metaData = resultSet.getMetaData();
            int columnCount = metaData.getColumnCount();
            while (resultSet.next()) {
                StringBuilder row = new StringBuilder();
                for (int i = 1; i <= columnCount; i++) {
                    if (i > 1) {
                        row.append(" | ");
                    }
                    row.append(metaData.getColumnLabel(i)).append('=').append(resultSet.getString(i));
                }
                lines.add(row.toString());
            }
        }
        lines.add("");
    }

    private void assertLatestChangeSetApplied(Connection connection) throws SQLException {
        String latestId = scalar(connection, "SELECT MAX(ID) FROM DATABASECHANGELOG");
        Assertions.assertEquals("202610111200", latestId, "latest downstream cleanup migration should be applied");
    }

    private void assertRequiredSeedCoverage(Connection connection) throws SQLException {
        assertExists(connection, "SELECT 1 FROM sys_params WHERE param_code = 'server.name' AND param_value = 'xiaozhi-esp32-server'");
        assertExists(connection, "SELECT 1 FROM ai_model_config WHERE id = 'LLM_OpenAILLM' AND is_enabled = 1");
        assertExists(connection, "SELECT 1 FROM ai_model_config WHERE id = 'TTS_EdgeTTS' AND is_enabled = 1");
        assertExists(connection, "SELECT 1 FROM ai_model_config WHERE id = 'VAD_SileroVAD' AND is_enabled = 1");
        assertExists(connection, "SELECT 1 FROM ai_model_config WHERE id = 'ASR_VoskASR' AND is_enabled = 1");
        assertExists(connection, "SELECT 1 FROM sys_params WHERE param_code = 'exit_commands' AND param_value = 'exit;close'");
        assertExists(connection, "SELECT 1 FROM sys_params WHERE param_code = 'plugins.get_weather.default_location' AND param_value = 'New York'");
        assertExists(connection, "SELECT 1 FROM sys_params WHERE param_code = 'plugins.get_news.default_rss_url' AND param_value = 'https://feeds.reuters.com/reuters/worldNews'");
        assertExists(connection, "SELECT 1 FROM sys_params WHERE param_code = 'plugins.home_assistant.devices' AND param_value LIKE 'Living Room,%Bedroom,%'");
        assertExists(connection, "SELECT 1 FROM sys_params WHERE param_code = 'end_prompt.prompt' AND param_value LIKE 'Please start with \"Time flies so fast\"%'");
        assertExists(connection, "SELECT 1 FROM sys_params WHERE param_code = 'system_error_response' AND param_value LIKE 'The assistant is temporarily busy right now.%'");
        assertExists(connection, "SELECT 1 FROM sys_params WHERE param_code = 'twilio.sms.account_sid'");
        assertExists(connection, "SELECT 1 FROM sys_params WHERE param_code = 'twilio.sms.auth_token'");
        assertExists(connection, "SELECT 1 FROM sys_params WHERE param_code = 'twilio.sms.phone_number'");
        assertExists(connection, "SELECT 1 FROM sys_params WHERE param_code = 'twilio.sms.template_message' AND param_value = 'Your verification code is: %s'");

        assertExists(connection, "SELECT 1 FROM sys_dict_type WHERE id = 101 AND dict_name = 'Firmware Type'");
        assertExists(connection, "SELECT 1 FROM sys_dict_type WHERE id = 102 AND dict_name = 'Mobile Area'");
        assertExists(connection, "SELECT 1 FROM sys_dict_data WHERE id = 101001 AND dict_label = 'Breadboard New Wiring (WiFi)'");
        assertExists(connection, "SELECT 1 FROM sys_dict_data WHERE id = 102005 AND dict_label = 'USA/Canada'");

        assertExists(connection, "SELECT 1 FROM ai_model_provider WHERE id = 'SYSTEM_PLUGIN_WEATHER' AND name = 'Weather Service'");
        assertExists(connection, "SELECT 1 FROM ai_model_provider WHERE id = 'SYSTEM_PLUGIN_NEWS' AND name = 'News Service'");
        assertExists(connection, "SELECT 1 FROM ai_model_provider WHERE id = 'SYSTEM_PLUGIN_HA_STATE' AND name = 'HomeAssistant Device Control'");
        assertExists(connection, "SELECT 1 FROM ai_model_provider WHERE id = 'SYSTEM_PLUGIN_HA_GET_CALENDAR' AND name = 'Standard Calendar Information Service'");
        assertExists(connection, "SELECT 1 FROM ai_model_provider WHERE id = 'SYSTEM_PLUGIN_CHANGE_ROLE' AND name = 'Role Switching Service'");
        assertExists(connection, "SELECT 1 FROM ai_model_provider WHERE id = 'SYSTEM_ASR_GeminiASR' AND name = 'Gemini Speech Recognition'");
        assertExists(connection, "SELECT 1 FROM ai_model_provider WHERE id = 'SYSTEM_ASR_GroqASR' AND name = 'Groq Speech Recognition'");
        assertExists(connection, "SELECT 1 FROM ai_model_provider WHERE id = 'SYSTEM_ASR_OpenaiASR' AND name = 'OpenAI Speech Recognition'");
        assertExists(connection, "SELECT 1 FROM ai_model_provider WHERE id = 'SYSTEM_ASR_WhisperASR' AND name = 'OpenAI Whisper Speech Recognition'");
        assertExists(connection, "SELECT 1 FROM ai_model_provider WHERE id = 'SYSTEM_ASR_VoskASR' AND name = 'VOSK Offline Speech Recognition'");
        assertExists(connection, "SELECT 1 FROM ai_model_provider WHERE id = 'SYSTEM_TTS_elevenlabs' AND name = 'ElevenLabs TTS'");
        assertExists(connection, "SELECT 1 FROM ai_model_provider WHERE id = 'SYSTEM_TTS_kokoro' AND name = 'Kokoro TTS'");

        assertExists(connection, "SELECT 1 FROM ai_model_config WHERE id = 'ASR_GeminiASR' AND model_name = 'Gemini Speech Recognition'");
        assertExists(connection, "SELECT 1 FROM ai_model_config WHERE id = 'ASR_GroqASR' AND model_name = 'Groq Speech Recognition'");
        assertExists(connection, "SELECT 1 FROM ai_model_config WHERE id = 'ASR_OpenaiASR' AND model_name = 'OpenAI Speech Recognition'");
        assertExists(connection, "SELECT 1 FROM ai_model_config WHERE id = 'ASR_WhisperASR' AND model_name = 'OpenAI Whisper Speech Recognition'");
        assertExists(connection, "SELECT 1 FROM ai_model_config WHERE id = 'ASR_VoskASR' AND model_name = 'VOSK Offline Speech Recognition'");
        assertExists(connection, "SELECT 1 FROM ai_model_config WHERE id = 'Intent_intent_llm' AND config_json LIKE '%LLM_OpenAILLM%'");
        assertExists(connection, "SELECT 1 FROM ai_model_config WHERE id = 'LLM_OpenAILLM' AND model_name = 'OpenAI GPT'");
        assertExists(connection, "SELECT 1 FROM ai_model_config WHERE id = 'TTS_EdgeTTS' AND config_json LIKE '%en-US-AriaNeural%'");
        assertExists(connection, "SELECT 1 FROM ai_model_config WHERE id = 'TTS_ElevenLabsTTS' AND model_name = 'ElevenLabs TTS'");
        assertExists(connection, "SELECT 1 FROM ai_model_config WHERE id = 'TTS_KokoroTTS' AND model_name = 'Kokoro TTS'");
        assertExists(connection, "SELECT 1 FROM ai_model_config WHERE id = 'VLLM_GeminiVLLM' AND model_name = 'Google Gemini Vision AI'");
        assertExists(connection, "SELECT 1 FROM ai_model_config WHERE id = 'VLLM_OpenAILLMVLLM' AND model_name = 'OpenAI Vision Model'");

        assertExists(connection, "SELECT 1 FROM ai_tts_voice WHERE id = 'TTS_EdgeTTS_EN001' AND name = 'Aria' AND tts_voice = 'en-US-AriaNeural'");
        assertExists(connection, "SELECT 1 FROM ai_tts_voice WHERE id = 'TTS_EdgeTTS_EN002' AND name = 'Guy'");
        assertExists(connection, "SELECT 1 FROM ai_tts_voice WHERE id = 'TTS_EdgeTTS_EN003' AND name = 'Sonia'");
        assertExists(connection, "SELECT 1 FROM ai_tts_voice WHERE id = 'TTS_OpenAITTS0002' AND name = 'Alloy'");
        assertExists(connection, "SELECT 1 FROM ai_tts_voice WHERE id = 'TTS_OpenAITTS0006' AND name = 'Shimmer'");
        assertExists(connection, "SELECT 1 FROM ai_tts_voice WHERE id = 'TTS_ElevenLabs_0001' AND name = 'Rachel'");
        assertExists(connection, "SELECT 1 FROM ai_tts_voice WHERE id = 'TTS_ElevenLabs_0018' AND name = 'Grace'");
        assertExists(connection, "SELECT 1 FROM ai_tts_voice WHERE id = 'TTS_Kokoro_0001' AND name = 'Alloy'");
        assertExists(connection, "SELECT 1 FROM ai_tts_voice WHERE id = 'TTS_Kokoro_0032' AND name = 'Kumo'");
        assertExists(connection, "SELECT 1 FROM ai_tts_voice WHERE id = 'TTS_Kokoro_0043' AND name = 'Nicola'");
        assertCount(connection, "SELECT COUNT(*) FROM ai_tts_voice WHERE tts_model_id = 'TTS_EdgeTTS'", 10, "Edge TTS voice parity should be restored");
        assertCount(connection, "SELECT COUNT(*) FROM ai_tts_voice WHERE tts_model_id = 'TTS_OpenAITTS'", 6, "OpenAI TTS voice parity should be restored");
        assertCount(connection, "SELECT COUNT(*) FROM ai_tts_voice WHERE tts_model_id = 'TTS_ElevenLabsTTS'", 18, "ElevenLabs TTS voice parity should be restored");
        assertCount(connection, "SELECT COUNT(*) FROM ai_tts_voice WHERE tts_model_id = 'TTS_KokoroTTS'", 35, "Kokoro non-Chinese voice parity should be restored");

        assertExists(connection, "SELECT 1 FROM ai_agent_template WHERE id = '9406648b5cc5fde1b8aa335b6f8b4f76' AND agent_name = 'Tech-Savvy Girl' AND lang_code = 'en'");
        assertExists(connection, "SELECT 1 FROM ai_agent_template WHERE id = '0ca32eb728c949e58b1000b2e401f90c' AND agent_name = 'Stellar Wanderer' AND lang_code = 'en'");
        assertExists(connection, "SELECT 1 FROM ai_agent_template WHERE id = '6c7d8e9f0a1b2c3d4e5f6a7b8c9d0s24' AND agent_name = 'English Teacher' AND lang_code = 'en'");
        assertExists(connection, "SELECT 1 FROM ai_agent_template WHERE id = 'e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b1' AND agent_name = 'Curious Boy' AND lang_code = 'en'");
        assertExists(connection, "SELECT 1 FROM ai_agent_template WHERE id = 'a45b6c7d8e9f0a1b2c3d4e5f6a7b8c92' AND agent_name = 'Paw Patrol Captain' AND lang_code = 'en'");
    }

    private void assertWesternizationRules(Connection connection) throws SQLException {
        assertMissing(connection, "SELECT 1 FROM ai_model_provider WHERE id = 'SYSTEM_PLUGIN_NEWS_CHINANEWS'");
        assertMissing(connection, "SELECT 1 FROM ai_model_provider WHERE id = 'SYSTEM_PLUGIN_NEWS_NEWSNOW'");
        assertMissing(connection, "SELECT 1 FROM ai_model_provider WHERE id = 'SYSTEM_ASR_SherpaASR'");
        assertMissing(connection, "SELECT 1 FROM ai_model_config WHERE id = 'ASR_SherpaASR'");
        assertMissing(connection, "SELECT 1 FROM ai_tts_voice WHERE tts_model_id = 'TTS_EdgeTTS' AND (tts_voice LIKE 'zh' || '-CN-%' OR tts_voice LIKE 'zh' || '-HK-%')");

        assertZero(connection,
            "SELECT COUNT(*) FROM ai_model_provider WHERE REGEXP_LIKE(COALESCE(name, '') || COALESCE(fields, ''), '[\\p{IsHan}]')",
            "provider rows should not contain Han-script");
        assertZero(connection,
            "SELECT COUNT(*) FROM ai_model_config WHERE REGEXP_LIKE(COALESCE(model_name, '') || COALESCE(remark, '') || COALESCE(CAST(config_json AS VARCHAR), ''), '[\\p{IsHan}]')",
            "model config rows should not contain Han-script");
        assertZero(connection,
            "SELECT COUNT(*) FROM ai_agent_template WHERE REGEXP_LIKE(COALESCE(agent_code, '') || COALESCE(agent_name, '') || COALESCE(system_prompt, '') || COALESCE(language, ''), '[\\p{IsHan}]')",
            "agent template rows should not contain Han-script");
        assertZero(connection,
            "SELECT COUNT(*) FROM sys_params WHERE REGEXP_LIKE(COALESCE(param_value, '') || COALESCE(remark, ''), '[\\p{IsHan}]')",
            "sys_params rows should not contain Han-script");
        assertZero(connection,
            "SELECT COUNT(*) FROM sys_dict_type WHERE REGEXP_LIKE(COALESCE(dict_name, '') || COALESCE(remark, ''), '[\\p{IsHan}]')",
            "sys_dict_type rows should not contain Han-script");
        assertZero(connection,
            "SELECT COUNT(*) FROM sys_dict_data WHERE REGEXP_LIKE(COALESCE(dict_label, '') || COALESCE(remark, ''), '[\\p{IsHan}]')",
            "sys_dict_data rows should not contain Han-script");

        assertZero(connection,
            "SELECT COUNT(*) FROM ai_tts_voice WHERE REGEXP_LIKE(COALESCE(name, '') || COALESCE(languages, ''), '[\\p{IsHan}]')",
            "tts voice rows should not contain Han-script");

        assertZero(connection,
            "SELECT COUNT(*) FROM ai_tts_voice WHERE languages LIKE '%' || CHAR(20013) || CHAR(25991) || '%' OR languages LIKE '%' || CHAR(26222) || CHAR(36890) || CHAR(35805) || '%' OR languages LIKE '%' || CHAR(31908) || CHAR(35821) || '%'",
            "tts voice language labels should be westernized");

        assertNoChineseTokens(connection, "sys_params", "SELECT param_code, param_value, remark FROM sys_params");
        assertNoChineseTokens(connection, "ai_model_provider", "SELECT id, name, fields FROM ai_model_provider");
        assertNoChineseTokens(connection, "ai_model_config", "SELECT id, model_name, config_json, remark FROM ai_model_config");
        assertNoChineseTokens(connection, "ai_agent_template", "SELECT id, agent_code, agent_name, system_prompt, language FROM ai_agent_template");
        assertNoChineseTokens(connection, "ai_tts_voice", "SELECT id, name, tts_voice, languages FROM ai_tts_voice");
    }

    private void assertNoChineseTokens(Connection connection, String table, String sql) throws SQLException {
        List<String> offenders = new ArrayList<>();
        try (Statement statement = connection.createStatement();
             ResultSet resultSet = statement.executeQuery(sql)) {
            ResultSetMetaData metaData = resultSet.getMetaData();
            int columnCount = metaData.getColumnCount();
            while (resultSet.next()) {
                StringBuilder row = new StringBuilder();
                for (int i = 1; i <= columnCount; i++) {
                    String value = resultSet.getString(i);
                    if (value != null && (HAN_PATTERN.matcher(value).find() || CHINESE_TOKEN_PATTERN.matcher(value).find())) {
                        row.setLength(0);
                        for (int j = 1; j <= columnCount; j++) {
                            if (j > 1) {
                                row.append(" | ");
                            }
                            row.append(metaData.getColumnLabel(j)).append('=').append(resultSet.getString(j));
                        }
                        offenders.add(row.toString());
                        break;
                    }
                }
            }
        }

        Assertions.assertTrue(
            offenders.isEmpty(),
            table + " should not contain downstream-forbidden Chinese content.\nOffenders:\n" + String.join("\n", offenders)
        );
    }

    private void assertExists(Connection connection, String sql) throws SQLException {
        try (Statement statement = connection.createStatement();
             ResultSet resultSet = statement.executeQuery(sql)) {
            Assertions.assertTrue(resultSet.next(), "expected row missing for query: " + sql);
        }
    }

    private void assertMissing(Connection connection, String sql) throws SQLException {
        try (Statement statement = connection.createStatement();
             ResultSet resultSet = statement.executeQuery(sql)) {
            Assertions.assertFalse(resultSet.next(), "unexpected row present for query: " + sql);
        }
    }

    private void assertZero(Connection connection, String sql, String message) throws SQLException {
        String value = scalar(connection, sql);
        Assertions.assertEquals("0", value, message + " (query: " + sql + ")");
    }

    private void assertCount(Connection connection, String sql, int expected, String message) throws SQLException {
        String value = scalar(connection, sql);
        Assertions.assertEquals(String.valueOf(expected), value, message + " (query: " + sql + ")");
    }

    private String scalar(Connection connection, String sql) throws SQLException {
        try (PreparedStatement preparedStatement = connection.prepareStatement(sql);
             ResultSet resultSet = preparedStatement.executeQuery()) {
            Assertions.assertTrue(resultSet.next(), "query returned no rows: " + sql);
            return resultSet.getString(1);
        }
    }
}
