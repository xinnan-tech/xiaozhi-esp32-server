-- 更新模型供应器表
UPDATE `ai_model_provider` SET fields = '[{"key": "host", "type": "string", "label": "服务地址"}, {"key": "port", "type": "number", "label": "端口号"}, {"key": "type", "type": "string", "label": "服务类型"}, {"key": "is_ssl", "type": "boolean", "label": "是否使用SSL"}, {"key": "api_key", "type": "string", "label": "API密钥"}, {"key": "output_dir", "type": "string", "label": "输出目录"}]' WHERE id = 'SYSTEM_ASR_FunASRServer';

-- 更新模型配置表
UPDATE `ai_model_config` SET 
config_json = '{"host": "127.0.0.1", "port": 10096, "type": "fun_server", "is_ssl": true, "api_key": "none", "output_dir": "tmp/"}',
`doc_link` = 'https://github.com/modelscope/FunASR/blob/main/runtime/docs/SDK_advanced_guide_online_zh.md',
`remark` = '独立部署FunASR，使用FunASR的API服务，只需要五句话
第一句：mkdir -p ./funasr-runtime-resources/models
第二句：sudo docker run -p 10096:10095 -it --privileged=true -v $PWD/funasr-runtime-resources/models:/workspace/models registry.cn-hangzhou.aliyuncs.com/funasr_repo/funasr:funasr-runtime-sdk-online-cpu-0.1.12
上一句话执行后会进入到容器，继续第三句：cd FunASR/runtime
不要退出容器，继续在容器中执行第四句：nohup bash run_server_2pass.sh --download-model-dir /workspace/models --vad-dir damo/speech_fsmn_vad_zh-cn-16k-common-onnx --model-dir damo/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-onnx  --online-model-dir damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online-onnx  --punc-dir damo/punc_ct-transformer_zh-cn-common-vad_realtime-vocab272727-onnx --lm-dir damo/speech_ngram_lm_zh-cn-ai-wesp-fst --itn-dir thuduj12/fst_itn_zh --hotword /workspace/models/hotwords.txt > log.txt 2>&1 &
上一句话执行后会进入到容器，继续第五句：tail -f log.txt
第五句话执行完后，会看到模型下载日志，下载完后就可以连接使用了
以上是使用CPU推理，如果有GPU，详细参考：https://github.com/modelscope/FunASR/blob/main/runtime/docs/SDK_advanced_guide_online_zh.md' WHERE `id` = 'ASR_FunASRServer';

-- FishSpeech配置说明
UPDATE `ai_model_config` SET 
`doc_link` = 'https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/docs/fish-speech-integration.md',
`remark` = 'FishSpeech配置说明：
1. 需要本地部署FishSpeech服务
2. 支持自定义音色
3. 本地推理，无需网络连接
4. 输出文件保存在tmp/目录
5. 可参照教程https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/docs/fish-speech-integration.md' WHERE `id` = 'TTS_FishSpeech';
