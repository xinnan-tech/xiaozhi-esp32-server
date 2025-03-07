# 使用 Java 21 作为基础镜像
FROM eclipse-temurin:21-jdk-jammy

# 设置工作目录
WORKDIR /app

# 复制 Maven 配置文件
COPY pom.xml .

# 复制源代码和配置文件
COPY src ./src

# 安装 Maven
RUN apt-get update && \
    apt-get install -y maven && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 编译打包，跳过测试编译
RUN mvn install -Dmaven.test.skip=true

# 暴露端口
EXPOSE 8002

# 启动应用
CMD ["sh", "-c", "java -jar target/xiaozhi-esp32-api.jar \
    --spring.datasource.druid.url=${SPRING_DATASOURCE_DRUID_URL} \
    --spring.datasource.druid.username=${SPRING_DATASOURCE_DRUID_USERNAME} \
    --spring.datasource.druid.password=${SPRING_DATASOURCE_DRUID_PASSWORD} \
    --spring.data.redis.host=${SPRING_DATA_REDIS_HOST} \
    --spring.data.redis.port=${SPRING_DATA_REDIS_PORT}"] 