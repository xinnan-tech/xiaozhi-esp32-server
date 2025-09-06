module.exports = {
  apps: [
    {
      name: "manager-api",
      script: "mvn",
      args: "spring-boot:run",
      cwd: "/root/xiaozhi-esp32-server/main/manager-api",
      interpreter: "none"   // important, tells PM2 not to use node/python
    },
      {
      name: "manager-web",
      script: "npm",
      args: "run serve",
      cwd: "/root/xiaozhi-esp32-server/main/manager-web",
      interpreter: "none"
    },
 
    {
      name: "mqtt-gateway",
      script: "app.js",
      cwd: "/root/xiaozhi-esp32-server/main/mqtt-gateway",
      interpreter: "node",
      watch: true
    }
  ]
};

