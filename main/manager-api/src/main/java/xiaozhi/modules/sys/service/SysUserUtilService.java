package xiaozhi.modules.sys.service;


import java.util.function.Consumer;

/**
 * 定义一个系统用户工具类，避免和用户模块循环依赖
 * 如用户和设备互相依赖，用户需要获取所有设备，设备又需要获取每个设备的用户名
 * @author zjy
 * @since 2025-4-2
 */
public interface SysUserUtilService {
    /**
     * 赋值用户名
     * @param userId 用户id
     * @param setter 赋值方法
     */
    void assignUsername( Long userId, Consumer<String> setter);
}
