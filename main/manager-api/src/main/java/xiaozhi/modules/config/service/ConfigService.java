package xiaozhi.modules.config.service;

import java.util.Map;

public interface ConfigService {
    /**
     * 获取服务器配置
     * 
     * @param isCache 是否缓存
     * @return 配置信息
     */
    Object getConfig(Boolean isCache);

    /**
     * 获取智能体模型配置
     * 
     * @param macAddress     MAC地址
     * @param selectedModule 客户端已实例化的模型
     * @return 模型配置信息
     */
    Map<String, Object> getAgentModels(String macAddress, Map<String, String> selectedModule);
}