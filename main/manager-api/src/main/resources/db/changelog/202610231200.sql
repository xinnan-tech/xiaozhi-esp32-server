-- 设备 MAC 归一：改成小写冒号分隔，与 OTA 上报归一后的写法对齐
--
-- 之前用户在智控台手填的 MAC 原样入库（可能是 AA-BB-… 、aabbcc… 或全大写），
-- OTA 侧归一后按 aa:bb:… 精确查库，查不到就静默不发凭证、不下发固件。
-- 这里把存量两列刷成归一后的形态。
--
-- 只改 ai_device.mac_address，不动 id：手填设备的 id 就是当时的原始 MAC，
-- 改 id 会牵动外键和缓存键，风险大于收益。查不到归一值时查询侧会拿原文再试一次。
-- mac_address 上只有普通索引不是唯一键，这段不会撞键。

UPDATE `ai_device`
SET `mac_address` = LOWER(CONCAT(
        SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 1, 2), ':',
        SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 3, 2), ':',
        SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 5, 2), ':',
        SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 7, 2), ':',
        SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 9, 2), ':',
        SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 11, 2)
    ))
WHERE `mac_address` REGEXP '^([0-9A-Fa-f]{2}[-:_]?){5}[0-9A-Fa-f]{2}$'
  AND BINARY `mac_address` <> BINARY LOWER(CONCAT(
        SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 1, 2), ':',
        SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 3, 2), ':',
        SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 5, 2), ':',
        SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 7, 2), ':',
        SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 9, 2), ':',
        SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 11, 2)
    ));

-- 通讯录表的主键就是 (mac_address, target_mac)，两段拼起来还是同一个 MAC 时会撞键。
-- 撞键说明同一台设备在同一个人的通讯录里存了两条、只是写法不同，属于脏数据，
-- 跑之前先看一眼下面这条，有结果就得先把重复的挑出来删掉：
--
--   SELECT LOWER(REPLACE(REPLACE(REPLACE(`mac_address`,':',''),'-',''),'_','')) AS nmac,
--          LOWER(REPLACE(REPLACE(REPLACE(`target_mac`,':',''),'-',''),'_','')) AS ntmac,
--          COUNT(*) c
--   FROM `ai_device_address_book`
--   GROUP BY nmac, ntmac HAVING c > 1;
--
-- 真撞上了会直接报 Duplicate entry 而不是把数据改坏，这时上面 ai_device 那段
-- 已经生效了；把重复的清掉再跑一遍就行，两段都能重跑。
-- 值已经是对的就整行跳过，重跑一遍是空操作。两段是分开判的：
-- 只改本机地址不改对方地址的行，也要算进去，不然它会一直留着旧写法。

UPDATE `ai_device_address_book`
SET `mac_address` = LOWER(CONCAT(
        SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 1, 2), ':',
        SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 3, 2), ':',
        SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 5, 2), ':',
        SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 7, 2), ':',
        SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 9, 2), ':',
        SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 11, 2)
    )),
    `target_mac` = LOWER(CONCAT(
        SUBSTRING(REPLACE(REPLACE(REPLACE(`target_mac`, ':', ''), '-', ''), '_', ''), 1, 2), ':',
        SUBSTRING(REPLACE(REPLACE(REPLACE(`target_mac`, ':', ''), '-', ''), '_', ''), 3, 2), ':',
        SUBSTRING(REPLACE(REPLACE(REPLACE(`target_mac`, ':', ''), '-', ''), '_', ''), 5, 2), ':',
        SUBSTRING(REPLACE(REPLACE(REPLACE(`target_mac`, ':', ''), '-', ''), '_', ''), 7, 2), ':',
        SUBSTRING(REPLACE(REPLACE(REPLACE(`target_mac`, ':', ''), '-', ''), '_', ''), 9, 2), ':',
        SUBSTRING(REPLACE(REPLACE(REPLACE(`target_mac`, ':', ''), '-', ''), '_', ''), 11, 2)
    ))
WHERE `mac_address` REGEXP '^([0-9A-Fa-f]{2}[-:_]?){5}[0-9A-Fa-f]{2}$'
  AND `target_mac` REGEXP '^([0-9A-Fa-f]{2}[-:_]?){5}[0-9A-Fa-f]{2}$'
  AND (
        BINARY `mac_address` <> BINARY LOWER(CONCAT(
              SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 1, 2), ':',
              SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 3, 2), ':',
              SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 5, 2), ':',
              SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 7, 2), ':',
              SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 9, 2), ':',
              SUBSTRING(REPLACE(REPLACE(REPLACE(`mac_address`, ':', ''), '-', ''), '_', ''), 11, 2)
          ))
     OR BINARY `target_mac` <> BINARY LOWER(CONCAT(
              SUBSTRING(REPLACE(REPLACE(REPLACE(`target_mac`, ':', ''), '-', ''), '_', ''), 1, 2), ':',
              SUBSTRING(REPLACE(REPLACE(REPLACE(`target_mac`, ':', ''), '-', ''), '_', ''), 3, 2), ':',
              SUBSTRING(REPLACE(REPLACE(REPLACE(`target_mac`, ':', ''), '-', ''), '_', ''), 5, 2), ':',
              SUBSTRING(REPLACE(REPLACE(REPLACE(`target_mac`, ':', ''), '-', ''), '_', ''), 7, 2), ':',
              SUBSTRING(REPLACE(REPLACE(REPLACE(`target_mac`, ':', ''), '-', ''), '_', ''), 9, 2), ':',
              SUBSTRING(REPLACE(REPLACE(REPLACE(`target_mac`, ':', ''), '-', ''), '_', ''), 11, 2)
          ))
      );