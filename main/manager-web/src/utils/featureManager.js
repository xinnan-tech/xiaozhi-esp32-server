//功能配置工具
import Api from "@/apis/api";
import store from "@/store";

class FeatureManager {
    constructor() {
        this.defaultFeatures = {
            voiceprintRecognition: {
                name: 'feature.voiceprintRecognition.name',
                enabled: false,
                description: 'feature.voiceprintRecognition.description'
            },
            voiceClone: {
                name: 'feature.voiceClone.name',
                enabled: false,
                description: 'feature.voiceClone.description'
            },
            knowledgeBase: {
                name: 'feature.knowledgeBase.name',
                enabled: false,
                description: 'feature.knowledgeBase.description'
            },
            mcpAccessPoint: {
                name: 'feature.mcpAccessPoint.name',
                enabled: false,
                description: 'feature.mcpAccessPoint.description'
            },
            vad: {
                name: 'feature.vad.name',
                enabled: false,
                description: 'feature.vad.description'
            },
            asr: {
                name: 'feature.asr.name',
                enabled: false,
                description: 'feature.asr.description'
            }
        };
        this.currentFeatures = { ...this.defaultFeatures }; // 当前内存中的配置
        this.initialized = false;
        this.initPromise = null;
    }

    /**
     * 等待初始化完成
     */
    async waitForInitialization() {
        if (!this.initPromise) {
            this.initPromise = this.init();
        }
        await this.initPromise;
        return this.initialized;
    }

    /**
     * 初始化功能配置
     */
    async init() {
        try {
            // 从pub-config接口获取配置
            const config = await this.getConfigFromPubConfig();
            if (config) {
                this.currentFeatures = { ...config }; // 保存到内存
                this.initialized = true;
                return;
            }
        } catch (error) {
            console.warn('从pub-config接口获取配置失败:', error);
        }

        // pub-config接口失败，使用默认配置
        this.currentFeatures = { ...this.defaultFeatures }; // 保存默认配置到内存
        this.initialized = true;
    }

    /**
     * 更新config缓存
     */
    updateConfigCache(config) {
        store.commit('setPubConfig', config);
        localStorage.setItem('pubConfig', JSON.stringify(config));
    }

    /**
     * 从pub-config接口获取配置
     */
    async getConfigFromPubConfig() {
        return new Promise((resolve) => {
            // 直接调用pub-config接口获取配置
            Api.user.getPubConfig((result) => {
                // 检查返回结果的结构
                if (result && result.status === 200) {
                    // 检查是否有data字段
                    if (result.data) {
                        const configCache = result.data.data || {};
                        // 检查是否有code字段，如果有则按照code判断
                        if (result.data.code !== undefined) {
                            if (result.data.code === 0 && result.data.data && result.data.data.systemWebMenu) {
                                try {
                                    let config;
                                    if (typeof result.data.data.systemWebMenu === 'string') {
                                        // 如果是字符串，需要解析JSON
                                        config = JSON.parse(result.data.data.systemWebMenu);
                                    } else {
                                        // 如果已经是对象，直接使用
                                        config = result.data.data.systemWebMenu;
                                    }

                                    // 检查配置中是否包含features对象
                                    if (config && config.features) {
                                        // 确保knowledgeBase功能存在且配置正确
                                        if (!config.features.knowledgeBase) {
                                            console.warn('配置中缺少knowledgeBase功能，合并默认配置');
                                            config.features = { ...this.defaultFeatures, ...config.features };
                                        }
                                        resolve(config.features);
                                    } else {
                                        console.warn('配置中缺少features对象，使用默认配置');
                                        resolve(this.defaultFeatures);
                                    }
                                    configCache.systemWebMenu = config;
                                } catch (error) {
                                    console.warn('处理systemWebMenu配置失败:', error);
                                    resolve(null);
                                }
                            } else {
                                console.warn('接口返回code不为0或缺少必要数据，使用默认配置');
                                resolve(null);
                            }
                        } else {
                            // 如果没有code字段，直接检查systemWebMenu
                            if (result.data && result.data.systemWebMenu) {
                                try {
                                    let config;
                                    if (typeof result.data.systemWebMenu === 'string') {
                                        // 如果是字符串，需要解析JSON
                                        config = JSON.parse(result.data.systemWebMenu);
                                    } else {
                                        // 如果已经是对象，直接使用
                                        config = result.data.systemWebMenu;
                                    }

                                    // 检查配置中是否包含features对象
                                    if (config && config.features) {
                                        // 确保knowledgeBase功能存在且配置正确
                                        if (!config.features.knowledgeBase) {
                                            console.warn('配置中缺少knowledgeBase功能，合并默认配置');
                                            config.features = { ...this.defaultFeatures, ...config.features };
                                        }
                                        resolve(config.features);
                                    } else {
                                        console.warn('配置中缺少features对象，使用默认配置');
                                        resolve(this.defaultFeatures);
                                    }
                                    configCache.systemWebMenu = config;
                                } catch (error) {
                                    console.warn('处理systemWebMenu配置失败:', error);
                                    resolve(null);
                                }
                            } else {
                                console.warn('接口返回缺少systemWebMenu数据，使用默认配置');
                                resolve(null);
                            }
                        }
                        this.updateConfigCache(configCache)
                    } else {
                        console.warn('接口返回数据中缺少data字段，使用默认配置');
                        resolve(null);
                    }
                } else {
                    console.warn('pub-config接口调用失败，使用默认配置');
                    resolve(null);
                }
            });
        });
    }

    /**
     * 获取当前配置
     */
    getCurrentConfig() {
        // 返回内存中的当前配置
        return this.currentFeatures;
    }

    /**
     * 保存配置到后端API
     */
    async saveConfig(config) {
        try {
            // 更新内存中的配置
            this.currentFeatures = { ...config };

            // 异步保存到后端API
            this.saveConfigToAPI(config).catch(error => {
                console.warn('保存配置到API失败:', error);
            }).finally(() => {
                this.init()
            });

            // 触发配置变更事件
            window.dispatchEvent(new CustomEvent('featureConfigChanged', {
                detail: config
            }));
        } catch (error) {
            console.error('保存功能配置失败:', error);
        }
    }

    /**
     * 保存配置到后端API
     */
    async saveConfigToAPI(config) {
        return new Promise((resolve) => {
            // 直接使用已知的ID（600）更新参数
            Api.admin.updateParam(
                {
                    id: 600,
                    paramCode: 'system-web.menu',
                    paramValue: JSON.stringify({
                        features: config,
                        groups: {
                            featureManagement: ["voiceprintRecognition", "voiceClone", "knowledgeBase", "mcpAccessPoint"],
                            voiceManagement: ["vad", "asr"]
                        }
                    }),
                    valueType: 'json',
                    remark: '系统功能菜单配置'
                },
                (updateResult) => {
                    if (updateResult.code === 0) {
                        resolve();
                    } else {
                        // 如果更新失败，可能是参数不存在或其他错误，记录但不阻止保存到localStorage
                        console.warn('更新参数失败:', updateResult.msg);
                        resolve(); // 不阻止保存到localStorage
                    }
                },
                (error) => {
                    console.warn('更新参数失败:', error);
                    resolve(); // 不阻止保存到localStorage
                }
            );
        });
    }



    /**
     * 获取所有功能配置
     */
    getAllFeatures() {
        return this.getCurrentConfig();
    }

    /**
     * 获取简化的配置对象（用于首页组件）
     */
    getConfig() {
        const features = this.getAllFeatures();
        return {
            voiceprintRecognition: features.voiceprintRecognition?.enabled || false,
            voiceClone: features.voiceClone?.enabled || false,
            knowledgeBase: features.knowledgeBase?.enabled || false,
            mcpAccessPoint: features.mcpAccessPoint?.enabled || false,
            vad: features.vad?.enabled || false,
            asr: features.asr?.enabled || false
        };
    }

    /**
     * 获取指定功能的状态
     */
    getFeatureStatus(featureKey) {
        const features = this.getAllFeatures();
        return features[featureKey]?.enabled || false;
    }

    /**
     * 设置功能状态
     */
    setFeatureStatus(featureKey, enabled) {
        const features = this.getAllFeatures();
        if (features[featureKey]) {
            features[featureKey].enabled = enabled;
            this.saveConfig(features);
            return true;
        }
        return false;
    }

    /**
     * 启用功能
     */
    enableFeature(featureKey) {
        return this.setFeatureStatus(featureKey, true);
    }

    /**
     * 禁用功能
     */
    disableFeature(featureKey) {
        return this.setFeatureStatus(featureKey, false);
    }

    /**
     * 切换功能状态
     */
    toggleFeature(featureKey) {
        const currentStatus = this.getFeatureStatus(featureKey);
        return this.setFeatureStatus(featureKey, !currentStatus);
    }

    /**
     * 重置所有功能为默认状态
     */
    resetToDefault() {
        this.saveConfig(this.defaultFeatures);
    }

    /**
     * 批量更新功能状态
     */
    updateFeatures(featureUpdates) {
        const features = this.getAllFeatures();
        Object.keys(featureUpdates).forEach(featureKey => {
            if (features[featureKey]) {
                features[featureKey].enabled = featureUpdates[featureKey];
            }
        });
        this.saveConfig(features);
    }

    /**
     * 获取已启用的功能列表
     */
    getEnabledFeatures() {
        const features = this.getAllFeatures();
        return Object.keys(features).filter(key => features[key].enabled);
    }

    /**
     * 检查功能是否启用
     */
    isFeatureEnabled(featureKey) {
        return this.getFeatureStatus(featureKey);
    }
}

// 创建单例实例
const featureManager = new FeatureManager();

export default featureManager;