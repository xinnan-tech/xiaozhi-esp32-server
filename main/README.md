本文档是开发类文档，如需部署小智服务端，[点击这里查看部署教程](./FAQ.md#%E4%BD%BF%E7%94%A8%E6%96%B9%E5%BC%8F-)

# 项目目录介绍
当你看到这份文件的时候，这个这个项目还没完善好。我们还有很多东西要做。

如果你是一名软件开发者，这里有一份[《致开发者的公开信》](../docs/contributor_open_letter.md)，欢迎归队！

```
xiaozhi-esp32-server
  ├─ xiaozhi-server 8000 端口 Python语言开发 负责与esp32通信
  ├─ manager-web 8001 端口 Node.js+Vue开发 负责提供控制台的web界面
  ├─ manager-api 8002 端口 Java语言开发 负责提供控制台的api
```

# xiaozhi-server 接口协议

[虾哥团队通信协议：Websocket 连接](https://ccnphfhqs21z.feishu.cn/wiki/M0XiwldO9iJwHikpXD5cEx71nKh)

# manager-web 、manager-api接口协议

https://2662r3426b.vicp.fun/xiaozhi-esp32-api/api/v1/doc.html
