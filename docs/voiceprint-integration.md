# Voiceprint Recognition Enabling Guide

This tutorial consists of 3 parts
- 1. How to deploy the voiceprint recognition service
- 2. How to configure the voiceprint recognition interface when deploying all modules
- 3. How to configure voiceprint recognition in the most simplified deployment

# 1. How to deploy the voiceprint recognition service

## The first step is to download the source code of the voiceprint recognition project

Open the [Voiceprint Recognition Project Address](https://github.com/xinnan-tech/voiceprint-api) in your browser.

After opening, find a green button on the page with the word `Code` written on it, click it, and then you will see the `Download ZIP` button.

Click it to download the source code of this project. After downloading it to your computer, unzip it. At this time, its name may be called `voiceprint-api-main`
You need to rename it to `voiceprint-api`.

## Step 2: Create database and table

Voiceprint recognition requires a `MySQL` database. If you have previously deployed a `Smart Console`, you already have `MySQL` installed. You can share it.

You can try using the `telnet` command on the host machine to see if you can access the `3306` port of `mysql` normally.
```
telnet 127.0.0.1 3306
```
If you can access port 3306, please ignore the following content and go directly to step 3.

If you can't access it, you need to recall how you installed `mysql`.

If you installed MySQL using a package yourself, it means your MySQL server is isolated from the network. You may need to first resolve the issue of accessing port 3306 of MySQL server.

If you installed `mysql` through `docker-compose_all.yml` of this project, you need to find the `docker-compose_all.yml` file where you created the database and modify the following content

Before modification
```
  xiaozhi-esp32-server-db:
    ...
    networks:
      - default
    expose:
      - "3306:3306"
```

After modification
```
  xiaozhi-esp32-server-db:
    ...
    networks:
      - default
    ports:
      - "3306:3306"
```

Note that you need to change `expose` under `xiaozhi-esp32-server-db` to `ports`. After changing, you need to restart MySQL. The following is the command to restart MySQL:

```
# Enter the folder where your docker-compose_all.yml is located, for example, mine is xiaozhi-server
cd xiaozhi-server
docker compose -f docker-compose_all.yml down
docker compose -f docker-compose.yml up -d
```

After startup, use the `telnet` command on the host machine to see if you can access the `3306` port of `mysql` normally.
```
telnet 127.0.0.1 3306
```
Normally, this is accessible.

## Step 3: Create database and table
If your host machine can access the MySQL database normally, create a database named `voiceprint_db` and a `voiceprints` table on MySQL.

```
CREATE DATABASE voiceprint_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE voiceprint_db;

CREATE TABLE voiceprints (
    id INT AUTO_INCREMENT PRIMARY KEY,
    speaker_id VARCHAR(255) NOT NULL UNIQUE,
    feature_vector LONGBLOB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_speaker_id (speaker_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

## Step 4, configure database connection

Go to the `voiceprint-api` folder and create a folder named `data`.

Copy `voiceprint.yaml` from the `voiceprint-api` root directory to the `data` folder and rename it to `.voiceprint.yaml`

Next, you need to focus on configuring the database connection in `.voiceprint.yaml`.

```
mysql:
  host: "127.0.0.1"
  port: 3306
  user: "root"
  password: "your_password"
  database: "voiceprint_db"
```

Note! Since your voiceprint recognition service is deployed using Docker, `host` needs to be filled in with the LAN IP address of the machine where MySQL is located.

Note! Since your voiceprint recognition service is deployed using Docker, `host` needs to be filled in with the LAN IP address of the machine where MySQL is located.

Note! Since your voiceprint recognition service is deployed using Docker, `host` needs to be filled in with the LAN IP address of the machine where MySQL is located.

## Step 5, start the program
This project is a very simple one and it is recommended to run it using docker. However, if you do not want to use docker, you can refer to [this page](https://github.com/xinnan-tech/voiceprint-api/blob/main/README.md) to run it using the source code. The following is how to run it using docker

```
# Enter the source code root directory of this project
cd voiceprint-api

# Clear the cache
docker compose -f docker-compose.yml down
docker stop voiceprint-api
docker rm voiceprint-api
docker rmi ghcr.nju.edu.cn/xinnan-tech/voiceprint-api:latest

# Start the docker container
docker compose -f docker-compose.yml up -d
# View logs
docker logs -f voiceprint-api
```

At this point, the log will output a log similar to the following
```
250711 INFO-🚀 Start: Production environment service started (Uvicorn), listening address: 0.0.0.0:8005
250711 INFO-============================================================
250711 INFO-Voiceprint interface address: http://127.0.0.1:8005/voiceprint/health?key=abcd
250711 INFO-============================================================
```

Please copy the voiceprint interface address:

Since you are deploying with docker, do not use the above address directly!

Since you are deploying with docker, do not use the above address directly!

Since you are deploying with docker, do not use the above address directly!

First, copy the address and put it in a draft. You need to know what your computer's LAN IP is. For example, my computer's LAN IP is `192.168.1.25`, then
It turns out that my interface address
```
http://127.0.0.1:8005/voiceprint/health?key=abcd

```
It should be changed to
```
http://192.168.1.25:8005/voiceprint/health?key=abcd
```

After the modification, please use the browser to directly access the `Voiceprint Interface Address`. When the browser displays a code similar to this, it means it is successful.
```
{"total_voiceprints":0,"status":"healthy"}
```

Please keep the modified `Voiceprint Interface Address` as it will be used in the next step.

# 2. How to configure voiceprint recognition when deploying all modules

## Step 1: Configure the interface
If you are deploying a full module deployment, use the administrator account to log in to the intelligent console, click the `Parameter Dictionary` at the top, and select the `Parameter Management` function.

Then search for the parameter `server.voice_print`. At this point, its value should be `null`.
Click the Modify button and paste the Voiceprint Interface Address obtained in the previous step into the Parameter Value field. Then save the value.

If it is saved successfully, it means everything went well and you can go to the smart body to check the effect. If it is not successful, it means that the smart console cannot access the voiceprint recognition. It is very likely that there is a network firewall or the correct LAN IP is not entered.

## The second step is to set the agent memory mode

Enter your agent's character configuration, set the memory to `Local Short-Term Memory`, and be sure to enable `Report Text + Voice`.

## Step 3: Chat with your agent

Power on your device and chat with him at a normal speed and tone.

## Step 4: Set up voiceprint

On the Smart Dashboard, under the "Agent Management" page, in the "Agent" panel, there's a "Voiceprint Recognition" button. Click it. At the bottom, there's a "Add" button. You can then register a voiceprint of someone's words.
In the pop-up box, it is recommended to fill in the "Description" attribute, which can include the person's occupation, personality, and hobbies. This will help the agent analyze and understand the speaker.

## Step 3: Chat with your agent

Power on your device and ask it, "Do you know who I am?" If it can answer, it means the voiceprint recognition function is working properly.

# 3. How to configure voiceprint recognition in the most simplified deployment

## Step 1: Configure the interface
Open the `xiaozhi-server/data/.config.yaml` file (create it if it doesn't exist) and add/modify the following content:

```
# Voiceprint Recognition Configuration
voiceprint:
  # Voiceprint interface address
  url: your voiceprint interface address
  # Speaker configuration: speaker_id, name, description
  speakers:
    - "test1, Zhang San, Zhang San is a programmer"
    - "test2, Li Si, Li Si is a product manager"
    - "test3, Wang Wu, Wang Wu is a designer"
```

Paste the `voiceprint interface address` obtained in the previous step into `url` and save.

The `speakers` parameter is added as needed. Note the `speaker_id` parameter, which will be used later when registering the voiceprint.

## Step 2: Register voiceprint
If you have already started the voiceprint service, you can view the API documentation by visiting `http://localhost:8005/voiceprint/docs` in your local browser. Here we only explain how to use the API to register voiceprints.

The API address for registering voiceprint is `http://localhost:8005/voiceprint/register`, and the request method is POST.

The request header needs to include Bearer Token authentication. The token is the part after `?key=` in the `voiceprint interface address`. For example, if my voiceprint registration address is `http://127.0.0.1:8005/voiceprint/health?key=abcd`, then my token is `abcd`.

The request body contains the speaker ID (speaker_id) and the WAV audio file (file). The request example is as follows:

```
curl -X POST \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "speaker_id=your_speaker_id_here" \
  -F "file=@/path/to/your/file" \
  http://localhost:8005/voiceprint/register
```

 Here, `file` is the audio file of the speaker you want to register. `speaker_id` must be the same as the `speaker_id` configured in the first step. For example, if I need to register Zhang San's voiceprint, and Zhang San's `speaker_id` is `test1` in `.config.yaml`, then when registering Zhang San's voiceprint, `speaker_id` in the request body will be `test1`, and `file` should be the audio file of Zhang San speaking.

 ## Step 3: Start the service

Start the Xiaozhi server and voiceprint service and you can use it normally.
