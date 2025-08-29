-- Amazon Transcribe Streaming ASR provider and model configuration

-- Add Amazon Transcribe Streaming real-time ASR provider
DELETE FROM `ai_model_provider` WHERE id = 'SYSTEM_ASR_AmazonStreamASR';
INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) 
VALUES ('SYSTEM_ASR_AmazonStreamASR', 'ASR', 'amazon_transcribe_realtime', 'Amazon Transcribe Streaming', 
'[{"key":"aws_access_key_id","label":"AWS Access Key ID","type":"string"},{"key":"aws_secret_access_key","label":"AWS Secret Access Key","type":"string"},{"key":"aws_region","label":"AWS Region","type":"string"},{"key":"language_code","label":"Default Language Code","type":"string"},{"key":"enable_language_detection","label":"Enable Language Detection","type":"boolean"},{"key":"use_multiple_languages","label":"Support Multiple Languages","type":"boolean"},{"key":"romanized_output","label":"Romanized Output","type":"boolean"},{"key":"sample_rate","label":"Sample Rate","type":"number"},{"key":"media_encoding","label":"Media Encoding","type":"string"},{"key":"output_dir","label":"Output Directory","type":"string"},{"key":"timeout","label":"Timeout (seconds)","type":"number"}]', 
4, 1, NOW(), 1, NOW());

-- Add Amazon Transcribe Streaming model configuration
DELETE FROM `ai_model_config` WHERE id = 'ASR_AmazonStreamASR';
INSERT INTO `ai_model_config` VALUES ('ASR_AmazonStreamASR', 'ASR', 'AmazonStreamASR', 'Amazon Transcribe Streaming', 0, 1, 
'{"type": "amazon_transcribe_realtime", "aws_access_key_id": "", "aws_secret_access_key": "", "aws_region": "us-east-1", "language_code": "en-IN", "enable_language_detection": true, "use_multiple_languages": true, "romanized_output": true, "sample_rate": 16000, "media_encoding": "pcm", "output_dir": "tmp/", "timeout": 30}', 
'https://docs.aws.amazon.com/transcribe/latest/dg/streaming.html', 
'Amazon Transcribe Streaming Configuration:
1. Real-time speech recognition with fast response (seconds)
2. Supports automatic language detection for all major Indian languages
3. Supported languages: Hindi, Bengali, Telugu, Tamil, Gujarati, Kannada, Malayalam, Marathi, Punjabi, English (India)
4. Can output romanized text for local languages
5. Supports speakers switching languages mid-conversation
6. Requires AWS credentials and appropriate IAM permissions
7. Real-time transcription is better suited for conversation scenarios than batch processing
Setup Steps:
1. Visit AWS Console: https://console.aws.amazon.com/
2. Create IAM user and get access keys: https://console.aws.amazon.com/iam/home#/security_credentials
3. Add Amazon Transcribe permissions policy to the user', 
4, NULL, NULL, NULL, NULL);