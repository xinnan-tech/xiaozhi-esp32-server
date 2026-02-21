# RAGFlow External API Reference (Grouped by File)

## File: `api/apps/sdk/agents.py`
| Function Name | URL Pattern | Notes |
|---|---|---|
| `list_agents` | `/api/v1/agents` | List Agents |
| `create_agent` | `/api/v1/agents` | Create Agent |
| `update_agent` | `/api/v1/agents/<agent_id>` | Update Agent |
| `delete_agent` | `/api/v1/agents/<agent_id>` | Delete Agent |
| `webhook` | `/api/v1/webhook_test/<agent_id>` | Webhook Test |
| `webhook_trace` | `/api/v1/webhook_trace/<agent_id>` | Webhook Trace |

## File: `api/apps/sdk/chat.py`
| Function Name | URL Pattern | Notes |
|---|---|---|
| `create` | `/api/v1/chats` | Create Chat |
| `delete_chats` | `/api/v1/chats` | Delete Chat |
| `list_chat` | `/api/v1/chats` | List Chats |
| `update` | `/api/v1/chats/<chat_id>` | Update Chat |

## File: `api/apps/sdk/dataset.py`
| Function Name | URL Pattern | Notes |
|---|---|---|
| `create` | `/api/v1/datasets` | Create Dataset |
| `delete` | `/api/v1/datasets` | Delete Dataset |
| `list_datasets` | `/api/v1/datasets` | List Datasets |
| `update` | `/api/v1/datasets/<dataset_id>` | Update Dataset |
| `knowledge_graph` | `/api/v1/datasets/<dataset_id>/knowledge_graph` | Knowledge Graph |
| `delete_knowledge_graph` | `/api/v1/datasets/<dataset_id>/knowledge_graph` | Delete Knowledge Graph |
| `run_graphrag` | `/api/v1/datasets/<dataset_id>/run_graphrag` | Run GraphRAG |
| `run_raptor` | `/api/v1/datasets/<dataset_id>/run_raptor` | Run Raptor |
| `trace_graphrag` | `/api/v1/datasets/<dataset_id>/trace_graphrag` | Trace GraphRAG |
| `trace_raptor` | `/api/v1/datasets/<dataset_id>/trace_raptor` | Trace Raptor |

## File: `api/apps/sdk/dify_retrieval.py`
| Function Name | URL Pattern | Notes |
|---|---|---|
| `retrieval` | `/api/v1/dify/retrieval` | Dify Retrieval |

## File: `api/apps/sdk/doc.py`
| Function Name | URL Pattern | Notes |
|---|---|---|
| `parse` | `/api/v1/datasets/<dataset_id>/chunks` | Parse Document Chunks |
| `stop_parsing` | `/api/v1/datasets/<dataset_id>/chunks` | Stop Parsing |
| `upload` | `/api/v1/datasets/<dataset_id>/documents` | Upload Document |
| `list_docs` | `/api/v1/datasets/<dataset_id>/documents` | List Documents |
| `delete` | `/api/v1/datasets/<dataset_id>/documents` | Delete Document |
| `update_doc` | `/api/v1/datasets/<dataset_id>/documents/<document_id>` | Update Document |
| `download` | `/api/v1/datasets/<dataset_id>/documents/<document_id>` | Download Document |
| `list_chunks` | `/api/v1/datasets/<dataset_id>/documents/<document_id>/chunks` | List Chunks |
| `add_chunk` | `/api/v1/datasets/<dataset_id>/documents/<document_id>/chunks` | Add Chunk |
| `update_chunk` | `/api/v1/datasets/<dataset_id>/documents/<document_id>/chunks/<chunk_id>` | Update Chunk |
| `rm_chunk` | `/api/v1/datasets/<dataset_id>/documents/<document_id>/chunks` | Remove Chunk |
| `metadata_summary` | `/api/v1/datasets/<dataset_id>/metadata/summary` | Metadata Summary |
| `metadata_batch_update` | `/api/v1/datasets/<dataset_id>/metadata/update` | Batch Update Metadata |
| `retrieval_test` | `/api/v1/retrieval` | Retrieval Test |

## File: `api/apps/sdk/files.py`
| Function Name | URL Pattern | Notes |
|---|---|---|
| `get_all_parent_folders` | `/api/v1/file/all_parent_folder` | Get All Parent Folders |
| `convert` | `/api/v1/file/convert` | File Convert |
| `create` | `/api/v1/file/create` | File Create |
| `download_attachment` | `/api/v1/file/download/<attachment_id>` | Download Attachment |
| `get` | `/api/v1/file/get/<file_id>` | Get File |
| `list_files` | `/api/v1/file/list` | List Files |
| `move` | `/api/v1/file/mv` | Move File |
| `get_parent_folder` | `/api/v1/file/parent_folder` | Get Parent Folder |
| `rename` | `/api/v1/file/rename` | Rename File |
| `rm` | `/api/v1/file/rm` | Remove File |
| `get_root_folder` | `/api/v1/file/root_folder` | Get Root Folder |
| `upload` | `/api/v1/file/upload` | Upload File |

## File: `api/apps/sdk/session.py`
| Function Name | URL Pattern | Notes |
|---|---|---|
| `agent_bot_completions` | `/api/v1/agentbots/<agent_id>/completions` | Agent Bot completion |
| `begin_inputs` | `/api/v1/agentbots/<agent_id>/inputs` | Get Agent Bot inputs |
| `agent_completions` | `/api/v1/agents/<agent_id>/completions` | Agent completion |
| `create_agent_session` | `/api/v1/agents/<agent_id>/sessions` | Create Agent Session |
| `list_agent_session` | `/api/v1/agents/<agent_id>/sessions` | List Agent Sessions |
| `delete_agent_session` | `/api/v1/agents/<agent_id>/sessions` | Delete Agent Session |
| `agents_completion_openai_compatibility` | `/api/v1/agents_openai/<agent_id>/chat/completions` | OpenAI compatible Agent completion |
| `chatbot_completions` | `/api/v1/chatbots/<dialog_id>/completions` | Chatbot completion |
| `chatbots_inputs` | `/api/v1/chatbots/<dialog_id>/info` | Chatbot info |
| `chat_completion` | `/api/v1/chats/<chat_id>/completions` | Chat completion |
| `create` | `/api/v1/chats/<chat_id>/sessions` | Create Chat Session |
| `list_session` | `/api/v1/chats/<chat_id>/sessions` | List Chat Sessions |
| `delete` | `/api/v1/chats/<chat_id>/sessions` | Delete Chat Session |
| `update` | `/api/v1/chats/<chat_id>/sessions/<session_id>` | Update Chat Session |
| `chat_completion_openai_like` | `/api/v1/chats_openai/<chat_id>/chat/completions` | OpenAI compatible Chat completion |
| `ask_about_embedded` | `/api/v1/searchbots/ask` | Searchbot Ask |
| `detail_share_embedded` | `/api/v1/searchbots/detail` | Searchbot Detail |
| `mindmap` | `/api/v1/searchbots/mindmap` | Searchbot Mindmap |
| `related_questions_embedded` | `/api/v1/searchbots/related_questions` | Searchbot Related Questions |
| `retrieval_test_embedded` | `/api/v1/searchbots/retrieval_test` | Searchbot Retrieval Test |
| `ask_about` | `/api/v1/sessions/ask` | Session Ask |
| `related_questions` | `/api/v1/sessions/related_questions` | Session Related Questions |
