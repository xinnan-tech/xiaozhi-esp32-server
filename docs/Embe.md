# mac

docker需要开8g才能运行成功

后续设备对话又爆内存

```sh
brew install git-lfs
cd models
GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/jinaai/jina-embeddings-v2-base-zh
cd jina-embeddings-v2-base-zh
git lfs pull
```