# 全模块源码部署自动升级方法

本教程是方便全模块源码部署的爱好者，如何通过自动命令，自动拉取源码，自动编译，自动启动端口运行。实现最高效率的升级系统。

本项目的测试平台`https://2662r3426b.vicp.fun`，从开放以来就使用了该方法，效果良好。

教程可参考B站博主`毕乐labs`发布的视频教程：[《开源小智服务器xiaozhi-server自动更新以及最新版本MCP接入点配置保姆教程》](https://www.bilibili.com/video/BV15H37zHE7Q)

# 开始条件
- 你的电脑/服务器是linux操作系统
- 你已经跑通了整个流程
- 你喜欢跟进最新功能，但是觉得每次手动部署有点麻烦，期待有一个自动更新的方法

第二个条件必须满足，因为本教程所涉及的某些文件，JDK、Node.js环境、Conda环境等，是需要你跑通整个流程才有的，如果你没有跑通，当我讲到某个文件的时候，你可能就不知道什么意思。

# 教程效果
- 解决国内不能拉取最新项目源码问题
- 自动拉取代码编译前端文件
- 自动拉取代码编译java文件，自动杀掉8002端口，自动启动8002端口
- 自动拉取python代码，自动杀掉8000端口，自动启动8000端口

# 第一步 选好你的项目目录

例如，我规划了我的项目目录是，这是一个新建的空白的目录，如果你不想出错，可以和我一样
```
/home/system/xiaozhi
```

# 第二步 克隆本项目
此刻，先要执行第一句话，拉取源码，这句命令适用于国内网络的服务器和电脑，无需翻墙

```
cd /home/system/xiaozhi
git clone https://ghproxy.net/https://github.com/xinnan-tech/xiaozhi-esp32-server.git
```

执行完后，你的项目目录会多了一个文件夹`xiaozhi-esp32-server`，这个就是项目的源码

# 第三步 复制基础的文件

如果你之前已经跑通了整个流程，对funasr的模型文件`xiaozhi-server/models/SenseVoiceSmall/model.pt`和你的私有配置文件`xiaozhi-server/data/.config.yaml`这两个文件不会陌生。

此刻你需要把`model.pt`文件复制到新的目录去，你可以这样
```
# 创建需要的目录
mkdir -p /home/system/xiaozhi/xiaozhi-esp32-server/main/xiaozhi-server/data/

cp 你原来的.config.yaml完整路径 /home/system/xiaozhi/xiaozhi-esp32-server/main/xiaozhi-server/data/.config.yaml
cp 你原来的model.pt完整路径 /home/system/xiaozhi/xiaozhi-esp32-server/main/xiaozhi-server/models/SenseVoiceSmall/model.pt
```

# 第四步 建立三个自动编译文件

## 4.1 自动编译mananger-web模块
在`/home/system/xiaozhi/`目录下，创建名字为`update_8001.sh`的文件，内容如下

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

保存好后执行赋权命令
```
chmod 777 update_8001.sh
```
执行完后，继续往下

## 4.2 自动编译运行manager-api模块
在`/home/system/xiaozhi/`目录下，创建名字为`update_8002.sh`的文件，内容如下

```
cd /home/system/xiaozhi/xiaozhi-esp32-server
git pull origin main


cd /home/system/xiaozhi/xiaozhi-esp32-server/main/manager-api
rm -rf target
mvn clean package -Dmaven.test.skip=true
cd /home/system/xiaozhi/

# 查找占用8002端口的进程号
PID=$(sudo netstat -tulnp | grep 8002 | awk '{print $7}' | cut -d'/' -f1)

rm -rf /home/system/xiaozhi/xiaozhi-esp32-api.jar
mv /home/system/xiaozhi/xiaozhi-esp32-server/main/manager-api/target/xiaozhi-esp32-api.jar /home/system/xiaozhi/xiaozhi-esp32-api.jar

# 检查是否找到进程号
if [ -z "$PID" ]; then
  echo "没有找到占用8002端口的进程"
else
  echo "找到占用8002端口的进程，进程号为: $PID"
  # 杀掉进程
  kill -9 $PID
  kill -9 $PID
  echo "已杀掉进程 $PID"
fi

nohup java -jar xiaozhi-esp32-api.jar --spring.profiles.active=dev &
```

保存好后执行赋权命令
```
chmod 777 update_8002.sh
```
执行完后，继续往下

## 4.3 自动编译运行Python项目
在`/home/system/xiaozhi/`目录下，创建名字为`update_8000.sh`的文件，内容如下

```
cd /home/system/xiaozhi/xiaozhi-esp32-server
git pull origin main

# 查找占用8000端口的进程号
PID=$(sudo netstat -tulnp | grep 8000 | awk '{print $7}' | cut -d'/' -f1)

# 检查是否找到进程号
if [ -z "$PID" ]; then
  echo "没有找到占用8000端口的进程"
else
  echo "找到占用8000端口的进程，进程号为: $PID"
  # 杀掉进程
  kill -9 $PID
  kill -9 $PID
  echo "已杀掉进程 $PID"
fi
cd main/xiaozhi-server
pip install -r requirements.txt
nohup python app.py >/dev/null &
```

保存好后执行赋权命令
```
chmod 777 update_8000.sh
```
执行完后，继续往下

# 日常更新

以上的脚本都建立好后，日常更新，我们只要依次执行以下命令就可以做到自动更新和启动

```
# 进入pyhton环境
conda activate xiaozhi-esp32-server
cd /home/system/xiaozhi
# 更新并启动Java程序
./update_8001.sh
# 更新web程序
./update_8002.sh
# 更新并启动python程序
./update_8000.sh
# 查看Java日志
tail -f nohup.out
# 查看Python日志
tail -f /home/system/xiaozhi/xiaozhi-esp32-server/main/xiaozhi-server/tmp/server.log
```

# 注意事项
测试平台`https://2662r3426b.vicp.fun`，是使用nginx做了反向代理。nginx.conf详细配置可以[参考这里](https://github.com/xinnan-tech/xiaozhi-esp32-server/issues/791)

## 常见问题

### 1、为什么没有见到8001端口？
回答：8001是开发环境使用的，用于运行前端的端口。如果你是服务器部署，不建议使用`npm run serve`启动8001端口运行前端，而是像本教程一样编译成html文件，然后使用nginx来管理访问。

### 2、每次更新需要更新手动SQL语句吗？
回答：不需要，因为项目使用**Liquibase**管理数据库版本，会自动执行新的sql脚本。