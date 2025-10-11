# Dockerイメージをローカルでビルドする方法

現在、このプロジェクトではGithub Actionsを使用してDockerイメージを自動的にビルドしていますが、このドキュメントはローカルでDockerイメージをビルドする必要がある方向けです。

1. Dockerのインストール
```
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```
2. Dockerイメージのビルド
```
# プロジェクトのルートディレクトリに移動
# serverのビルド
docker build -t xiaozhi-esp32-server:server_latest -f ./Dockerfile-server .
# webのビルド
docker build -t xiaozhi-esp32-server:web_latest -f ./Dockerfile-web .

# ビルド完了後、docker-composeを使用してプロジェクトを起動できます
# docker-compose.ymlを自分でビルドしたイメージのバージョンに修正する必要があります
cd main/xiaozhi-server
docker-compose up -d
```
