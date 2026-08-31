UPDATE `ai_model_provider`
SET `fields` = JSON_ARRAY_APPEND(
    `fields`,
    '$',
    JSON_OBJECT(
        'key', 'enable_function_call',
        'label', '启用函数调用（填false关闭，默认true）',
        'type', 'boolean',
        'default', TRUE
    )
)
WHERE `id` = 'SYSTEM_LLM_openai'
  AND JSON_SEARCH(
      `fields`, 'one', 'enable_function_call', NULL, '$[*].key'
  ) IS NULL;
