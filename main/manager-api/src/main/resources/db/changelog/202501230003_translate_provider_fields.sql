-- Translate provider field labels from Chinese to English
-- This will update the field labels shown in the Call Information section

-- Update common field labels across all providers
UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"API密钥"', '"label":"API Key"')
WHERE fields LIKE '%"label":"API密钥"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"服务地址"', '"label":"Service URL"')
WHERE fields LIKE '%"label":"服务地址"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"基础URL"', '"label":"Base URL"')
WHERE fields LIKE '%"label":"基础URL"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"模型名称"', '"label":"Model Name"')
WHERE fields LIKE '%"label":"模型名称"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"输出目录"', '"label":"Output Directory"')
WHERE fields LIKE '%"label":"输出目录"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"端口号"', '"label":"Port"')
WHERE fields LIKE '%"label":"端口号"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"服务类型"', '"label":"Service Type"')
WHERE fields LIKE '%"label":"服务类型"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"是否使用SSL"', '"label":"Use SSL"')
WHERE fields LIKE '%"label":"是否使用SSL"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"请求方式"', '"label":"Request Method"')
WHERE fields LIKE '%"label":"请求方式"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"请求参数"', '"label":"Request Parameters"')
WHERE fields LIKE '%"label":"请求参数"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"请求头"', '"label":"Request Headers"')
WHERE fields LIKE '%"label":"请求头"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"音频格式"', '"label":"Audio Format"')
WHERE fields LIKE '%"label":"音频格式"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"访问令牌"', '"label":"Access Token"')
WHERE fields LIKE '%"label":"访问令牌"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"响应格式"', '"label":"Response Format"')
WHERE fields LIKE '%"label":"响应格式"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"音色"', '"label":"Voice"')
WHERE fields LIKE '%"label":"音色"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"应用密钥"', '"label":"App Key"')
WHERE fields LIKE '%"label":"应用密钥"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"访问密钥ID"', '"label":"Access Key ID"')
WHERE fields LIKE '%"label":"访问密钥ID"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"访问密钥密码"', '"label":"Access Key Secret"')
WHERE fields LIKE '%"label":"访问密钥密码"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"授权"', '"label":"Authorization"')
WHERE fields LIKE '%"label":"授权"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"速度"', '"label":"Speed"')
WHERE fields LIKE '%"label":"速度"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"温度"', '"label":"Temperature"')
WHERE fields LIKE '%"label":"温度"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"音色ID"', '"label":"Voice ID"')
WHERE fields LIKE '%"label":"音色ID"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"采样率"', '"label":"Sample Rate"')
WHERE fields LIKE '%"label":"采样率"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"参考音频"', '"label":"Reference Audio"')
WHERE fields LIKE '%"label":"参考音频"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"参考文本"', '"label":"Reference Text"')
WHERE fields LIKE '%"label":"参考文本"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"是否标准化"', '"label":"Normalize"')
WHERE fields LIKE '%"label":"是否标准化"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"最大新令牌数"', '"label":"Max New Tokens"')
WHERE fields LIKE '%"label":"最大新令牌数"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"块长度"', '"label":"Chunk Length"')
WHERE fields LIKE '%"label":"块长度"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"重复惩罚"', '"label":"Repetition Penalty"')
WHERE fields LIKE '%"label":"重复惩罚"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"是否流式"', '"label":"Streaming"')
WHERE fields LIKE '%"label":"是否流式"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"是否使用内存缓存"', '"label":"Use Memory Cache"')
WHERE fields LIKE '%"label":"是否使用内存缓存"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"种子"', '"label":"Seed"')
WHERE fields LIKE '%"label":"种子"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"通道数"', '"label":"Channels"')
WHERE fields LIKE '%"label":"通道数"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"参考ID"', '"label":"Reference ID"')
WHERE fields LIKE '%"label":"参考ID"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"组ID"', '"label":"Group ID"')
WHERE fields LIKE '%"label":"组ID"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"文本语言"', '"label":"Text Language"')
WHERE fields LIKE '%"label":"文本语言"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"参考音频路径"', '"label":"Reference Audio Path"')
WHERE fields LIKE '%"label":"参考音频路径"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"提示文本"', '"label":"Prompt Text"')
WHERE fields LIKE '%"label":"提示文本"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"提示语言"', '"label":"Prompt Language"')
WHERE fields LIKE '%"label":"提示语言"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"文本分割方法"', '"label":"Text Split Method"')
WHERE fields LIKE '%"label":"文本分割方法"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"批处理大小"', '"label":"Batch Size"')
WHERE fields LIKE '%"label":"批处理大小"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"批处理阈值"', '"label":"Batch Threshold"')
WHERE fields LIKE '%"label":"批处理阈值"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"是否分桶"', '"label":"Split Bucket"')
WHERE fields LIKE '%"label":"是否分桶"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"是否返回片段"', '"label":"Return Fragment"')
WHERE fields LIKE '%"label":"是否返回片段"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"速度因子"', '"label":"Speed Factor"')
WHERE fields LIKE '%"label":"速度因子"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"是否流式模式"', '"label":"Streaming Mode"')
WHERE fields LIKE '%"label":"是否流式模式"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"是否并行推理"', '"label":"Parallel Inference"')
WHERE fields LIKE '%"label":"是否并行推理"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"辅助参考音频路径"', '"label":"Auxiliary Reference Audio Paths"')
WHERE fields LIKE '%"label":"辅助参考音频路径"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"切分标点"', '"label":"Cut Punctuation"')
WHERE fields LIKE '%"label":"切分标点"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"输入参考"', '"label":"Input References"')
WHERE fields LIKE '%"label":"输入参考"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"采样步数"', '"label":"Sample Steps"')
WHERE fields LIKE '%"label":"采样步数"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"是否使用SR"', '"label":"Use SR"')
WHERE fields LIKE '%"label":"是否使用SR"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"音调因子"', '"label":"Pitch Factor"')
WHERE fields LIKE '%"label":"音调因子"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"音量变化"', '"label":"Volume Change dB"')
WHERE fields LIKE '%"label":"音量变化"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"目标语言"', '"label":"Target Language"')
WHERE fields LIKE '%"label":"目标语言"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"格式"', '"label":"Format"')
WHERE fields LIKE '%"label":"格式"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"情感"', '"label":"Emotion"')
WHERE fields LIKE '%"label":"情感"%';

-- Additional field translations
UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"应用ID"', '"label":"App ID"')
WHERE fields LIKE '%"label":"应用ID"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"应用AppID"', '"label":"App ID"')
WHERE fields LIKE '%"label":"应用AppID"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"应用AppKey"', '"label":"App Key"')
WHERE fields LIKE '%"label":"应用AppKey"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"临时Token"', '"label":"Temporary Token"')
WHERE fields LIKE '%"label":"临时Token"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"AccessKey ID"', '"label":"Access Key ID"')
WHERE fields LIKE '%"label":"AccessKey ID"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"AccessKey Secret"', '"label":"Access Key Secret"')
WHERE fields LIKE '%"label":"AccessKey Secret"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"API服务地址"', '"label":"API Service URL"')
WHERE fields LIKE '%"label":"API服务地址"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"API地址"', '"label":"API URL"')
WHERE fields LIKE '%"label":"API地址"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"WebSocket地址"', '"label":"WebSocket URL"')
WHERE fields LIKE '%"label":"WebSocket地址"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"资源ID"', '"label":"Resource ID"')
WHERE fields LIKE '%"label":"资源ID"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"默认音色"', '"label":"Default Voice"')
WHERE fields LIKE '%"label":"默认音色"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"断句检测时间"', '"label":"Sentence Silence Detection Time"')
WHERE fields LIKE '%"label":"断句检测时间"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"集群"', '"label":"Cluster"')
WHERE fields LIKE '%"label":"集群"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"热词文件名称"', '"label":"Hotword File Name"')
WHERE fields LIKE '%"label":"热词文件名称"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"替换词文件名称"', '"label":"Replacement File Name"')
WHERE fields LIKE '%"label":"替换词文件名称"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"区域"', '"label":"Region"')
WHERE fields LIKE '%"label":"区域"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"语言参数"', '"label":"Language Parameter"')
WHERE fields LIKE '%"label":"语言参数"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"音量"', '"label":"Volume"')
WHERE fields LIKE '%"label":"音量"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"语速"', '"label":"Speech Rate"')
WHERE fields LIKE '%"label":"语速"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"音调"', '"label":"Pitch"')
WHERE fields LIKE '%"label":"音调"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"检测阈值"', '"label":"Detection Threshold"')
WHERE fields LIKE '%"label":"检测阈值"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"模型目录"', '"label":"Model Directory"')
WHERE fields LIKE '%"label":"模型目录"%';

UPDATE ai_model_provider 
SET fields = REPLACE(fields, '"label":"最小静音时长"', '"label":"Min Silence Duration"')
WHERE fields LIKE '%"label":"最小静音时长"%';

-- Update placeholder values in ai_model_config
UPDATE ai_model_config 
SET config_json = REPLACE(config_json, '"你的api_key"', '"your_api_key"')
WHERE config_json LIKE '%"你的api_key"%';

UPDATE ai_model_config 
SET config_json = REPLACE(config_json, '"你的网关访问密钥"', '"your_gateway_access_key"')
WHERE config_json LIKE '%"你的网关访问密钥"%';

UPDATE ai_model_config 
SET config_json = REPLACE(config_json, '"你的app_id"', '"your_app_id"')
WHERE config_json LIKE '%"你的app_id"%';

UPDATE ai_model_config 
SET config_json = REPLACE(config_json, '"你的bot_id"', '"your_bot_id"')
WHERE config_json LIKE '%"你的bot_id"%';

UPDATE ai_model_config 
SET config_json = REPLACE(config_json, '"你的user_id"', '"your_user_id"')
WHERE config_json LIKE '%"你的user_id"%';

UPDATE ai_model_config 
SET config_json = REPLACE(config_json, '"你的personal_access_token"', '"your_personal_access_token"')
WHERE config_json LIKE '%"你的personal_access_token"%';

UPDATE ai_model_config 
SET config_json = REPLACE(config_json, '"你的home assistant api访问令牌"', '"your_home_assistant_api_token"')
WHERE config_json LIKE '%"你的home assistant api访问令牌"%';

UPDATE ai_model_config 
SET config_json = REPLACE(config_json, '"你的Secret ID"', '"your_secret_id"')
WHERE config_json LIKE '%"你的Secret ID"%';

UPDATE ai_model_config 
SET config_json = REPLACE(config_json, '"你的Secret Key"', '"your_secret_key"')
WHERE config_json LIKE '%"你的Secret Key"%';

UPDATE ai_model_config 
SET config_json = REPLACE(config_json, '"你的appkey"', '"your_appkey"')
WHERE config_json LIKE '%"你的appkey"%';

UPDATE ai_model_config 
SET config_json = REPLACE(config_json, '"你的access_key_id"', '"your_access_key_id"')
WHERE config_json LIKE '%"你的access_key_id"%';

UPDATE ai_model_config 
SET config_json = REPLACE(config_json, '"你的access_key_secret"', '"your_access_key_secret"')
WHERE config_json LIKE '%"你的access_key_secret"%';

UPDATE ai_model_config 
SET config_json = REPLACE(config_json, '"你的API Key"', '"your_api_key"')
WHERE config_json LIKE '%"你的API Key"%';

UPDATE ai_model_config 
SET config_json = REPLACE(config_json, '"你的应用ID"', '"your_app_id"')
WHERE config_json LIKE '%"你的应用ID"%';

UPDATE ai_model_config 
SET config_json = REPLACE(config_json, '"你的音色ID"', '"your_voice_id"')
WHERE config_json LIKE '%"你的音色ID"%';

UPDATE ai_model_config 
SET config_json = REPLACE(config_json, '"你的访问令牌"', '"your_access_token"')
WHERE config_json LIKE '%"你的访问令牌"%';

UPDATE ai_model_config 
SET config_json = REPLACE(config_json, '"你的资源ID"', '"your_resource_id"')
WHERE config_json LIKE '%"你的资源ID"%';

UPDATE ai_model_config 
SET config_json = REPLACE(config_json, '"你的默认音色"', '"your_default_voice"')
WHERE config_json LIKE '%"你的默认音色"%';

UPDATE ai_model_config 
SET config_json = REPLACE(config_json, '"你的集群"', '"your_cluster"')
WHERE config_json LIKE '%"你的集群"%';