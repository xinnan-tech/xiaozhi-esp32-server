package xiaozhi.common.exception;

/**
 * 错误编码，由5位数字组成，前2位为模块编码，后3位为业务编码
 * <p>
 * 如：10001（10代表系统模块，001代表业务代码）
 * </p>
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
public interface ErrorCode {
    int INTERNAL_SERVER_ERROR = 500;
    int UNAUTHORIZED = 401;
    int FORBIDDEN = 403;

    int NOT_NULL = 10001;
    int DB_RECORD_EXISTS = 10002;
    int PARAMS_GET_ERROR = 10003;
    int ACCOUNT_PASSWORD_ERROR = 10004;
    int ACCOUNT_DISABLE = 10005;
    int IDENTIFIER_NOT_NULL = 10006;
    int CAPTCHA_ERROR = 10007;
    int PHONE_NOT_NULL = 10008;
    int PASSWORD_ERROR = 10009;

    int SUPERIOR_DEPT_ERROR = 10011;
    int SUPERIOR_MENU_ERROR = 10012;
    int DATA_SCOPE_PARAMS_ERROR = 10013;
    int DEPT_SUB_DELETE_ERROR = 10014;
    int DEPT_USER_DELETE_ERROR = 10015;

    int UPLOAD_FILE_EMPTY = 10019;
    int TOKEN_NOT_EMPTY = 10020;
    int TOKEN_INVALID = 10021;
    int ACCOUNT_LOCK = 10022;

    int OSS_UPLOAD_FILE_ERROR = 10024;

    int REDIS_ERROR = 10027;
    int JOB_ERROR = 10028;
    int INVALID_SYMBOL = 10029;
    int PASSWORD_LENGTH_ERROR = 10030;
    int PASSWORD_WEAK_ERROR = 10031;
    int DEL_MYSELF_ERROR = 10032;
    int DEVICE_CAPTCHA_ERROR = 10033;

    // 参数校验相关错误码
    int PARAM_VALUE_NULL = 10034;
    int PARAM_TYPE_NULL = 10035;
    int PARAM_TYPE_INVALID = 10036;
    int PARAM_NUMBER_INVALID = 10037;
    int PARAM_BOOLEAN_INVALID = 10038;
    int PARAM_ARRAY_INVALID = 10039;
    int PARAM_JSON_INVALID = 10040;

    int OTA_DEVICE_NOT_FOUND = 10041;
    int OTA_DEVICE_NEED_BIND = 10042;

    // 新增错误编码
    int DELETE_DATA_FAILED = 10043;
    int USER_NOT_LOGIN = 10044;
    int WEB_SOCKET_CONNECT_FAILED = 10045;
    int VOICE_PRINT_SAVE_ERROR = 10046;
    int TODAY_SMS_LIMIT_REACHED = 10047;
    int OLD_PASSWORD_ERROR = 10048;
    int INVALID_LLM_TYPE = 10049;
    int TOKEN_GENERATE_ERROR = 10050;
    int RESOURCE_NOT_FOUND = 10051;

    // 新增错误编码
    int DEFAULT_AGENT_NOT_FOUND = 10052;
    int AGENT_NOT_FOUND = 10053;
    int VOICEPRINT_API_NOT_CONFIGURED = 10054;
    int SMS_SEND_FAILED = 10055;
    int SMS_CONNECTION_FAILED = 10056;
    int AGENT_VOICEPRINT_CREATE_FAILED = 10057;
    int AGENT_VOICEPRINT_UPDATE_FAILED = 10058;
    int AGENT_VOICEPRINT_DELETE_FAILED = 10059;
    int SMS_SEND_TOO_FREQUENTLY = 10060;
    int ACTIVATION_CODE_EMPTY = 10061;
    int ACTIVATION_CODE_ERROR = 10062;
    int DEVICE_ALREADY_ACTIVATED = 10063;
    // 默认模型删除错误
    int DEFAULT_MODEL_DELETE_ERROR = 10064;
    // 登录相关错误码
    int ADD_DATA_FAILED = 10065; // 新增数据失败
    int UPDATE_DATA_FAILED = 10066; // 修改数据失败
    int SMS_CAPTCHA_ERROR = 10067; // 短信验证码错误
    int MOBILE_REGISTER_DISABLED = 10068; // 未开启手机注册
    int USERNAME_NOT_PHONE = 10069; // 用户名不是手机号码
    int PHONE_ALREADY_REGISTERED = 10070; // 手机号码已注册
    int PHONE_NOT_REGISTERED = 10071; // 手机号码未注册
    int USER_REGISTER_DISABLED = 10072; // 不允许用户注册
    int RETRIEVE_PASSWORD_DISABLED = 10073; // 未开启找回密码功能
    int PHONE_FORMAT_ERROR = 10074; // 手机号码格式不正确
    int SMS_CODE_ERROR = 10075; // 手机验证码错误

    // 字典类型相关错误码
    int DICT_TYPE_NOT_EXIST = 10076; // 字典类型不存在
    int DICT_TYPE_DUPLICATE = 10077; // 字典类型编码重复

    // 资源处理相关错误码
    int RESOURCE_READ_ERROR = 10078; // 读取资源失败

    // 智能体相关错误码
    int LLM_INTENT_PARAMS_MISMATCH = 10079; // LLM大模型和Intent意图识别，选择参数不匹配

    // 声纹相关错误码
    int VOICEPRINT_ALREADY_REGISTERED = 10080; // 此声音声纹已经注册
    int VOICEPRINT_DELETE_ERROR = 10081; // 删除声纹出现错误
    int VOICEPRINT_UPDATE_NOT_ALLOWED = 10082; // 声纹修改不允许，声音已注册
    int VOICEPRINT_UPDATE_ADMIN_ERROR = 10083; // 修改声纹错误，请联系管理员
    int VOICEPRINT_API_URI_ERROR = 10084; // 声纹接口地址错误
    int VOICEPRINT_AUDIO_NOT_BELONG_AGENT = 10085; // 音频数据不属于智能体
    int VOICEPRINT_AUDIO_EMPTY = 10086; // 音频数据为空
    int VOICEPRINT_REGISTER_REQUEST_ERROR = 10087; // 声纹保存请求失败
    int VOICEPRINT_REGISTER_PROCESS_ERROR = 10088; // 声纹保存处理失败
    int VOICEPRINT_UNREGISTER_REQUEST_ERROR = 10089; // 声纹注销请求失败
    int VOICEPRINT_UNREGISTER_PROCESS_ERROR = 10090; // 声纹注销处理失败
    int VOICEPRINT_IDENTIFY_REQUEST_ERROR = 10091; // 声纹识别请求失败

    int LLM_NOT_EXIST = 10092; // 设置的LLM不存在
    int MODEL_REFERENCED_BY_AGENT = 10093; // 该模型配置已被智能体引用，无法删除
    int LLM_REFERENCED_BY_INTENT = 10094; // 该LLM模型已被意图识别配置引用，无法删除

    // 服务端管理相关错误码
    int INVALID_SERVER_ACTION = 10095; // 无效服务端操作
    int SERVER_WEBSOCKET_NOT_CONFIGURED = 10096; // 未配置服务端WebSocket地址
    int TARGET_WEBSOCKET_NOT_EXIST = 10097; // 目标WebSocket地址不存在

    // 参数验证相关错误码
    int WEBSOCKET_URLS_EMPTY = 10098; // WebSocket地址列表不能为空
    int WEBSOCKET_URL_LOCALHOST = 10099; // WebSocket地址不能使用localhost或127.0.0.1
    int WEBSOCKET_URL_FORMAT_ERROR = 10100; // WebSocket地址格式不正确
    int WEBSOCKET_CONNECTION_FAILED = 10101; // WebSocket连接测试失败
    int OTA_URL_EMPTY = 10102; // OTA地址不能为空
    int OTA_URL_LOCALHOST = 10103; // OTA地址不能使用localhost或127.0.0.1
    int OTA_URL_PROTOCOL_ERROR = 10104; // OTA地址必须以http或https开头
    int OTA_URL_FORMAT_ERROR = 10105; // OTA地址必须以/ota/结尾
    int OTA_INTERFACE_ACCESS_FAILED = 10106; // OTA接口访问失败
    int OTA_INTERFACE_FORMAT_ERROR = 10107; // OTA接口返回内容格式不正确
    int OTA_INTERFACE_VALIDATION_FAILED = 10108; // OTA接口验证失败
    int MCP_URL_EMPTY = 10109; // MCP地址不能为空
    int MCP_URL_LOCALHOST = 10110; // MCP地址不能使用localhost或127.0.0.1
    int MCP_URL_INVALID = 10111; // 不是正确的MCP地址
    int MCP_INTERFACE_ACCESS_FAILED = 10112; // MCP接口访问失败
    int MCP_INTERFACE_FORMAT_ERROR = 10113; // MCP接口返回内容格式不正确
    int MCP_INTERFACE_VALIDATION_FAILED = 10114; // MCP接口验证失败
    int VOICEPRINT_URL_EMPTY = 10115; // 声纹接口地址不能为空
    int VOICEPRINT_URL_LOCALHOST = 10116; // 声纹接口地址不能使用localhost或127.0.0.1
    int VOICEPRINT_URL_INVALID = 10117; // 不是正确的声纹接口地址
    int VOICEPRINT_URL_PROTOCOL_ERROR = 10118; // 声纹接口地址必须以http或https开头
    int VOICEPRINT_INTERFACE_ACCESS_FAILED = 10119; // 声纹接口访问失败
    int VOICEPRINT_INTERFACE_FORMAT_ERROR = 10120; // 声纹接口返回内容格式不正确
    int VOICEPRINT_INTERFACE_VALIDATION_FAILED = 10121; // 声纹接口验证失败
    int MQTT_SECRET_EMPTY = 10122; // mqtt密钥不能为空
    int MQTT_SECRET_LENGTH_INSECURE = 10123; // mqtt密钥长度不安全
    int MQTT_SECRET_CHARACTER_INSECURE = 10124; // mqtt密钥必须同时包含大小写字母
    int MQTT_SECRET_WEAK_PASSWORD = 10125; // mqtt密钥包含弱密码
    int DICT_LABEL_DUPLICATE = 10128; // 字典标签重复
    int SM2_KEY_NOT_CONFIGURED = 10129; // SM2密钥未配置
    int SM2_DECRYPT_ERROR = 10130; // SM2解密失败
    int MODEL_TYPE_PROVIDE_CODE_NOT_NULL = 10131; // modelType和provideCode不能为空

    // 聊天记录相关错误码
    int CHAT_HISTORY_NO_PERMISSION = 10132; // 没有权限查看该智能体的聊天记录
    int CHAT_HISTORY_SESSION_ID_NOT_NULL = 10133; // 会话ID不能为空
    int CHAT_HISTORY_AGENT_ID_NOT_NULL = 10134; // 智能体ID不能为空
    int CHAT_HISTORY_DOWNLOAD_FAILED = 10135; // 聊天记录下载失败
    int DOWNLOAD_LINK_EXPIRED = 10136; // 下载链接已过期或无效
    int DOWNLOAD_LINK_INVALID = 10137; // 下载链接无效
    int CHAT_ROLE_USER = 10138; // 用户角色
    int CHAT_ROLE_AGENT = 10139; // 智能体角色

    // 声音克隆相关错误码
    int VOICE_CLONE_AUDIO_EMPTY = 10140; // 音频文件不能为空
    int VOICE_CLONE_NOT_AUDIO_FILE = 10141; // 只支持音频文件
    int VOICE_CLONE_AUDIO_TOO_LARGE = 10142; // 音频文件大小不能超过10MB
    int VOICE_CLONE_UPLOAD_FAILED = 10143; // 上传失败
    int VOICE_CLONE_RECORD_NOT_EXIST = 10144; // 声音克隆记录不存在
    int VOICE_RESOURCE_INFO_EMPTY = 10145; // 音色资源信息不能为空
    int VOICE_RESOURCE_PLATFORM_NAME_EMPTY = 10146; // 平台名称不能为空
    int VOICE_RESOURCE_ID_EMPTY = 10147; // 音色ID不能为空
    int VOICE_RESOURCE_ACCOUNT_EMPTY = 10148; // 归属账号不能为空
    int VOICE_RESOURCE_DELETE_ID_EMPTY = 10149; // 删除的音色资源ID不能为空
    int VOICE_RESOURCE_NO_PERMISSION = 10150; // 您没有权限操作该记录
    int VOICE_CLONE_AUDIO_NOT_UPLOADED = 10151; // 请先上传音频文件
    int VOICE_CLONE_MODEL_CONFIG_NOT_FOUND = 10152; // 模型配置未找到
    int VOICE_CLONE_MODEL_TYPE_NOT_FOUND = 10153; // 模型类型未找到
    int VOICE_CLONE_TRAINING_FAILED = 10154; // 训练失败
    int VOICE_CLONE_HUOSHAN_CONFIG_MISSING = 10155; // 火山引擎缺少配置
    int VOICE_CLONE_RESPONSE_FORMAT_ERROR = 10156; // 响应格式错误
    int VOICE_CLONE_REQUEST_FAILED = 10157; // 请求失败
    int VOICE_CLONE_PREFIX = 10158; // 复刻音色前缀
    int VOICE_ID_ALREADY_EXISTS = 10159; // 音色ID已存在
    int VOICE_CLONE_HUOSHAN_VOICE_ID_ERROR = 10160; // 火山引擎音色ID格式错误

    // 设备相关错误码
    int MAC_ADDRESS_ALREADY_EXISTS = 10161; // Mac地址已存在
    // 模型相关错误码
    int MODEL_PROVIDER_NOT_EXIST = 10162; // 供应器不存在

    // 知识库相关错误码
    int Knowledge_Base_RECORD_NOT_EXISTS = 10163; // 知识库记录不存在
    int RAG_CONFIG_NOT_FOUND = 10164; // RAG配置未找到
    int RAG_CONFIG_TYPE_ERROR = 10165; // RAG配置类型错误
    int RAG_DEFAULT_CONFIG_NOT_FOUND = 10166; // 默认RAG配置未找到
    int RAG_API_ERROR = 10167; // RAG调用失败
    int UPLOAD_FILE_ERROR = 10168; // 上传文件失败
    int NO_PERMISSION = 10169; // 没有权限
    int KNOWLEDGE_BASE_NAME_EXISTS = 10170; // 同名知识库已存在
    int RAG_API_ERROR_URL_NULL = 10171; // RAG配置中base_url为空，请完善配置
    int RAG_API_ERROR_API_KEY_NULL = 10172; // RAG配置中api_key为空，请完善配置
    int RAG_API_ERROR_API_KEY_INVALID = 10173; // RAG配置中api_key包含占位符，请替换为实际的API密钥
    int RAG_API_ERROR_URL_INVALID = 10174; // RAG配置中base_url格式不正确，请检查协议是否正确
    int RAG_DATASET_ID_NOT_NULL = 10176; // RAG配置中dataset_id不能为空
    int RAG_MODEL_ID_NOT_NULL = 10177; // RAG配置中model_id不能为空
    int RAG_DATASET_ID_AND_MODEL_ID_NOT_NULL = 10178; // RAG配置中dataset_id和model_id不能为空
    int RAG_FILE_NAME_NOT_NULL = 10179; // 文件名称不能为空
    int RAG_FILE_CONTENT_EMPTY = 10180; // 文件内容不能为空

    // 设备相关错误码（补充）
    int MCA_NOT_NULL = 10175; // mac地址不能为空

    // 音色克隆（补充）
    int VOICE_CLONE_NAME_NOT_NULL = 10181; // 音色克隆名称不能为空
    int VOICE_CLONE_AUDIO_NOT_FOUND = 10182; // 音色克隆音频不存在

    // 智能体模板相关错误码(补充)
    int AGENT_TEMPLATE_NOT_FOUND = 10183; // 默认智能体未找到

    // 知识库适配器相关错误码
    int RAG_ADAPTER_TYPE_NOT_SUPPORTED = 10184; // 不支持的适配器类型
    int RAG_CONFIG_VALIDATION_FAILED = 10185; // RAG配置验证失败
    int RAG_ADAPTER_CREATION_FAILED = 10186; // 适配器创建失败
    int RAG_ADAPTER_INIT_FAILED = 10187; // 适配器初始化失败
    int RAG_ADAPTER_CONNECTION_FAILED = 10188; // 适配器连接测试失败
    int RAG_ADAPTER_OPERATION_FAILED = 10189; // 适配器操作失败
    int RAG_ADAPTER_NOT_FOUND = 10190; // 适配器未找到
    int RAG_ADAPTER_CACHE_ERROR = 10191; // 适配器缓存错误
    int RAG_ADAPTER_TYPE_NOT_FOUND = 10192; // 适配器类型未找到

    // 设备工具相关错误码
    int DEVICE_ID_NOT_NULL = 10193; // 设备ID不能为空
    int DEVICE_NOT_EXIST = 10194; // 设备不存在
    int OTA_UPLOAD_COUNT_EXCEED = 10195; // OTA上传次数超过限制

    int RAG_DOCUMENT_PARSING_DELETE_ERROR = 10196; // 文档解析中，禁止删除
}
