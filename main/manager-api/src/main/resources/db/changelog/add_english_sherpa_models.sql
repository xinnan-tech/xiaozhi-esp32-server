-- Add English-only Sherpa-ONNX ASR model configurations
-- Author: Assistant
-- Date: 2025-08-15

-- Add Whisper Tiny English model
INSERT INTO `ai_model_config` VALUES ('ASR_SherpaWhisperTinyEN', 'ASR', 'SherpaWhisperTinyEN', 'Sherpa Whisper Tiny English', 0, 1, '{\"type\": \"sherpa_onnx_local\", \"model_dir\": \"models/sherpa-onnx-whisper-tiny.en\", \"model_type\": \"whisper\", \"output_dir\": \"tmp/\"}', NULL, NULL, 10, NULL, NULL, NULL, NULL);

-- Add Whisper Base English model  
INSERT INTO `ai_model_config` VALUES ('ASR_SherpaWhisperBaseEN', 'ASR', 'SherpaWhisperBaseEN', 'Sherpa Whisper Base English', 0, 1, '{\"type\": \"sherpa_onnx_local\", \"model_dir\": \"models/sherpa-onnx-whisper-base.en\", \"model_type\": \"whisper\", \"output_dir\": \"tmp/\"}', NULL, NULL, 11, NULL, NULL, NULL, NULL);

-- Add Whisper Small English model
INSERT INTO `ai_model_config` VALUES ('ASR_SherpaWhisperSmallEN', 'ASR', 'SherpaWhisperSmallEN', 'Sherpa Whisper Small English', 0, 1, '{\"type\": \"sherpa_onnx_local\", \"model_dir\": \"models/sherpa-onnx-whisper-small.en\", \"model_type\": \"whisper\", \"output_dir\": \"tmp/\"}', NULL, NULL, 12, NULL, NULL, NULL, NULL);

-- Add working English-only models
INSERT INTO `ai_model_config` VALUES ('ASR_SherpaZipformerEN', 'ASR', 'SherpaZipformerEN', 'Sherpa Zipformer English (Good Balance)', 0, 1, '{\"type\": \"sherpa_onnx_local\", \"model_dir\": \"models/sherpa-onnx-zipformer-en-2023-04-01\", \"model_type\": \"zipformer\", \"output_dir\": \"tmp/\"}', NULL, NULL, 13, NULL, NULL, NULL, NULL);

INSERT INTO `ai_model_config` VALUES ('ASR_SherpaZipformerGigaspeechEN', 'ASR', 'SherpaZipformerGigaspeechEN', 'Sherpa Zipformer Gigaspeech English (Large Vocab)', 0, 1, '{\"type\": \"sherpa_onnx_local\", \"model_dir\": \"models/sherpa-onnx-zipformer-gigaspeech-2023-12-12\", \"model_type\": \"zipformer\", \"output_dir\": \"tmp/\"}', NULL, NULL, 14, NULL, NULL, NULL, NULL);

INSERT INTO `ai_model_config` VALUES ('ASR_SherpaParaformerEN', 'ASR', 'SherpaParaformerEN', 'Sherpa Paraformer English (Alternative)', 0, 1, '{\"type\": \"sherpa_onnx_local\", \"model_dir\": \"models/sherpa-onnx-paraformer-en-2023-10-24\", \"model_type\": \"paraformer\", \"output_dir\": \"tmp/\"}', NULL, NULL, 15, NULL, NULL, NULL, NULL);