# プロジェクト改造調査レポート

## 1. 概要

本調査レポートは、xiaozhi-esp32-server プロジェクトにおける音声合成(TTS)、音声認識(ASR)、大規模言語モデル(LLM)の各コンポーネントのカスタマイズ可能性について分析し、指定されたサービス(Google TTS/Voicevox/ElevenLabs、Google ASR/Whisper、OpenAI LLM)への変更が可能な箇所を特定することを目的としています。

## 2. アーキテクチャ概観

プロジェクトはマイクロサービスアーキテクチャを採用しており、以下の 3 つの主要コンポーネントで構成されています：

1. **xiaozhi-server (Python)**: WebSocket/HTTP サーバー、AI サービス統合
2. **manager-api (Java/SpringBoot)**: 管理 API
3. **manager-web (Vue.js)**: 管理フロントエンド

AI サービス統合部分（xiaozhi-server）では、各機能（TTS, ASR, LLM など）が抽象化されたプロバイダーベースのアーキテクチャを採用しており、新しいプロバイダーの追加が容易に設計されています。

## 3. コンポーネント別変更可能性分析

### 3.1 音声合成 (TTS)

#### 現状の実装

- プロジェクトは複数の TTS プロバイダーをサポートしており、`core/providers/tts/`ディレクトリに各プロバイダーの実装が存在します。
- 現在サポートされているプロバイダー: EdgeTTS, Doubao, FishSpeech, OpenAI TTS, GPT-SoVITS など
- 設定ファイル(`config.yaml`)で使用するプロバイダーを切り替えることが可能

#### 変更要求分析

1. **Google TTS**

   - 現在の実装には含まれていませんが、OpenAI TTS の実装(`openai.py`)を参考に新規実装が可能です
   - Google Cloud Text-to-Speech API を使用して実装する必要があります

2. **Voicevox (URL: https://voicevox.dev.ip-dream.jp/)**

   - 現在の実装には含まれていません
   - HTTP API 経由で Voicevox サービスにアクセスする実装が必要です

3. **ElevenLabs**
   - 現在の実装には含まれていません
   - ElevenLabs API を使用した新規実装が必要です

#### 変更箇所

- `main/xiaozhi-server/core/providers/tts/`ディレクトリに新規プロバイダーファイルの追加
- `config.yaml`の TTS セクションに新しいプロバイダー設定の追加
- 必要に応じてデータベース設定の更新（管理画面から設定可能にする場合）

### 3.2 音声認識 (ASR)

#### 現状の実装

- `core/providers/asr/`ディレクトリに各プロバイダーの実装が存在します
- 現在サポートされているプロバイダー: FunASR(ローカル/サーバー), Doubao, Baidu, Tencent, Aliyun など
- `ASRProviderBase`抽象クラスを継承して各プロバイダーを実装

#### 変更要求分析

1. **Google ASR**

   - 現在の実装には含まれていません
   - Google Cloud Speech-to-Text API を使用した実装が必要です

2. **Whisper**
   - 現在の実装には含まれていません
   - OpenAI Whisper API またはローカル Whisper モデルを使用した実装が必要です

#### 変更箇所

- `main/xiaozhi-server/core/providers/asr/`ディレクトリに新規プロバイダーファイルの追加
- `config.yaml`の ASR セクションに新しいプロバイダー設定の追加

### 3.3 大規模言語モデル (LLM)

#### 現状の実装

- `core/providers/llm/`ディレクトリに各プロバイダーの実装が存在します
- 現在サポートされているプロバイダー: OpenAI, Ollama, Gemini, Coze, ChatGLM など
- `LLMProviderBase`抽象クラスを継承して各プロバイダーを実装
- OpenAI 互換 API を使用するプロバイダーが多い

#### 変更要求分析

1. **OpenAI**
   - 既に`openai`プロバイダーが実装されており、設定変更のみで利用可能
   - `config.yaml`の LLM セクションで設定を変更することで使用可能

#### 変更箇所

- `config.yaml`の LLM セクションの設定変更のみで対応可能

## 4. スクレイピング先変更について

プロジェクトのコードを分析した結果、明示的なスクレイピング機能は見つかりませんでした。ただし、以下の可能性があります：

1. プラグイン機能(`plugins_func/functions/`)にスクレイピングを行うモジュールが存在する可能性
2. LLM プロバイダーが内部で何らかの情報を取得している可能性

詳細な調査が必要ですが、一般的な変更方法は：

- `plugins_func/functions/`ディレクトリ内の関連ファイルを確認・修正
- 新しいスクレイピング先に対応したプラグインの開発

## 5. 実装計画

### 5.1 優先順位

1. **LLM (OpenAI)** - 既存実装利用のため、設定変更のみで対応可能
2. **TTS (Google TTS, Voicevox, ElevenLabs)** - 新規実装が必要
3. **ASR (Google ASR, Whisper)** - 新規実装が必要
4. **スクレイピング先変更** - 詳細調査後に対応

### 5.2 各コンポーネントの実装手順

#### TTS プロバイダー追加

1. `core/providers/tts/base.py`の`TTSProviderBase`クラスを継承した新しいプロバイダークラスを作成
2. `text_to_speak`メソッドを実装
3. 必要に応じて`__init__`メソッドで API キーなどの設定を読み込む
4. `config.yaml`に新しいプロバイダーの設定を追加
5. 管理画面から設定可能にするためにデータベース更新が必要な場合がある

#### ASR プロバイダー追加

1. `core/providers/asr/base.py`の`ASRProviderBase`クラスを継承した新しいプロバイダークラスを作成
2. `speech_to_text`メソッドを実装
3. 必要に応じて`__init__`メソッドで API キーなどの設定を読み込む
4. `config.yaml`に新しいプロバイダーの設定を追加

#### LLM プロバイダー設定変更

1. `config.yaml`の LLM セクションにある既存の OpenAI 設定を変更
2. API キー、ベース URL、モデル名などを新しいサービスに合わせて変更

## 6. リスクと注意点

1. **API 利用料金**: Google Cloud、ElevenLabs などの商用 API を使用する場合、利用料金が発生する可能性があります
2. **認証情報の管理**: API キーなどの認証情報を安全に管理する必要があります
3. **互換性**: 新しいプロバイダーが既存のインターフェースと完全に互換性があるとは限りません。必要に応じて調整が必要です
4. **パフォーマンス**: ネットワーク遅延などにより、パフォーマンスに影響が出る可能性があります
5. **依存ライブラリ**: 新しい API を使用するために追加の Python ライブラリが必要になる場合があります

## 7. まとめ

本プロジェクトはプロバイダーベースのアーキテクチャを採用しているため、要求されたサービスへの変更は比較的容易に実現可能です。特に LLM については既存の OpenAI プロバイダーを活用することで、設定変更のみで対応できます。TTS と ASR については新規プロバイダーの実装が必要ですが、既存の実装を参考にすることで効率的に開発が可能です。
