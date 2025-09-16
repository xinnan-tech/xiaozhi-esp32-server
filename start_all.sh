#!/bin/bash

# This script provides the commands to run all the necessary projects for the xiaozhi-esp32-server.
# Please open a separate terminal window for each of the following commands.

# --- Terminal 1: Start xiaozhi-server (Python backend) ---
# cd main/xiaozhi-server
# pip install -r requirements.txt  # If you haven't installed dependencies
# python app.py

# --- Terminal 2: Start manager-api (Java backend) ---
# cd main/manager-api
# ./mvnw spring-boot:run

# --- Terminal 3: Start manager-web (Vue.js frontend) ---
# cd main/manager-web
# npm install  # If you haven't installed dependencies
# npm run serve

# --- Terminal 4: Start mqtt-gateway (Node.js) ---
# cd main/mqtt-gateway
# npm install  # If you haven't installed dependencies
# node app.js
