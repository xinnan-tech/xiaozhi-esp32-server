const { Room } = require('@livekit/rtc-node');
const { AccessToken } = require('livekit-server-sdk');
const fs = require('fs');
const path = require('path');

async function testConnection() {
  let config;
  try {
    const configFile = fs.readFileSync(path.join(__dirname, 'config', 'mqtt.json'), 'utf8');
    config = JSON.parse(configFile);
  } catch (e) {
    console.error('Error: Could not read or parse config/mqtt.json.', e);
    return;
  }

  if (!config.livekit || !config.livekit.url || !config.livekit.api_key || !config.livekit.api_secret) {
    console.error('Error: livekit configuration is missing or incomplete in config/mqtt.json.');
    return;
  }

  const { url, api_key, api_secret } = config.livekit;
  const roomName = `test-connection-${Date.now()}`;
  const participantName = 'diagnostic-script';

  console.log(`---> [TEST SCRIPT] Connecting with URL: '${url}'`);
  console.log(`Room: ${roomName}, Participant: ${participantName}`);

  const at = new AccessToken(api_key, api_secret, {
    identity: participantName,
  });
  
  at.addGrant({ 
    room: roomName, 
    roomJoin: true, 
    roomCreate: true, 
    canPublish: true, 
    canSubscribe: true 
  });
  
  const token = await at.toJwt(); // Make this async
  console.log('Generated Access Token.');
  
  const room = new Room();

  // Add connection state monitoring
  room.on('connectionStateChanged', (state) => {
    console.log('Connection state changed:', state);
  });
  
  room.on('connected', () => {
    console.log('Room connected event fired');
  });
  
  room.on('disconnected', (reason) => {
    console.log('Room disconnected:', reason);
  });

  try {
    console.log('Attempting to connect...');
    await room.connect(url, token, { 
      autoSubscribe: true, 
      dynacast: true 
    });
    
    console.log('✅ ✅ ✅  Successfully connected to LiveKit room! ✅ ✅ ✅');
    console.log('Connection state:', room.connectionState);
    console.log('Is connected:', room.isConnected);
    console.log('Local participant:', room.localParticipant?.identity);
    
    // Wait a moment to ensure connection is stable
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    console.log('The issue is likely within the mqtt-gateway application logic.');
    await room.disconnect();
    console.log('Disconnected successfully');
    
  } catch (error) {
    console.error('❌ ❌ ❌  Failed to connect to LiveKit. ❌ ❌ ❌');
    console.error('This indicates an issue with your network environment or the credentials in mqtt.json.');
    console.error('Error name:', error.name);
    console.error('Error message:', error.message);
    console.error('Full error:', error);
  }
}

testConnection().catch(console.error);
