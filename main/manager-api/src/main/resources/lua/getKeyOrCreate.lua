local value = redis.call('GET', KEYS[1])
-- value 如果为空着设置值
if not value then
    local result = redis.call('SET', KEYS[1], ARGV[1]) 
    -- 检查 ARGV[2] 是否存在且大于 0
    local expireTime = tonumber(ARGV[2])
    if expireTime and expireTime > 0 then
        redis.call('EXPIRE', KEYS[1], expireTime)
    end
end
return value