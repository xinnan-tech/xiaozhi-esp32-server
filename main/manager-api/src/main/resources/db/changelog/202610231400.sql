-- 通讯录别名回填：设备登记了但用户没起名时，alias 落的是 NULL，
-- 缓存刷新会整条跳过，对方永远呼不过来，接口却返回成功
--
-- 名字取法和 DeviceAddressBookServiceImpl.formatMacAsDeviceName 一致：
-- 设备在智控台起过名就用那个名，没起过才退回「尾号为xx的设备」。
-- 两边都对末两位做小写化：MAC 本身不区分大小写，落库查库走的都是小写化后的值，
-- 这里跟着取原值的话大写 MAC 会迁出「尾号为AB的设备」，而运行期算出的是「ab」。
-- target_mac 为空或短于两位的行维持原样，Java 那边也是原样返回，算不出名字就不硬造
--
-- 取智控台名字的前提是：这个 MAC 在设备表里只对应一台。
-- 同一台设备被两个用户各登记一次是能发生的（ai_device.mac_address 上只有普通索引），
-- 这种时候同一个 target_mac 会对上好几行，MySQL 自己挑一行，不报错、不打日志。
-- 挑到谁全看存储引擎当时怎么返回，跟通讯录这一行属于哪个用户毫无关系：
-- 实测把其中一个用户的设备删掉之后，剩下那个用户拿到的名字就从前者换成了后者，
-- 用户看到什么会随着设备表的增删变来变去。填一个别人的私有名比不填更糟，
-- 所以多行的情况一律不取名字，退回「尾号为xx的设备」。
-- 那个称呼是拿这一行自己的 target_mac 算的，谁的私有名都没往外露，
-- 而且照样把 alias 填上，缓存还是会刷新，对方还是呼得到。
--
-- GROUP BY 跟着连接的比较规则走，两边都是不区分大小写的，
-- aa:bb:... 和 AA:BB:... 在这里算一组，和 ON 那句会匹配上几行是一致的。
-- 比较规则只折叠大小写，不折叠分隔符，AA-BB-... 和 aa:bb:... 是两个不同的 MAC，
-- 连接本来也对不上，不算撞车
--
-- HAVING COUNT(*) = 1 放在连接之前，派生表带聚合会被物化，
-- 歧义在 JOIN 之前就消掉了，优化器没有机会再挑一行

UPDATE `ai_device_address_book` b
LEFT JOIN (
    SELECT `mac_address`, MIN(`alias`) AS `alias`
    FROM `ai_device`
    GROUP BY `mac_address`
    HAVING COUNT(*) = 1
) d
       ON d.`mac_address` = b.`target_mac`
SET b.`alias` = COALESCE(
        NULLIF(TRIM(d.`alias`), ''),
        CONCAT('尾号为', RIGHT(LOWER(b.`target_mac`), 2), '的设备')
    )
WHERE (b.`alias` IS NULL OR TRIM(b.`alias`) = '')
  AND b.`target_mac` IS NOT NULL
  AND CHAR_LENGTH(b.`target_mac`) >= 2;

-- ── 排查用：这个 MAC 在设备表里有几行 ────────────────────────────────────────
-- 跑完上面那段以后还想要智控台的名字，只能是上面没填成。查一下是不是撞上了：
-- n 大于 1 的就是被人各登记一次的设备，通讯录那边拿到的是尾号称呼。
--
--   SELECT `mac_address`, COUNT(*) AS `n`
--   FROM `ai_device`
--   GROUP BY `mac_address`
--   HAVING COUNT(*) > 1;