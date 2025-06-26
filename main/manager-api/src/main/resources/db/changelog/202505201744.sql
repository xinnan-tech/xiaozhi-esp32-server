-- 更新ai_model_provider的fields字段，将type为dict的改为string
update ai_model_provider set fields = replace(fields, '"type": "dict"', '"type": "string"') where id not in ('SYSTEM_LLM_fastgpt', 'SYSTEM_TTS_custom');
update ai_model_provider set fields = replace(fields, '"type":"dict"', '"type": "string"') where id not in ('SYSTEM_LLM_fastgpt', 'SYSTEM_TTS_custom');