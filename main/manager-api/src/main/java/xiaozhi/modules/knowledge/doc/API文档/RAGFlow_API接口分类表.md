# RAGFlow API Interface Classification

## 1. External APIs (三方接入体系)
**Path Prefix:** `/api/v1`
**Authentication:** API Key (`@token_required`)
**Primary Use:** External system integration, SDK usage.

| Interface Type | Python File Path | Class/Function Name | URL Pattern | Notes |
|---|---|---|---|---|
| **External** | `api/apps/sdk/session.py` | `agent_bot_completions` | `/api/v1/agentbots/<agent_id>/completions` | Agent Bot completion |
| **External** | `api/apps/sdk/session.py` | `begin_inputs` | `/api/v1/agentbots/<agent_id>/inputs` | Get Agent Bot inputs |
| **External** | `api/apps/sdk/agents.py` | `list_agents` | `/api/v1/agents` | List Agents |
| **External** | `api/apps/sdk/agents.py` | `create_agent` | `/api/v1/agents` | Create Agent |
| **External** | `api/apps/sdk/agents.py` | `update_agent` | `/api/v1/agents/<agent_id>` | Update Agent |
| **External** | `api/apps/sdk/agents.py` | `delete_agent` | `/api/v1/agents/<agent_id>` | Delete Agent |
| **External** | `api/apps/sdk/session.py` | `agent_completions` | `/api/v1/agents/<agent_id>/completions` | Agent completion |
| **External** | `api/apps/sdk/session.py` | `create_agent_session` | `/api/v1/agents/<agent_id>/sessions` | Create Agent Session |
| **External** | `api/apps/sdk/session.py` | `list_agent_session` | `/api/v1/agents/<agent_id>/sessions` | List Agent Sessions |
| **External** | `api/apps/sdk/session.py` | `delete_agent_session` | `/api/v1/agents/<agent_id>/sessions` | Delete Agent Session |
| **External** | `api/apps/sdk/session.py` | `agents_completion_openai_compatibility` | `/api/v1/agents_openai/<agent_id>/chat/completions` | OpenAI compatible Agent completion |
| **External** | `api/apps/sdk/session.py` | `chatbot_completions` | `/api/v1/chatbots/<dialog_id>/completions` | Chatbot completion |
| **External** | `api/apps/sdk/session.py` | `chatbots_inputs` | `/api/v1/chatbots/<dialog_id>/info` | Chatbot info |
| **External** | `api/apps/sdk/chat.py` | `create` | `/api/v1/chats` | Create Chat |
| **External** | `api/apps/sdk/chat.py` | `delete_chats` | `/api/v1/chats` | Delete Chat |
| **External** | `api/apps/sdk/chat.py` | `list_chat` | `/api/v1/chats` | List Chats |
| **External** | `api/apps/sdk/chat.py` | `update` | `/api/v1/chats/<chat_id>` | Update Chat |
| **External** | `api/apps/sdk/session.py` | `chat_completion` | `/api/v1/chats/<chat_id>/completions` | Chat completion |
| **External** | `api/apps/sdk/session.py` | `create` | `/api/v1/chats/<chat_id>/sessions` | Create Chat Session |
| **External** | `api/apps/sdk/session.py` | `list_session` | `/api/v1/chats/<chat_id>/sessions` | List Chat Sessions |
| **External** | `api/apps/sdk/session.py` | `delete` | `/api/v1/chats/<chat_id>/sessions` | Delete Chat Session |
| **External** | `api/apps/sdk/session.py` | `update` | `/api/v1/chats/<chat_id>/sessions/<session_id>` | Update Chat Session |
| **External** | `api/apps/sdk/session.py` | `chat_completion_openai_like` | `/api/v1/chats_openai/<chat_id>/chat/completions` | OpenAI compatible Chat completion |
| **External** | `api/apps/sdk/dataset.py` | `create` | `/api/v1/datasets` | Create Dataset |
| **External** | `api/apps/sdk/dataset.py` | `delete` | `/api/v1/datasets` | Delete Dataset |
| **External** | `api/apps/sdk/dataset.py` | `list_datasets` | `/api/v1/datasets` | List Datasets |
| **External** | `api/apps/sdk/dataset.py` | `update` | `/api/v1/datasets/<dataset_id>` | Update Dataset |
| **External** | `api/apps/sdk/doc.py` | `parse` | `/api/v1/datasets/<dataset_id>/chunks` | Parse Document Chunks |
| **External** | `api/apps/sdk/doc.py` | `stop_parsing` | `/api/v1/datasets/<dataset_id>/chunks` | Stop Parsing |
| **External** | `api/apps/sdk/doc.py` | `upload` | `/api/v1/datasets/<dataset_id>/documents` | Upload Document |
| **External** | `api/apps/sdk/doc.py` | `list_docs` | `/api/v1/datasets/<dataset_id>/documents` | List Documents |
| **External** | `api/apps/sdk/doc.py` | `delete` | `/api/v1/datasets/<dataset_id>/documents` | Delete Document |
| **External** | `api/apps/sdk/doc.py` | `update_doc` | `/api/v1/datasets/<dataset_id>/documents/<document_id>` | Update Document |
| **External** | `api/apps/sdk/doc.py` | `download` | `/api/v1/datasets/<dataset_id>/documents/<document_id>` | Download Document |
| **External** | `api/apps/sdk/doc.py` | `list_chunks` | `/api/v1/datasets/<dataset_id>/documents/<document_id>/chunks` | List Chunks |
| **External** | `api/apps/sdk/doc.py` | `add_chunk` | `/api/v1/datasets/<dataset_id>/documents/<document_id>/chunks` | Add Chunk |
| **External** | `api/apps/sdk/doc.py` | `update_chunk` | `/api/v1/datasets/<dataset_id>/documents/<document_id>/chunks/<chunk_id>` | Update Chunk |
| **External** | `api/apps/sdk/dataset.py` | `knowledge_graph` | `/api/v1/datasets/<dataset_id>/knowledge_graph` | Knowledge Graph |
| **External** | `api/apps/sdk/dataset.py` | `delete_knowledge_graph` | `/api/v1/datasets/<dataset_id>/knowledge_graph` | Delete Knowledge Graph |
| **External** | `api/apps/sdk/doc.py` | `metadata_summary` | `/api/v1/datasets/<dataset_id>/metadata/summary` | Metadata Summary |
| **External** | `api/apps/sdk/doc.py` | `metadata_batch_update` | `/api/v1/datasets/<dataset_id>/metadata/update` | Batch Update Metadata |
| **External** | `api/apps/sdk/dataset.py` | `run_graphrag` | `/api/v1/datasets/<dataset_id>/run_graphrag` | Run GraphRAG |
| **External** | `api/apps/sdk/dataset.py` | `run_raptor` | `/api/v1/datasets/<dataset_id>/run_raptor` | Run Raptor |
| **External** | `api/apps/sdk/dataset.py` | `trace_graphrag` | `/api/v1/datasets/<dataset_id>/trace_graphrag` | Trace GraphRAG |
| **External** | `api/apps/sdk/dataset.py` | `trace_raptor` | `/api/v1/datasets/<dataset_id>/trace_raptor` | Trace Raptor |
| **External** | `api/apps/sdk/dify_retrieval.py` | `retrieval` | `/api/v1/dify/retrieval` | Dify Retrieval |
| **External** | `api/apps/sdk/files.py` | `get_all_parent_folders` | `/api/v1/file/all_parent_folder` | Get All Parent Folders |
| **External** | `api/apps/sdk/files.py` | `convert` | `/api/v1/file/convert` | File Convert |
| **External** | `api/apps/sdk/files.py` | `create` | `/api/v1/file/create` | File Create |
| **External** | `api/apps/sdk/files.py` | `download_attachment` | `/api/v1/file/download/<attachment_id>` | Download Attachment |
| **External** | `api/apps/sdk/files.py` | `get` | `/api/v1/file/get/<file_id>` | Get File |
| **External** | `api/apps/sdk/files.py` | `list_files` | `/api/v1/file/list` | List Files |
| **External** | `api/apps/sdk/files.py` | `move` | `/api/v1/file/mv` | Move File |
| **External** | `api/apps/sdk/files.py` | `get_parent_folder` | `/api/v1/file/parent_folder` | Get Parent Folder |
| **External** | `api/apps/sdk/files.py` | `rename` | `/api/v1/file/rename` | Rename File |
| **External** | `api/apps/sdk/files.py` | `rm` | `/api/v1/file/rm` | Remove File |
| **External** | `api/apps/sdk/files.py` | `get_root_folder` | `/api/v1/file/root_folder` | Get Root Folder |
| **External** | `api/apps/sdk/files.py` | `upload` | `/api/v1/file/upload` | Upload File |
| **External** | `api/apps/sdk/doc.py` | `retrieval_test` | `/api/v1/retrieval` | Retrieval Test |
| **External** | `api/apps/sdk/session.py` | `ask_about_embedded` | `/api/v1/searchbots/ask` | Searchbot Ask |
| **External** | `api/apps/sdk/session.py` | `detail_share_embedded` | `/api/v1/searchbots/detail` | Searchbot Detail |
| **External** | `api/apps/sdk/session.py` | `mindmap` | `/api/v1/searchbots/mindmap` | Searchbot Mindmap |
| **External** | `api/apps/sdk/session.py` | `related_questions_embedded` | `/api/v1/searchbots/related_questions` | Searchbot Related Questions |
| **External** | `api/apps/sdk/session.py` | `retrieval_test_embedded` | `/api/v1/searchbots/retrieval_test` | Searchbot Retrieval Test |
| **External** | `api/apps/sdk/session.py` | `ask_about` | `/api/v1/sessions/ask` | Session Ask |
| **External** | `api/apps/sdk/session.py` | `related_questions` | `/api/v1/sessions/related_questions` | Session Related Questions |
| **External** | `api/apps/sdk/agents.py` | `webhook` | `/api/v1/webhook_test/<agent_id>` | Webhook Test |
| **External** | `api/apps/sdk/agents.py` | `webhook_trace` | `/api/v1/webhook_trace/<agent_id>` | Webhook Trace |
| **External** | `api/apps/sdk/doc.py` | `rm_chunk` | `/api/v1datasets/<dataset_id>/documents/<document_id>/chunks` | Remove Chunk |


## 2. Internal APIs (内部前端体系)
**Path Prefix:** `/v1/<app_name>` matches file `api/apps/<app_name>_app.py`
**Authentication:** Session/Cookie (`@login_required`)
**Primary Use:** RAGFlow Web Frontend.

**Selected Core Interfaces:**

| Interface Type | Python File Path | Class/Function Name | URL Pattern | Notes |
|---|---|---|---|---|
| Internal | `api/apps/user_app.py` | `login` | `/v1/user/login` | User Login (Frontend) |
| Internal | `api/apps/user_app.py` | `log_out` | `/v1/user/logout` | User Logout |
| Internal | `api/apps/user_app.py` | `user_add` | `/v1/user/register` | User Registration |
| Internal | `api/apps/user_app.py` | `user_profile` | `/v1/user/info` | User Profile Info |
| Internal | `api/apps/api_app.py` | `new_token` | `/v1/api/new_token` | Generate new API Token |
| Internal | `api/apps/conversation_app.py` | `set_conversation` | `/v1/conversation/set` | Create/Update Conversation |
| Internal | `api/apps/conversation_app.py` | `completion` | `/v1/conversation/completion` | Chat Conversation Completion |
| Internal | `api/apps/kb_app.py` | `list_kbs` | `/v1/kb/list` | List Knowledge Bases |
| Internal | `api/apps/kb_app.py` | `create` | `/v1/kb/create` | Create Knowledge Base |
| Internal | `api/apps/document_app.py` | `upload` | `/v1/document/upload` | Upload Document to KB |
| Internal | `api/apps/document_app.py` | `parse` | `/v1/document/parse` | Parse Document |

*(For a complete list of all 200+ internal APIs, please refer to the `api_endpoints.txt` file or the full scan results)*
