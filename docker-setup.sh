#!/bin/bash

# 设置颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}开始安装小智服务端...${NC}"

# 创建必要的目录
echo "创建目录结构..."
mkdir -p xiaozhi-server/data xiaozhi-server/models/SenseVoiceSmall
cd xiaozhi-server

# 下载语音识别模型
echo "下载语音识别模型..."
curl -L --progress-bar -o models/SenseVoiceSmall/model.pt https://modelscope.cn/models/iic/SenseVoiceSmall/resolve/master/model.pt
if [ $? -ne 0 ]; then
    echo -e "${RED}模型下载失败。请手动从以下地址下载：${NC}"
    echo "1. https://modelscope.cn/models/iic/SenseVoiceSmall/resolve/master/model.pt"
    echo "2. 百度网盘: https://pan.baidu.com/share/init?surl=QlgM58FHhYv1tFnUT_A8Sg (提取码: qvna)"
    echo "下载后请将文件放置在 models/SenseVoiceSmall/model.pt"
fi

# 下载配置文件
echo "下载配置文件..."
curl -L --progress-bar -o docker-compose.yml https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/main/main/xiaozhi-server/docker-compose.yml
curl -L --progress-bar -o data/.config.yaml https://raw.githubusercontent.com/xinnan-tech/xiaozhi-esp32-server/main/main/xiaozhi-server/config.yaml

# 检查文件是否存在
echo "检查文件完整性..."
files_to_check=("docker-compose.yml" "data/.config.yaml" "models/SenseVoiceSmall/model.pt")
all_files_exist=true

for file in "${files_to_check[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}错误: $file 不存在${NC}"
        all_files_exist=false
    fi
done

if [ "$all_files_exist" = false ]; then
    echo -e "${RED}某些文件下载失败，请检查上述错误信息并手动下载缺失的文件。${NC}"
    exit 1
fi

echo -e "${GREEN}文件下载完成！${NC}"
echo "请编辑 data/.config.yaml 文件配置你的API密钥。"
echo "配置完成后，运行以下命令启动服务："
echo -e "${GREEN}docker-compose up -d${NC}"
echo "查看日志请运行："
echo -e "${GREEN}docker logs -f xiaozhi-esp32-server${NC}"

# 提示用户编辑配置文件
echo -e "\n${RED}重要提示：${NC}"
echo "1. 请确保编辑 data/.config.yaml 文件，配置必要的API密钥"
echo "2. 特别是 ChatGLM 和 mem0ai 的密钥必须配置"
echo "3. 配置完成后再启动 docker 服务"