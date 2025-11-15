# Full module source code deployment automatic upgrade method

This tutorial is for those who are interested in deploying full-module source code. It shows you how to use automatic commands to automatically pull source code, automatically compile, and automatically start port operations, achieving the most efficient upgrade system.

The test platform of this project, `https://2662r3426b.vicp.fun`, has used this method since it was released, with good results.

For tutorials, please refer to the video tutorial released by B station blogger `Bi Le Labs`: [Open Source Xiaozhi Server xiaozhi-server automatic update and the latest version of MCP access point configuration nanny tutorial] (https://www.bilibili.com/video/BV15H37zHE7Q)

# Start conditions
- Your computer/server is running Linux
- You've run through the entire process.
- You like to keep up with the latest features, but find it troublesome to deploy manually each time, and hope to have an automatic update method

The second condition must be met because some of the files involved in this tutorial, such as JDK, Node.js environment, and Conda environment, require you to run through the entire process. If you don't run through it, you may not know what I mean when I talk about a certain file.

# Tutorial Effect
- Solve the problem of not being able to pull the latest project source code in China
- Automatically pull code and compile front-end files
- Automatically pull code to compile Java files, automatically kill port 8002, and automatically start port 8002
- Automatically pull Python code, automatically kill port 8000, and automatically start port 8000

# The first step is to choose your project directory

For example, I planned my project directory to be a new blank directory. If you don’t want to make mistakes, you can do the same as me.
```
/home/system/xiaozhi
```

# Step 2: Clone this project
At this moment, you must first execute the first sentence to pull the source code. This command is applicable to servers and computers on the domestic network and does not require a VPN.

```
cd /home/system/xiaozhi
git clone https://ghproxy.net/https://github.com/xinnan-tech/xiaozhi-esp32-server.git
```

After the execution, your project directory will have an additional folder `xiaozhi-esp32-server`, which is the source code of the project

# The third step is to copy the basic files

If you have run through the entire process before, you will be familiar with the funasr model file `xiaozhi-server/models/SenseVoiceSmall/model.pt` and your private configuration file `xiaozhi-server/data/.config.yaml`.

Now you need to copy the `model.pt` file to the new directory, you can do this
```
# Create the required directories
mkdir -p /home/system/xiaozhi/xiaozhi-esp32-server/main/xiaozhi-server/data/

cp your original .config.yaml full path /home/system/xiaozhi/xiaozhi-esp32-server/main/xiaozhi-server/data/.config.yaml
cp your original model.pt full path /home/system/xiaozhi/xiaozhi-esp32-server/main/xiaozhi-server/models/SenseVoiceSmall/model.pt
```

# The fourth step is to create three automatic compilation files

## 4.1 Automatically compile the mananger-web module
In the `/home/system/xiaozhi/` directory, create a file named `update_8001.sh` with the following content

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

After saving, execute the empowerment command
```
chmod 777 update_8001.sh
```
After execution, continue to

## 4.2 Automatically compile and run the manager-api module
In the `/home/system/xiaozhi/` directory, create a file named `update_8002.sh` with the following content

```
cd /home/system/xiaozhi/xiaozhi-esp32-server
git pull origin main


cd /home/system/xiaozhi/xiaozhi-esp32-server/main/manager-api
rm -rf target
mvn clean package -Dmaven.test.skip=true
cd /home/system/xiaozhi/

# Find the process number occupying port 8002
PID=$(sudo netstat -tulnp | grep 8002 | awk '{print $7}' | cut -d'/' -f1)

rm -rf /home/system/xiaozhi/xiaozhi-esp32-api.jar
mv /home/system/xiaozhi/xiaozhi-esp32-server/main/manager-api/target/xiaozhi-esp32-api.jar /home/system/xiaozhi/xiaozhi-esp32-api.jar

# Check if the process ID is found
if [ -z "$PID" ]; then
  echo "No process occupying port 8002 was found"
else
  echo "Found the process occupying port 8002, process ID: $PID"
  # Kill the process
  kill -9 $PID
  kill -9 $PID
  echo "Process $PID has been killed"
fi

nohup java -jar xiaozhi-esp32-api.jar --spring.profiles.active=dev &

tail tail -f nohup.out
```

After saving, execute the empowerment command
```
chmod 777 update_8002.sh
```
After execution, continue to

## 4.3 Automatically compile and run Python projects
In the `/home/system/xiaozhi/` directory, create a file named `update_8000.sh` with the following content

```
cd /home/system/xiaozhi/xiaozhi-esp32-server
git pull origin main

# Find the process number occupying port 8000
PID=$(sudo netstat -tulnp | grep 8000 | awk '{print $7}' | cut -d'/' -f1)

# Check if the process ID is found
if [ -z "$PID" ]; then
  echo "No process occupying port 8000 was found"
else
  echo "Found the process occupying port 8000, process ID: $PID"
  # Kill the process
  kill -9 $PID
  kill -9 $PID
  echo "Process $PID has been killed"
fi
cd main/xiaozhi-server
# Initialize the conda environment
source ~/.bashrc
conda activate xiaozhi-esp32-server
pip install -r requirements.txt
nohup python app.py >/dev/null &
tail -f /home/system/xiaozhi/xiaozhi-esp32-server/main/xiaozhi-server/tmp/server.log
```

After saving, execute the empowerment command
```
chmod 777 update_8000.sh
```
After execution, continue to

# Daily Updates

After the above scripts are created, for daily updates, we only need to execute the following commands in sequence to automatically update and start

```
cd /home/system/xiaozhi
# Update and start the Java program
./update_8001.sh
# Update web application
./update_8002.sh
# Update and start the python program
./update_8000.sh


# If you want to view the Java log later, execute the following command
tail -f nohup.out
# If you want to view the python log later, execute the following command
tail -f /home/system/xiaozhi/xiaozhi-esp32-server/main/xiaozhi-server/tmp/server.log
```

# Notes
The test platform `https://2662r3426b.vicp.fun` uses nginx as a reverse proxy. The detailed configuration of nginx.conf can be found here [https://github.com/xinnan-tech/xiaozhi-esp32-server/issues/791]

## Frequently Asked Questions

### 1. Why can’t I see port 8001?
Answer: Port 8001 is used in the development environment and is used to run the front-end. If you are deploying on a server, it is not recommended to use `npm run serve` to start the front-end on port 8001. Instead, compile it into an HTML file as shown in this tutorial and use nginx to manage access.

### 2. Do I need to update the manual SQL statement every time I update?
Answer: No, because the project uses **Liquibase** to manage the database version, which will automatically execute the new SQL script.
