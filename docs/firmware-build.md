# esp32ファームウェアのコンパイル

## ステップ1 OTAアドレスの準備

このプロジェクトのバージョン0.3.12を使用している場合、シンプルサーバー展開でもフルモジュール展開でも、OTAアドレスがあります。

シンプルサーバー展開とフルモジュール展開ではOTAアドレスの設定方法が異なるため、以下の具体的な方法を選択してください：

### シンプルサーバー展開を使用している場合
今すぐ、ブラウザでOTAアドレスを開いてください。例えば、私のアドレスは次のとおりです。
```
http://192.168.1.25:8003/xiaozhi/ota/
```
「OTAインターフェースは正常に動作しています。デバイスに送信されるwebsocketアドレスはws://xxx:8000/xiaozhi/v1/です」と表示された場合

プロジェクトに付属の`test_page.html`を使用して、OTAページが出力するwebsocketアドレスに接続できるかどうかをテストできます。

アクセスできない場合は、設定ファイル`.config.yaml`で`server.websocket`のアドレスを変更し、再起動後に再度テストして、`test_page.html`が正常にアクセスできるようになるまで試してください。

成功したら、ステップ2に進んでください。

### フルモジュール展開を使用している場合
今すぐ、ブラウザでOTAアドレスを開いてください。例えば、私のアドレスは次のとおりです。
```
http://192.168.1.25:8002/xiaozhi/ota/
```

「OTAインターフェースは正常に動作しています。websocketクラスター数：X」と表示された場合は、ステップ2に進んでください。

「OTAインターフェースは正常に動作していません」と表示された場合は、おそらく`スマートコントロールパネル`で`Websocket`アドレスを設定していないためです。その場合は：

- 1. スーパー管理者でスマートコントロールパネルにログインします。

- 2. 上部メニューの`パラメータ管理`をクリックします。

- 3. リストから`server.websocket`項目を見つけ、`Websocket`アドレスを入力します。例えば、私の場合は次のようになります。

```
ws://192.168.1.25:8000/xiaozhi/v1/
```

設定後、ブラウザでOTAインターフェースアドレスを更新して、正常に動作するかどうかを確認してください。それでも正常に動作しない場合は、Websocketが正常に起動しているか、Websocketアドレスが設定されているかを再度確認してください。

## ステップ2 環境設定
まず、このチュートリアルに従ってプロジェクト環境を設定します[《WindowsでESP IDF 5.3.2開発環境を構築し、小智をコンパイルする》](https://icnynnzcwou8.feishu.cn/wiki/JEYDwTTALi5s2zkGlFGcDiRknXf)

## ステップ3 設定ファイルを開く
コンパイル環境を設定した後、虾哥のxiaozhi-esp32プロジェクトのソースコードをダウンロードします。

ここから虾哥の[xiaozhi-esp32プロジェクトソースコード](https://github.com/78/xiaozhi-esp32)をダウンロードします。

ダウンロード後、`xiaozhi-esp32/main/Kconfig.projbuild`ファイルを開きます。

## ステップ4 OTAアドレスの変更

`OTA_URL`の`default`の内容を見つけ、`https://api.tenclass.net/xiaozhi/ota/`を自分のアドレスに変更します。例えば、私のインターフェースアドレスが`http://192.168.1.25:8002/xiaozhi/ota/`の場合、内容をこれに変更します。

変更前：
```
config OTA_URL
    string "Default OTA URL"
    default "https://api.tenclass.net/xiaozhi/ota/"
    help
        The application will access this URL to check for new firmwares and server address.
```
変更後：
```
config OTA_URL
    string "Default OTA URL"
    default "http://192.168.1.25:8002/xiaozhi/ota/"
    help
        The application will access this URL to check for new firmwares and server address.
```

## ステップ4 コンパイルパラメータの設定

コンパイルパラメータの設定

```
# ターミナルコマンドラインでxiaozhi-esp32のルートディレクトリに移動します
cd xiaozhi-esp32
# 例えば、私が使用しているボードはesp32s3なので、コンパイルターゲットをesp32s3に設定します。お使いのボードが他のモデルの場合は、対応するモデルに置き換えてください
idf.py set-target esp32s3
# メニュー設定に入ります
idf.py menuconfig
```

メニュー設定に入った後、`Xiaozhi Assistant`に入り、`BOARD_TYPE`をお使いのボードの具体的なモデルに設定します。
保存して終了し、ターミナルコマンドラインに戻ります。

## ステップ5 ファームウェアのコンパイル

```
idf.py build
```

## ステップ6 binファームウェアのパッケージ化

```
cd scripts
python release.py
```

上記のパッケージ化コマンドが完了すると、プロジェクトのルートディレクトリの`build`ディレクトリにファームウェアファイル`merged-binary.bin`が生成されます。
この`merged-binary.bin`が、ハードウェアに書き込むファームウェアファイルです。

注意：2番目のコマンドの実行後に「zip」関連のエラーが報告された場合は、このエラーを無視してください。`build`ディレクトリにファームウェアファイル`merged-binary.bin`が生成されていれば、大きな影響はありませんので、続けてください。

## ステップ7 ファームウェアの書き込み
   esp32デバイスをコンピュータに接続し、Chromeブラウザを使用して次のURLを開きます。

```
https://espressif.github.io/esp-launchpad/
```

このチュートリアルを開きます[Flashツール/Web経由でのファームウェア書き込み（IDF開発環境なし）](https://ccnphfhqs21z.feishu.cn/wiki/Zpz4wXBtdimBrLk25WdcXzxcnNS)。
`方法2：ESP-LaunchpadブラウザWEB経由での書き込み`までスクロールし、`3. ファームウェアの書き込み/開発ボードへのダウンロード`からチュートリアルに従って操作します。

書き込みとネットワーク接続が成功したら、ウェイクワードで小智を起動し、サーバー側のコンソール出力情報に注意してください。

## よくある質問
以下は参考のためのよくある質問です：

[1. なぜ私の話した言葉を、小智は韓国語、日本語、英語でたくさん認識するのですか](./FAQ.md)

[2. なぜ「TTSタスクエラー ファイルが存在しません」と表示されるのですか？](./FAQ.md)

[3. TTSが頻繁に失敗し、タイムアウトします](./FAQ.md)

[4. Wi-Fiでは自作サーバーに接続できますが、4Gモードでは接続できません](./FAQ.md)

[5. 小智の対話応答速度を向上させるにはどうすればよいですか？](./FAQ.md)

[6. 話すのが遅く、間が空くと小智が割り込んで話してしまいます](./FAQ.md)

[7. 小智を使って照明、エアコン、リモートでの電源オン/オフなどを操作したい](./FAQ.md)
