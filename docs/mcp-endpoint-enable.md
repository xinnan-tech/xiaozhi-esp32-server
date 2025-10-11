# MCPエンドポイントデプロイガイド

このチュートリアルは2つのパートで構成されています
- 1、MCPエンドポイントサービスのデプロイ方法
- 2、全モジュールデプロイ時のMCPエンドポイント設定方法
- 3、単一モジュールデプロイ時のMCPエンドポイント設定方法

# 1、MCPエンドポイントサービスのデプロイ方法

## ステップ1: MCPエンドポイントプロジェクトのソースコードをダウンロード

ブラウザで[MCPエンドポイントプロジェクトのURL](https://github.com/xinnan-tech/mcp-endpoint-server)を開きます

ページ内の緑色の`Code`ボタンをクリックし、`Download ZIP`ボタンを選択します。

ZIPファイルをダウンロード後、解凍します。解凍後のフォルダ名が`mcp-endpoint-server-main`の場合、`mcp-endpoint-server`にリネームしてください。

## ステップ2: プログラムの起動

このプロジェクトはシンプルな構成なので、Dockerを使用することを推奨します。Dockerを使用しない場合は、[このページ](https://github.com/xinnan-tech/mcp-endpoint-server/blob/main/README_dev.md)を参考にソースコードから実行してください。以下はDockerを使用する方法です

```
# 进入本项目源码根目录
cd mcp-endpoint-server

# 清除缓存
docker compose -f docker-compose.yml down
docker stop mcp-endpoint-server
docker rm mcp-endpoint-server
docker rmi ghcr.nju.edu.cn/xinnan-tech/mcp-endpoint-server:latest

# 启动docker容器
docker compose -f docker-compose.yml up -d
# 查看日志
docker logs -f mcp-endpoint-server
```

此时，日志里会输出类似以下的日志
```
250705 INFO-=====下面的地址分别是智控台/单模块MCP接入点地址====
250705 INFO-智控台MCP参数配置: http://172.22.0.2:8004/mcp_endpoint/health?key=abc
250705 INFO-单模块部署MCP接入点: ws://172.22.0.2:8004/mcp_endpoint/mcp/?token=def
250705 INFO-=====请根据具体部署选择使用，请勿泄露给任何人======
```

请你把两个接口地址复制出来：

由于你是docker部署，切不可直接使用上面的地址！

由于你是docker部署，切不可直接使用上面的地址！

由于你是docker部署，切不可直接使用上面的地址！

你先把地址复制出来，放在一个草稿里，你要知道你的电脑的局域网ip是什么，例如我的电脑局域网ip是`192.168.1.25`，那么
原来我的接口地址
```
智控台MCP参数配置: http://172.22.0.2:8004/mcp_endpoint/health?key=abc
单模块部署MCP接入点: ws://172.22.0.2:8004/mcp_endpoint/mcp/?token=def
```
就要改成
```
智控台MCP参数配置: http://192.168.1.25:8004/mcp_endpoint/health?key=abc
单模块部署MCP接入点: ws://192.168.1.25:8004/mcp_endpoint/mcp/?token=def
```

改好后，请使用浏览器直接访问`智控台MCP参数配置`。当浏览器出现类似这样的代码，说明是成功了。
```
{"result":{"status":"success","connections":{"tool_connections":0,"robot_connections":0,"total_connections":0}},"error":null,"id":null,"jsonrpc":"2.0"}
```

请你保留好上面两个`接口地址`，下一步要用到。

# 2、全モジュールデプロイ時のMCPエンドポイント設定方法

全モジュールデプロイの場合、管理者アカウントで智控台にログインし、上部の`参数字典`をクリック、`参数管理`機能を選択します。

`server.mcp_endpoint`パラメータを検索し、値が`null`になっていることを確認します。
編集ボタンをクリックし、前のステップで取得した`智控台MCP参数配置`を`参数値`に貼り付けて保存します。

保存が成功すれば設定は完了です。失敗した場合、智控台がMCPエンドポイントにアクセスできないことを意味し、ネットワークファイアウォールや正しいローカルIPが設定されていない可能性があります。

# 3、単一モジュールデプロイ時のMCPエンドポイント設定方法

単一モジュールデプロイの場合、設定ファイル`data/.config.yaml`を開きます。
`mcp_endpoint`を検索し、見つからない場合は以下のように追加します。
```
server:
  websocket: ws://あなたのIPまたはドメイン:ポート番号/xiaozhi/v1/
  http_port: 8002
log:
  log_level: INFO

# その他の設定がここにある場合もあります

mcp_endpoint: あなたのエンドポイントwebsocketアドレス
```

`MCPエンドポイントサービスのデプロイ方法`で取得した`単一モジュールデプロイMCPエンドポイント`を`mcp_endpoint`に貼り付けます。例:

```
server:
  websocket: ws://あなたのIPまたはドメイン:ポート番号/xiaozhi/v1/
  http_port: 8002
log:
  log_level: INFO

# その他の設定がここにある場合もあります

mcp_endpoint: ws://192.168.1.25:8004/mcp_endpoint/mcp/?token=def
```

設定後、単一モジュールを起動すると以下のようなログが出力されます。
```
250705[__main__]-INFO-初期化コンポーネント: vad成功 SileroVAD
250705[__main__]-INFO-初期化コンポーネント: asr成功 FunASRServer
250705[__main__]-INFO-OTAインターフェース:          http://192.168.1.25:8002/xiaozhi/ota/
250705[__main__]-INFO-視覚分析インターフェース:     http://192.168.1.25:8002/mcp/vision/explain
250705[__main__]-INFO-MCPエンドポイント:        ws://192.168.1.25:8004/mcp_endpoint/mcp/?token=abc
250705[__main__]-INFO-Websocketアドレス:    ws://192.168.1.25:8000/xiaozhi/v1/
250705[__main__]-INFO-=======上記のアドレスはwebsocketプロトコルアドレスです、ブラウザで直接アクセスしないでください=======
250705[__main__]-INFO-Websocketをテストする場合はGoogle Chromeでtestディレクトリのtest_page.htmlを開いてください
250705[__main__]-INFO-=============================================================
```

上記のように`MCPエンドポイント: ws://192.168.1.25:8004/mcp_endpoint/mcp/?token=abc`が出力されれば設定は成功です。

