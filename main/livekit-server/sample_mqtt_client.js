
const mqtt = require('mqtt');

// MQTT broker details from config.yaml
const brokerUrl = 'mqtt://192.168.1.8:1883';

// Client details
const clientId = 'GID_test@@@00:11:22:33:44:55'; // Example clientId
const username = 'testuser'; // Example username
const password = 'testpassword'; // Example password

const options = {
  clientId: clientId,
  username: username,
  password: password,
  clean: true,
  connectTimeout: 4000,
};

const client = mqtt.connect(brokerUrl, options);

const topic = 'devices/p2p/00:11:22:33:44:55';

client.on('connect', () => {
  console.log('Connected to MQTT broker');

  client.subscribe(topic, (err) => {
    if (!err) {
      console.log(`Subscribed to topic: ${topic}`);
      // Send a hello message
      const helloMessage = {
        type: 'hello',
        version: 3,
        audio_params: {},
        features: {}
      };
      client.publish(topic, JSON.stringify(helloMessage));
      console.log(`Published 'hello' message to ${topic}`);
    } else {
        console.error(`Subscription error: ${err}`);
    }
  });
});

client.on('message', (topic, message) => {
  console.log(`Received message on topic ${topic}: ${message.toString()}`);
  // Close the connection after receiving a message
  client.end();
});

client.on('error', (err) => {
  console.error('Connection error:', err);
  client.end();
});

client.on('close', () => {
  console.log('Connection closed');
});
