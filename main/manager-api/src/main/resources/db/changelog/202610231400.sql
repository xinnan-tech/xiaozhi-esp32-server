-- 通讯录别名回填：设备登记了但用户没起名时，alias 落的是 NULL，
-- 缓存刷新会整条跳过，对方永远呼不过来，接口却返回成功
--
-- 名字取法和 DeviceAddressBookServiceImpl.formatMacAsDeviceName 一致：
-- 设备在智控台起过名就用那个名，没起过才退回「尾号为xx的设备」。
-- target_mac 为空或短于两位的行维持原样，Java 那边也是原样返回，算不出名字就不硬造

UPDATE `ai_device_address_book` b
LEFT JOIN `ai_device` d
       ON d.`mac_address` = b.`target_mac`
SET b.`alias` = COALESCE(
        NULLIF(TRIM(d.`alias`), ''),
        CONCAT('尾号为', RIGHT(b.`target_mac`, 2), '的设备')
    )
WHERE (b.`alias` IS NULL OR TRIM(b.`alias`) = '')
  AND b.`target_mac` IS NOT NULL
  AND CHAR_LENGTH(b.`target_mac`) >= 2;