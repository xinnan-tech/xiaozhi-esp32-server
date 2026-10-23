-- 设备 MAC 归一：改成小写冒号分隔，与 OTA 上报归一后的写法对齐
--
-- 之前用户在智控台手填的 MAC 原样入库（可能是 AA-BB-… 、aabbcc… 或全大写），
-- OTA 侧归一后按 aa:bb:… 精确查库，查不到就静默不发凭证、不下发固件。
-- 这里把存量刷成归一后的形态。
--
-- 只改 mac_address，不动 id：手填设备的 id 就是当时的原始 MAC，而 ai_chat_history
-- 等表按 device_id 存着对话记录，改 id 会牵动这些外键和缓存键，风险大于收益。
-- 查不到归一值时查询侧会拿原文再试一次。
--
-- 需要 MySQL 8.0.19 及以上：下面三段都是 WITH ... UPDATE，这个写法 8.0.19 才有。
-- 低版本上第一段就是语法错，三段又都在一个事务里，语法错会整体回滚，
-- manager-api 起不来。README 的环境要求写的是同一个下限。
--
-- ⚠️ 三段都只刷「归一后全表只剩它一行」的那种，这不是保守，是必须。
--
-- 同一台设备被填过两种写法（AA-BB-CC-DD-EE-FF 和 aabbccddeeff）时，两行会归一成
-- 同一个值，全刷就撞了。而两段撞了的后果完全不一样，方向是反的：
--
--   ai_device：mac_address 上只有普通索引不是唯一键，撞了数据库一声不吭。
--     两行一模一样存下来，之后 getDeviceByMacAddress 的 selectOne 命中多行直接抛
--     TooManyResultsException。这台设备之后彻底读不出来，报活和激活两条路全崩，
--     库里没有任何东西能看出发生过什么，用户只看到一个错误响应。
--
--   ai_device_address_book：主键是 (mac_address, target_mac)，撞上会报 Duplicate
--     entry，整个 changeset 回滚，服务起不来。吵，但看得见。
--
-- 也就是没有 DB 保护的那段才会静默坏数据。下面每段的 cnt.n = 1 就是这个保护：
-- 刷完不会出现两行同值。撞上的行一个都不动，保持迁移前的状态——写法不同就 eq 不到，
-- 用户看得见、也还能重新添加，manualAddDevice 现在入库前会归一，重新添加会补上一行
-- 归一后的。
--
-- ── ① ai_device.mac_address ────────────────────────────────────────────

WITH norm AS (
    SELECT `id`, LOWER(CONCAT(SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 1, 2), ':', SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 3, 2), ':', SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 5, 2), ':', SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 7, 2), ':', SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 9, 2), ':', SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 11, 2))) AS `nmac`
    FROM `ai_device`
    WHERE `mac_address` REGEXP '^([0-9A-Fa-f]{2}[-:_]?){5}[0-9A-Fa-f]{2}$'
),
cnt AS (SELECT `nmac`, COUNT(*) AS `n` FROM norm GROUP BY `nmac`)
UPDATE `ai_device` d
JOIN norm ON norm.`id` = d.`id`
JOIN cnt ON cnt.`nmac` = norm.`nmac`
SET d.`mac_address` = norm.`nmac`
WHERE cnt.`n` = 1
  -- BINARY 是逐字节比：ai_device 走的是库的 utf8mb4_0900_ai_ci，
  -- 普通 <> 认为 AA:BB:… 和 aa:bb:… 相等，大写行会永远刷不掉
  AND BINARY d.`mac_address` <> BINARY norm.`nmac`;

--
-- ── ② ai_device_address_book 的两列 ────────────────────────────────────
-- 主键是 (mac_address, target_mac)，撞的是这一对，所以两列分开刷、各自判重。
-- 一次只改一列时另一列不动，会不会撞只由这一列决定：
-- mac 相同的行 target 必然不同（主键），target 归一成同一个值的行有 cnt 挡着。
--
-- 12 位以外的地址（ESP32 伪 MAC 是 32 位）正则不匹配，原样不动，和 Java 那边
-- normalizeDeviceId 的行为一致——它同样只归一 12 位那种。mac 和 target 各自判断，
-- 一列不合法不妨碍另一列刷（伪 MAC 那台本机的 mac 照样刷得掉）。

WITH norm AS (
    SELECT `mac_address`, `target_mac`, LOWER(CONCAT(SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 1, 2), ':', SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 3, 2), ':', SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 5, 2), ':', SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 7, 2), ':', SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 9, 2), ':', SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 11, 2))) AS `nmac`
    FROM `ai_device_address_book`
    WHERE `mac_address` REGEXP '^([0-9A-Fa-f]{2}[-:_]?){5}[0-9A-Fa-f]{2}$'
),
cnt AS (SELECT `nmac`, COUNT(*) AS `n` FROM norm GROUP BY `nmac`)
UPDATE `ai_device_address_book` b
JOIN norm ON norm.`mac_address` = b.`mac_address` AND norm.`target_mac` = b.`target_mac`
JOIN cnt ON cnt.`nmac` = norm.`nmac`
SET b.`mac_address` = norm.`nmac`
WHERE cnt.`n` = 1
  AND BINARY b.`mac_address` <> BINARY norm.`nmac`;

WITH norm AS (
    SELECT `mac_address`, `target_mac`, LOWER(CONCAT(SUBSTRING(REPLACE(REPLACE(REPLACE(`target_mac`, ':', ''), '-', ''), '_', ''), 1, 2), ':', SUBSTRING(REPLACE(REPLACE(REPLACE(`target_mac`, ':', ''), '-', ''), '_', ''), 3, 2), ':', SUBSTRING(REPLACE(REPLACE(REPLACE(`target_mac`, ':', ''), '-', ''), '_', ''), 5, 2), ':', SUBSTRING(REPLACE(REPLACE(REPLACE(`target_mac`, ':', ''), '-', ''), '_', ''), 7, 2), ':', SUBSTRING(REPLACE(REPLACE(REPLACE(`target_mac`, ':', ''), '-', ''), '_', ''), 9, 2), ':', SUBSTRING(REPLACE(REPLACE(REPLACE(`target_mac`, ':', ''), '-', ''), '_', ''), 11, 2))) AS `ntmac`
    FROM `ai_device_address_book`
    WHERE `target_mac` REGEXP '^([0-9A-Fa-f]{2}[-:_]?){5}[0-9A-Fa-f]{2}$'
),
cnt AS (SELECT `ntmac`, COUNT(*) AS `n` FROM norm GROUP BY `ntmac`)
UPDATE `ai_device_address_book` b
JOIN norm ON norm.`mac_address` = b.`mac_address` AND norm.`target_mac` = b.`target_mac`
JOIN cnt ON cnt.`ntmac` = norm.`ntmac`
SET b.`target_mac` = norm.`ntmac`
WHERE cnt.`n` = 1
  AND BINARY b.`target_mac` <> BINARY norm.`ntmac`;

--
-- ── ③ 刷完之后跑这个，看有没有被跳过的重复 ─────────────────────────────
-- 有结果说明同一台设备被填过多种写法，两行现在还是分开存的，行为和迁移前完全一样。
-- 真要合得人来看：两行的 user_id 可能不是同一个人，谁该留下不是机器能定的，
-- 所以这里只报不动。
--
--   SELECT LOWER(CONCAT(SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`,':',''),'-',''),'_',''), 1, 2), ':',
--          SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`,':',''),'-',''),'_',''), 3, 2), ':',
--          SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`,':',''),'-',''),'_',''), 5, 2), ':',
--          SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`,':',''),'-',''),'_',''), 7, 2), ':',
--          SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`,':',''),'-',''),'_',''), 9, 2), ':',
--          SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`,':',''),'-',''),'_',''), 11, 2))) AS `nmac`,
--          COUNT(*) AS `c`
--   FROM `ai_device`
--   WHERE `mac_address` REGEXP '^([0-9A-Fa-f]{2}[-:_]?){5}[0-9A-Fa-f]{2}$'
--   GROUP BY `nmac` HAVING `c` > 1;
--
-- 三段合在一个 changeset 里，也就是一个事务（Liquibase 默认 runInTransaction 为真），
-- 任何一段报错都会整体回滚、服务起不来。所以它们不该去撞，上面的 cnt 就是为这个。
-- 值已经是对的三段都是空操作，重跑安全。
