# 全モジュールソースコードデプロイの自動アップグレード方法

このチュートリアルは、全モジュールをソースコードからデプロイする愛好家向けに、自動コマンドを使用してソースコードを自動的にプルし、自動的にコンパイルし、ポートを自動的に起動して実行する方法を説明します。これにより、システムのアップグレード効率を最大化します。

このプロジェクトのテストプラットフォーム`https://2662r3426b.vicp.fun`は、公開以来この方法を使用しており、良好な結果を得ています。

チュートリアルは、Bilibiliのブロガー`毕乐labs`が公開したビデオチュートリアルを参考にしてください：[《オープンソース小智サーバーxiaozhi-server自動更新および最新バージョンMCPアクセスポイント設定完全ガイド》](https://www.bilibili.com/video/BV15H37zHE7Q)

# 開始条件
- あなたのコンピュータ/サーバーはLinuxオペレーティングシステムであること
- あなたはすでにプロセス全体を実行したことがあること
- 最新の機能を追いかけるのが好きだが、毎回手動でデプロイするのが面倒で、自動更新の方法を期待していること

2番目の条件は必須です。このチュートリアルで言及する一部のファイル、JDK、Node.js環境、Conda環境などは、プロセス全体を実行して初めて利用可能になるためです。もし実行したことがなければ、特定のファイルについて話すときに、その意味がわからないかもしれません。

# チュートリアルの効果
- 国内で最新のプロジェクトソースコードをプルできない問題を解決
- コードを自動的にプルしてフロントエンドファイルをコンパイル
- コードを自動的にプルしてJavaファイルをコンパイルし、8002ポートを自動的に強制終了し、8002ポートを自動的に起動
- Pythonコードを自動的にプルし、8000ポートを自動的に強制終了し、8000ポートを自動的に起動

# ステップ1 プロジェクトディレクトリの選択

例えば、私のプロジェクトディレクトリを次のように計画します。これは新しく作成された空のディレクトリです。エラーを避けたい場合は、私と同じようにしてください。
```
/home/system/xiaozhi
```

# ステップ2 プロジェクトのクローン
まず、最初のコマンドを実行してソースコードをプルします。このコマンドは、国内ネットワークのサーバーとコンピュータに適用され、VPNは不要です。

```
cd /home/system/xiaozhi
git clone https://ghproxy.net/https://github.com/xinnan-tech/xiaozhi-esp32-server.git
```

実行後、プロジェクトディレクトリに`xiaozhi-esp32-server`というフォルダが追加されます。これがプロジェクトのソースコードです。

# ステップ3 基本ファイルのコピー

以前にプロセス全体を実行したことがある場合、funasrのモデルファイル`xiaozhi-server/models/SenseVoiceSmall/model.pt`とプライベート設定ファイル`xiaozhi-server/data/.config.yaml`についてはよくご存知のはずです。

ここで、`model.pt`ファイルを新しいディレクトリにコピーする必要があります。次のようにします。
```
# 必要なディレクトリを作成
mkdir -p /home/system/xiaozhi/xiaozhi-esp32-server/main/xiaozhi-server/data/

cp あなたの元の.config.yamlのフルパス /home/system/xiaozhi/xiaozhi-esp32-server/main/xiaozhi-server/data/.config.yaml
cp あなたの元のmodel.ptのフルパス /home/system/xiaozhi/xiaozhi-esp32-server/main/xiaozhi-server/models/SenseVoiceSmall/model.pt
```

# ステップ4 3つの自動コンパイルファイルの作成

## 4.1 mananger-webモジュールの自動コンパイル
`/home/system/xiaozhi/`ディレクトリに、`update_8001.sh`という名前のファイルを作成し、内容は次の通りです。

```
cd /home/system/xiaozhi/xiaozhi-esp32-server
git fetch --all
git reset --hard
git pull origin main


cd /home/system/xiaozhi/xiaozhi-esp32-server/main/manager-web
npm install
npm run build
rm -rf /home/system/xiaozhi/manager-web
mv /home/system/xiaozhi/xiaozhi-esp32-server/main/manager-web/dist /home/system/xiaozhi/manager-web
```

保存後、権限を付与するコマンドを実行します。
```
chmod 777 update_8001.sh
```
実行後、次に進みます。

## 4.2 manager-apiモジュールの自動コンパイルと実行
`/home/system/xiaozhi/`ディレクトリに、`update_8002.sh`という名前のファイルを作成し、内容は次の通りです。

```
cd /home/system/xiaozhi/xiaozhi-esp32-server
git pull origin main


cd /home/system/xiaozhi/xiaozhi-esp32-server/main/manager-api
rm -rf target
mvn clean package -Dmaven.test.skip=true
cd /home/system/xiaozhi/

# 8002ポートを占有しているプロセスIDを検索
PID=$(sudo netstat -tulnp | grep 8002 | awk '{print $7}' | cut -d'/' -f1)

rm -rf /home/system/xiaozhi/xiaozhi-esp32-api.jar
mv /home/system/xiaozhi/xiaozhi-esp32-server/main/manager-api/target/xiaozhi-esp32-api.jar /home/system/xiaozhi/xiaozhi-esp32-api.jar

# プロセスIDが見つかったか確認
if [ -z "$PID" ]; then
  echo "8002ポートを占有しているプロセスが見つかりません"
else
  echo "8002ポートを占有しているプロセスが見つかりました。プロセスID: $PID"
  # プロセスを強制終了
  kill -9 $PID
  kill -9 $PID
  echo "プロセス $PID を強制終了しました"
fi

nohup java -jar xiaozhi-esp32-api.jar --spring.profiles.active=dev &
```

保存後、権限を付与するコマンドを実行します。
```
chmod 777 update_8002.sh
```
実行後、次に進みます。

## 4.3 Pythonプロジェクトの自動コンパイルと実行
`/home/system/xiaozhi/`ディレクトリに、`update_8000.sh`という名前のファイルを作成し、内容は次の通りです。

```
cd /home/system/xiaozhi/xiaozhi-esp32-server
git pull origin main

# 8000ポートを占有しているプロセスIDを検索
PID=$(sudo netstat -tulnp | grep 8000 | awk '{print $7}' | cut -d'/' -f1)

# プロセスIDが見つかったか確認
if [ -z "$PID" ]; then
  echo "8000ポートを占有しているプロセスが見つかりません"
else
  echo "8000ポートを占有しているプロセスが見つかりました。プロセスID: $PID"
  # プロセスを強制終了
  kill -9 $PID
  kill -9 $PID
  echo "プロセス $PID を強制終了しました"
fi
cd main/xiaozhi-server
pip install -r requirements.txt
nohup python app.py >/dev/null &
```

保存後、権限を付与するコマンドを実行します。
```
chmod 777 update_8000.sh
```
実行後、次に進みます。

# 日常の更新

上記のスクリプトをすべて作成した後、日常の更新では、以下のコマンドを順に実行するだけで自動更新と起動ができます。

```
# Python環境に入る
conda activate xiaozhi-esp32-server
cd /home/system/xiaozhi
# Javaプログラムを更新して起動
./update_8001.sh
# Webプログラムを更新
./update_8002.sh
# Pythonプログラムを更新して起動
./update_8000.sh
# Javaのログを表示
tail -f nohup.out
# Pythonのログを表示
tail -f /home/system/xiaozhi/xiaozhi-esp32-server/main/xiaozhi-server/tmp/server.log
```

# 注意事項
テストプラットフォーム`https://2662r3426b.vicp.fun`は、nginxを使用してリバースプロキシを行っています。nginx.confの詳細な設定は[こちら](https://github.com/xinnan-tech/xiaozhi-esp32-server/issues/791)を参考にしてください。

## よくある質問

### 1、なぜ8001ポートが見当たらないのですか？
回答：8001は開発環境で使用される、フロントエンドを実行するためのポートです。サーバーにデプロイする場合、`npm run serve`で8001ポートを起動してフロントエンドを実行するのではなく、このチュートリアルのようにHTMLファイルにコンパイルし、nginxでアクセスを管理することをお勧めします。

### 2、更新のたびに手動でSQL文を更新する必要がありますか？
回答：いいえ、必要ありません。プロジェクトは**Liquibase**を使用してデータベースのバージョンを管理しており、新しいSQLスクリプトが自動的に実行されます。