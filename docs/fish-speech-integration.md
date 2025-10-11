AutoDLにログインし、イメージをレンタルします
イメージを選択:
```
PyTorch / 2.1.0 / 3.10(ubuntu22.04) / cuda 12.1
```

マシン起動後、学術加速を設定します
```
source /etc/network_turbo
```

作業ディレクトリに移動
```
cd autodl-tmp/
```

プロジェクトをクローン
```
git clone https://gitclone.com/github.com/fishaudio/fish-speech.git ; cd fish-speech
```

依存関係をインストール
```
pip install -e.
```

エラーが発生した場合、portaudioをインストールします
```
apt-get install portaudio19-dev -y
```

インストール後に実行
```
pip install torch==2.3.1 torchvision==0.18.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cu121
```

モデルをダウンロード
```
cd tools
python download_models.py 
```

モデルダウンロード後、インターフェースを実行
```
python -m tools.api_server --listen 0.0.0.0:6006 
```

次にブラウザでAutoDLインスタンスページに移動します
```
https://autodl.com/console/instance/list
```

以下の画像のように、先程のマシンの`カスタムサービス`ボタンをクリックし、ポート転送サービスを開始します
![自定义服务](images/fishspeech/autodl-01.png)

ポート転送サービスの設定が完了したら、ローカルコンピュータで`http://localhost:6006/`を開くと、fish-speechのインターフェースにアクセスできます
![服务预览](images/fishspeech/autodl-02.png)


シングルモジュール展開の場合、コア設定は以下の通りです
```
selected_module:
  TTS: FishSpeech
TTS:
  FishSpeech:
    reference_audio: ["config/assets/wakeup_words.wav",]
    reference_text: ["哈啰啊，我是小智啦，声音好听的台湾女孩一枚，超开心认识你耶，最近在忙啥，别忘了给我来点有趣的料哦，我超爱听八卦的啦",]
    api_key: "123"
    api_url: "http://127.0.0.1:6006/v1/tts"
```

その後、サービスを再起動します