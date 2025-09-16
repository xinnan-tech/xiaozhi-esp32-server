import json
import time
import uuid
import threading
import socket
import struct
import logging
import pyaudio
import keyboard

from typing import Dict, Optional, Tuple
import requests
import paho.mqtt.client as mqtt_client
from paho.mqtt.enums import CallbackAPIVersion
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from queue import Queue, Empty
import opuslib

# --- Configuration ---

SERVER_IP = "139.59.7.72" # !!! UPDATE with your server's local IP address !!!
OTA_PORT = 8002
MQTT_BROKER_HOST = "139.59.7.72"  # Your EMQX instance


MQTT_BROKER_PORT = 1883
# DEVICE_MAC is now dynamically generated for uniqueness
PLAYBACK_BUFFER_MIN_FRAMES = 3  # Minimum frames to have in buffer to continue playback
PLAYBACK_BUFFER_START_FRAMES = 16 # Number of frames to buffer before starting playback

# --- NEW: Sequence tracking configuration ---
ENABLE_SEQUENCE_LOGGING = True  # Set to False to disable sequence loggingdocker-compose logs -f appserver
LOG_SEQUENCE_EVERY_N_PACKETS = 16  # Log every N packets instead of every packet

# --- NEW: Timeout configurations ---
TTS_TIMEOUT_SECONDS = 30  # Maximum time to wait for TTS audio
BUFFER_TIMEOUT_SECONDS = 10  # Maximum time to wait for initial buffering
KEEP_ALIVE_INTERVAL = 5  # Send keep-alive every N seconds

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("TestClient")

# --- Global variables ---
mqtt_message_queue = Queue()
udp_session_details = {}
stop_threads = threading.Event()
start_recording_event = threading.Event() # Event to signal recording thread to start
stop_recording_event = threading.Event()  # Event to signal recording thread to stop

def generate_mqtt_credentials(device_mac: str) -> Dict[str, str]:
    """Generate MQTT credentials for the gateway."""
    import base64
    import hashlib
    import hmac
    
    # Create client ID
    client_id = f"GID_test@@@{device_mac}@@@{uuid.uuid4()}"
    
    # Create username (base64 encoded JSON)
    username_data = {"ip": "192.168.1.10"}  # Placeholder IP
    username = base64.b64encode(json.dumps(username_data).encode()).decode()
    
    # Create password (HMAC-SHA256) - must match gateway's logic
    # Gateway uses: clientId + '|' + username as content
    secret_key = "test-signature-key-12345"  # Must match MQTT_SIGNATURE_KEY in gateway's .env
    content = f"{client_id}|{username}"
    password = base64.b64encode(hmac.new(secret_key.encode(), content.encode(), hashlib.sha256).digest()).decode()
    
    return {
        "client_id": client_id,
        "username": username,
        "password": password
    }

def generate_unique_mac() -> str:
    """Generates a unique MAC address for the client."""
    # Generate 6 random bytes for the MAC address
    # Using a common OUI prefix (00:16:3E) for locally administered addresses
    # and then random bytes to ensure uniqueness for each client instance.
    mac_bytes = [0x00, 0x16, 0x3E, # OUI prefix
                 uuid.uuid4().bytes[0], uuid.uuid4().bytes[1], uuid.uuid4().bytes[2]]
    return '_'.join(f'{b:02x}' for b in mac_bytes)

class TestClient:
    def __init__(self):
        self.mqtt_client = None
        # Generate a unique MAC address for this client instance
        self.device_mac_formatted = "00:16:3e:ac:b5:38"
        print(f"Generated unique MAC address: {self.device_mac_formatted}")
        
        # MQTT credentials will be set from OTA response
        self.mqtt_credentials = None
        
        # The P2P topic will now be unique to this client's MAC address
        self.p2p_topic = f"devices/p2p/{self.device_mac_formatted}"
        self.ota_config = {}
        self.websocket_url = None  # Will be set from OTA endpoint
        self.udp_socket = None
        self.udp_listener_thread = None
        self.playback_thread = None
        self.audio_recording_thread = None
        self.udp_local_sequence = 0
        self.audio_playback_queue = Queue()
        
        # --- NEW: Sequence tracking variables ---
        self.expected_sequence = 1  # Expected next sequence number
        self.last_received_sequence = 0  # Last sequence number received
        self.total_packets_received = 0  # Total packets received
        self.out_of_order_packets = 0  # Count of out-of-order packets
        self.duplicate_packets = 0  # Count of duplicate packets
        self.missing_packets = 0  # Count of missing packets
        self.sequence_gaps = []  # List of detected gaps in sequence
        
        # --- NEW: State tracking ---
        self.tts_active = False
        self.last_audio_received = 0
        self.session_active = True
        self.conversation_count = 0
        
        logger.info(f"Client initialized with unique MAC: {self.device_mac_formatted}")

    def on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        """Callback for MQTT connection."""
        if rc == 0:
            logger.info(f"✅ MQTT Connected! Subscribing to P2P topic: {self.p2p_topic}")
            client.subscribe(self.p2p_topic)
        else:
            logger.error(f"❌ MQTT Connection failed with code {rc}")

    def on_mqtt_message(self, client, userdata, msg):
        """Callback for MQTT message reception."""
        try:
            payload_str = msg.payload.decode()
            payload = json.loads(payload_str)
            logger.info(f"📨 MQTT Message received on topic '{msg.topic}':\n{json.dumps(payload, indent=2)}")
            
            # Handle TTS start signal (reset sequence tracking)
            if payload.get("type") == "tts" and payload.get("state") == "start":
                logger.info("🎵 TTS started. Resetting sequence tracking.")
                self.tts_active = True
                self.reset_sequence_tracking()
            
            # Handle TTS stop signal (start recording for next user input)
            elif payload.get("type") == "tts" and payload.get("state") == "stop":
                logger.info("🎤 TTS finished. Received 'stop' signal. Preparing for microphone capture...")
                self.tts_active = False
                self.print_sequence_summary()  # Print summary when TTS ends
                
                # Only proceed with recording if we actually received audio
                if self.total_packets_received > 0:
                    # Clear the stop event to allow the recording thread to continue or start
                    stop_recording_event.clear() 
                    # Set the start event to signal the recording thread to begin (if it was waiting)
                    start_recording_event.set()
                    logger.info("🎤 Cleared stop_recording_event and set start_recording_event for next recording.")
                else:
                    logger.warning("⚠️ No audio packets received during TTS. Server may have an issue.")
                    # Try to trigger another conversation after a short delay
                    threading.Timer(2.0, self.retry_conversation).start()
            
            # Handle STT message (server processed our speech)
            elif payload.get("type") == "stt":
                transcription = payload.get("text", "")
                logger.info(f"🗣️ Server transcribed: '{transcription}'")
            
            # Handle record stop signal (stop recording)
            elif payload.get("type") == "record_stop":
                logger.info("🛑 Received 'record_stop' signal from server. Stopping current audio recording...")
                stop_recording_event.set() # This will cause the recording thread loop to exit
            
            else:
                mqtt_message_queue.put(payload)
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Error processing MQTT message: {e}")

    def retry_conversation(self):
        """Retry triggering a conversation if no audio was received."""
        if self.session_active and not self.tts_active:
            self.conversation_count += 1
            logger.info(f"🔄 Retry attempt #{self.conversation_count}: Sending listen message again...")
            
            if self.conversation_count < 3:  # Limit retries
                listen_payload = {
                    "type": "listen", 
                    "session_id": udp_session_details["session_id"], 
                    "state": "detect", 
                    "text": f"retry attempt {self.conversation_count}"
                }
                if self.mqtt_client:
                    self.mqtt_client.publish("device-server", json.dumps(listen_payload))
            else:
                logger.error("❌ Too many retry attempts. There may be a server issue.")
                self.session_active = False

    def reset_sequence_tracking(self):
        """Reset sequence tracking statistics for a new TTS stream."""
        self.expected_sequence = 1
        self.last_received_sequence = 0
        self.total_packets_received = 0
        self.out_of_order_packets = 0
        self.duplicate_packets = 0
        self.missing_packets = 0
        self.sequence_gaps = []
        self.last_audio_received = time.time()
        if ENABLE_SEQUENCE_LOGGING:
            logger.info("🔄 Reset sequence tracking for new TTS stream")

    def print_sequence_summary(self):
        """Print a summary of sequence statistics."""
        if not ENABLE_SEQUENCE_LOGGING:
            return
            
        logger.info("=" * 60)
        logger.info("📊 SEQUENCE TRACKING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"📦 Total packets received: {self.total_packets_received}")
        logger.info(f"🔢 Last sequence number: {self.last_received_sequence}")
        logger.info(f"❌ Missing packets: {self.missing_packets}")
        logger.info(f"🔄 Out-of-order packets: {self.out_of_order_packets}")
        logger.info(f"🔁 Duplicate packets: {self.duplicate_packets}")
        
        if self.sequence_gaps:
            logger.info(f"🕳️  Sequence gaps detected: {len(self.sequence_gaps)}")
            for gap in self.sequence_gaps[-5:]:  # Show last 5 gaps
                logger.info(f"   Gap: expected {gap['expected']}, got {gap['received']}")
        else:
            logger.info("✅ No sequence gaps detected")
        
        # Calculate packet loss percentage
        if self.last_received_sequence > 0:
            expected_total = self.last_received_sequence
            loss_rate = (self.missing_packets / expected_total) * 100
            logger.info(f"📈 Packet loss rate: {loss_rate:.2f}%")
        
        logger.info("=" * 60)

    def parse_packet_header(self, header: bytes) -> Dict:
        """Parse the packet header to extract sequence and other info."""
        if len(header) < 16:
            return {}
        
        try:
            # Unpack header: packet_type, flags, payload_len, ssrc, timestamp, sequence
            packet_type, flags, payload_len, ssrc, timestamp, sequence = struct.unpack('>BBHIII', header)
            return {
                'packet_type': packet_type,
                'flags': flags,
                'payload_len': payload_len,
                'ssrc': ssrc,
                'timestamp': timestamp,
                'sequence': sequence
            }
        except struct.error:
            return {}

    def track_sequence(self, sequence: int):
        """Track and analyze packet sequence numbers."""
        if not ENABLE_SEQUENCE_LOGGING:
            return
            
        self.total_packets_received += 1
        self.last_audio_received = time.time()
        
        # Check for out-of-order packets
        if sequence < self.expected_sequence:
            if sequence <= self.last_received_sequence:
                self.duplicate_packets += 1
                if self.total_packets_received % LOG_SEQUENCE_EVERY_N_PACKETS == 0:
                    logger.warning(f"🔁 Duplicate packet: seq={sequence} (expected={self.expected_sequence})")
            else:
                self.out_of_order_packets += 1
                if self.total_packets_received % LOG_SEQUENCE_EVERY_N_PACKETS == 0:
                    logger.warning(f"🔄 Out-of-order packet: seq={sequence} (expected={self.expected_sequence})")
        
        # Check for missing packets (gaps in sequence)
        elif sequence > self.expected_sequence:
            gap_size = sequence - self.expected_sequence
            self.missing_packets += gap_size
            self.sequence_gaps.append({
                'expected': self.expected_sequence,
                'received': sequence,
                'gap_size': gap_size,
                'timestamp': time.time()
            })
            logger.warning(f"🕳️  Sequence gap detected: expected {self.expected_sequence}, got {sequence} (missing {gap_size} packets)")
        
        # Update tracking variables
        if sequence > self.last_received_sequence:
            self.last_received_sequence = sequence
            self.expected_sequence = sequence + 1
        
        # Log sequence info periodically
        if self.total_packets_received % LOG_SEQUENCE_EVERY_N_PACKETS == 0:
            logger.info(f"🔢 Packet #{self.total_packets_received}: seq={sequence}, expected={self.expected_sequence}")

    def encrypt_packet(self, payload: bytes) -> bytes:
        """Encrypts the audio payload using AES-CTR with header as nonce."""
        global udp_session_details
        if "udp" not in udp_session_details: 
            logger.error("UDP session details not available for encryption.")
            return b''
        
        aes_key = bytes.fromhex(udp_session_details["udp"]["key"])
        
        # Extract connectionId from the nonce (which is the header template)
        nonce_bytes = bytes.fromhex(udp_session_details["udp"]["nonce"])
        connection_id = struct.unpack('>I', nonce_bytes[4:8])[0]  # Extract connectionId from nonce
        
        packet_type, flags = 0x01, 0x00
        payload_len, timestamp, sequence = len(payload), int(time.time()), self.udp_local_sequence
        
        # Header format: [type: 1u, flags: 1u, payload_len: 2u, connectionId: 4u, timestamp: 4u, sequence: 4u]
        header = struct.pack('>BBHIII', packet_type, flags, payload_len, connection_id, timestamp, sequence)
        
        cipher = Cipher(algorithms.AES(aes_key), modes.CTR(header), backend=default_backend())
        encryptor = cipher.encryptor()
        encrypted_payload = encryptor.update(payload) + encryptor.finalize()
        self.udp_local_sequence += 1
        return header + encrypted_payload

    def get_ota_config(self) -> bool:
        """Requests OTA configuration from the server."""
        logger.info(f"▶️ STEP 1: Requesting OTA config from http://{SERVER_IP}:{OTA_PORT}/toy/ota/")
        try:
            # Generate a client ID for this session
            import uuid
            session_client_id = str(uuid.uuid4())
            
            headers = {"device-id": self.device_mac_formatted}
            data = {
                "application": {
                    "version": "1.7.6",
                    "name": "DOIT AI Kit v1.7.6"
                },
                "board": {
                    "type": "doit-ai-01-kit"
                },
                "client_id": session_client_id
            }
            response = requests.post(f"http://{SERVER_IP}:{OTA_PORT}/toy/ota/", headers=headers, json=data, timeout=5)
            response.raise_for_status()
            self.ota_config = response.json()
            print(f"OTA Config received: {json.dumps(self.ota_config, indent=2)}")
            
            # Extract websocket URL from the new OTA response format
            websocket_info = self.ota_config.get("websocket", {})
            if websocket_info and "url" in websocket_info:
                self.websocket_url = websocket_info["url"]
                logger.info(f"✅ Got websocket URL from OTA: {self.websocket_url}")
            else:
                logger.warning("⚠️ No websocket URL in OTA response, using fallback")
                self.websocket_url = f"ws://{SERVER_IP}:8000/toy/v1/"
            
            # Extract MQTT credentials from OTA response
            mqtt_info = self.ota_config.get("mqtt", {})
            if mqtt_info:
                self.mqtt_credentials = {
                    "client_id": mqtt_info.get("client_id"),
                    "username": mqtt_info.get("username"),
                    "password": mqtt_info.get("password")
                }
                logger.info(f"✅ Got MQTT credentials from OTA: {self.mqtt_credentials['client_id']}")
            else:
                logger.warning("⚠️ No MQTT credentials in OTA response, generating locally as fallback")
                # Generate MQTT credentials locally as fallback
                self.mqtt_credentials = generate_mqtt_credentials(self.device_mac_formatted)
                logger.info(f"✅ Generated MQTT credentials locally: {self.mqtt_credentials['client_id']}")
            
            logger.info("✅ OTA config received successfully.")

            # --- Handle activation logic (optional, may not be needed) ---
            activation = self.ota_config.get("activation")
            if activation:
                code = activation.get("code")
                if code:
                    print(f"🔐 Activation Required. Code: {code}")
                    activated = False
                    for attempt in range(10):
                        logger.info(f"🕒 Checking activation status... Attempt {attempt + 1}/10")
                        try:
                            status_response = requests.get(f"http://{SERVER_IP}:{OTA_PORT}/ota/active", params={"mac": self.device_mac_formatted}, timeout=3)
                            print(f"Activation status response: {status_response.text}")
                            if status_response.ok and status_response.json().get("activated"):
                                logger.info("✅ Device activated!")
                                activated = True
                                break
                            else:
                                logger.warning("❌ Device not activated yet. Retrying...")

                        except Exception as e:
                            logger.warning(f"Activation check failed: {e}")
                        time.sleep(5)
                    if not activated:
                        logger.error("❌ Activation failed after 10 attempts. Exiting client.")
                        return False
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to get OTA config: {e}")
            return False

    def connect_mqtt(self) -> bool:
        """Connects to the MQTT Broker."""
        # Get MQTT configuration from OTA response
        mqtt_config = self.ota_config.get("mqtt_gateway", {})
        mqtt_broker = mqtt_config.get("broker", MQTT_BROKER_HOST)
        mqtt_port = mqtt_config.get("port", MQTT_BROKER_PORT)
        
        logger.info(f"📍 MQTT Config from OTA: {mqtt_config}")
        logger.info(f"📍 Using MQTT Broker: {mqtt_broker}")
        logger.info(f"📍 Using MQTT Port: {mqtt_port}")
        logger.info(f"📍 MQTT Credentials: client_id={self.mqtt_credentials.get('client_id', 'NOT SET')}")
        logger.info(f"▶️ STEP 2: Connecting to MQTT Gateway at {mqtt_broker}:{mqtt_port}...")
        
        self.mqtt_client = mqtt_client.Client(
            callback_api_version=CallbackAPIVersion.VERSION2, 
            client_id=self.mqtt_credentials["client_id"]
        )
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.username_pw_set(
            self.mqtt_credentials["username"], 
            self.mqtt_credentials["password"]
        )
        
        try:
            logger.info(f"🔄 Attempting connection to MQTT broker...")
            logger.info(f"   Host: {mqtt_broker}")
            logger.info(f"   Port: {mqtt_port}")
            logger.info(f"   Client ID: {self.mqtt_credentials['client_id']}")
            logger.info(f"   Username: {self.mqtt_credentials['username']}")
            
            self.mqtt_client.connect(mqtt_broker, mqtt_port, 60)
            self.mqtt_client.loop_start()
            
            # Wait a moment for connection to establish
            time.sleep(2)
            
            # Check if connected
            if self.mqtt_client.is_connected():
                logger.info("✅ MQTT client is connected!")
            else:
                logger.warning("⚠️ MQTT client connection status unknown, waiting...")
            
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to MQTT Gateway: {e}")
            logger.error(f"   Error type: {type(e).__name__}")
            logger.error(f"   Broker: {mqtt_broker}:{mqtt_port}")
            return False

    def send_hello_and_get_session(self) -> bool:
        """Sends 'hello' message and waits for session details."""
        logger.info("▶️ STEP 3: Sending 'hello' and pinging UDP...")
        # Use the client_id from our generated MQTT credentials
        hello_message = {
            "type": "hello", 
            "version": 3,
            "transport": "mqtt",
            "audio_params": {
                "sample_rate": 16000,
                "channels": 1,
                "frame_duration": 20,
                "format": "opus"
            },
            "features": ["tts", "asr", "vad"]
        }
        self.mqtt_client.publish("device-server", json.dumps(hello_message))
        try:
            response = mqtt_message_queue.get(timeout=10)
            if response.get("type") == "hello" and "udp" in response:
                global udp_session_details
                udp_session_details = response
                self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.udp_socket.settimeout(1.0)
                ping_payload = f"ping:{udp_session_details['session_id']}".encode()
                encrypted_ping = self.encrypt_packet(ping_payload)
                server_udp_addr = (udp_session_details['udp']['server'], udp_session_details['udp']['port'])
                logger.info(f"🔄 Sending UDP Ping to {server_udp_addr} with session ID {udp_session_details['session_id']}"
                             f" and key {udp_session_details['udp']['key']}"
                             f" (local sequence: {self.udp_local_sequence})"
                             )
                if encrypted_ping:
                    self.udp_socket.sendto(encrypted_ping, server_udp_addr)
                    logger.info(f"✅ UDP Ping sent. Session configured.")
                    return True
            logger.error(f"❌ Received unexpected message: {response}")
            return False
        except Empty:
            logger.error("❌ Timed out waiting for 'hello' response.")
            return False

    def _playback_thread(self):
        """Thread to play back incoming audio from the server with a robust jitter buffer."""
        p = pyaudio.PyAudio()
        audio_params = udp_session_details["audio_params"]
        stream = p.open(format=p.get_format_from_width(2),
                        channels=audio_params["channels"],
                        rate=audio_params["sample_rate"],
                        output=True)
        
        logger.info("🔊 Playback thread started.")
        is_playing = False
        buffer_timeout_start = time.time()

        while not stop_threads.is_set() and self.session_active:
            try:
                # --- JITTER BUFFER LOGIC ---
                if not is_playing:
                    # Wait until we have enough frames to start playback smoothly
                    if self.audio_playback_queue.qsize() < PLAYBACK_BUFFER_START_FRAMES:
                        # Check for timeout
                        if time.time() - buffer_timeout_start > BUFFER_TIMEOUT_SECONDS:
                            logger.warning(f"⏰ Buffer timeout after {BUFFER_TIMEOUT_SECONDS}s. Queue size: {self.audio_playback_queue.qsize()}")
                            if self.tts_active:
                                logger.warning("🔊 TTS is active but no audio received. Possible server issue.")
                            buffer_timeout_start = time.time()  # Reset timeout
                        
                        logger.info(f"🎧 Buffering audio... {self.audio_playback_queue.qsize()}/{PLAYBACK_BUFFER_START_FRAMES}")
                        time.sleep(0.05)
                        continue
                    else:
                        logger.info("✅ Buffer ready. Starting playback.")
                        is_playing = True

                # --- If buffer runs low, stop playing and re-buffer ---
                if self.audio_playback_queue.qsize() < PLAYBACK_BUFFER_MIN_FRAMES:
                    is_playing = False
                    buffer_timeout_start = time.time()  # Reset timeout when buffering starts
                    logger.warning(f"‼️ Playback buffer low ({self.audio_playback_queue.qsize()}). Re-buffering...")
                    continue
                
                # Get audio chunk from the queue and play it
                stream.write(self.audio_playback_queue.get(timeout=1))

            except Empty:
                is_playing = False
                buffer_timeout_start = time.time()  # Reset timeout
                continue
            except Exception as e:
                logger.error(f"Playback error: {e}")
                break

        stream.stop_stream()
        stream.close()
        p.terminate()
        logger.info("🔊 Playback thread finished.")

    def listen_for_udp_audio(self):
        """Thread to listen for incoming UDP audio from the server with sequence tracking."""
        logger.info(f"🎧 UDP Listener started on local socket {self.udp_socket.getsockname()}")
        aes_key = bytes.fromhex(udp_session_details["udp"]["key"])
        audio_params = udp_session_details["audio_params"]
        
        # Initialize the decoder with the sample rate provided by the server
        decoder = opuslib.Decoder(audio_params["sample_rate"], audio_params["channels"])
        frame_size_samples = int(audio_params["sample_rate"] * audio_params["frame_duration"] / 1000)
        # Maximum frame size for Opus (120ms at 48kHz = 5760 samples, but we'll use a larger buffer)
        max_frame_size = int(audio_params["sample_rate"] * 0.12)  # 120ms worth of samples
        
        while not stop_threads.is_set() and self.session_active:
            try:
                data, addr = self.udp_socket.recvfrom(4096)
                if data and len(data) > 16:
                    header, encrypted = data[:16], data[16:]
                    
                    # --- Parse header to extract sequence number ---
                    header_info = self.parse_packet_header(header)
                    if header_info and ENABLE_SEQUENCE_LOGGING:
                        sequence = header_info.get('sequence', 0)
                        timestamp = header_info.get('timestamp', 0)
                        payload_len = header_info.get('payload_len', 0)
                        
                        # Track sequence for analysis
                        self.track_sequence(sequence)
                        
                        # Detailed logging for first few packets or periodically
                        if self.total_packets_received <= 5 or self.total_packets_received % (LOG_SEQUENCE_EVERY_N_PACKETS * 2) == 0:
                            logger.info(f"📦 Packet details: seq={sequence}, payload={payload_len}B, ts={timestamp}, from={addr}")
                    
                    # Decrypt and decode as usual
                    cipher = Cipher(algorithms.AES(aes_key), modes.CTR(header), backend=default_backend())
                    decryptor = cipher.decryptor()
                    opus_payload = decryptor.update(encrypted) + decryptor.finalize()
                    
                    # Decode the Opus payload to PCM and put it in the playback queue
                    # Use max_frame_size to provide enough buffer space for variable frame sizes
                    pcm_payload = decoder.decode(opus_payload, max_frame_size)
                    self.audio_playback_queue.put(pcm_payload)
                    
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"UDP Listen Error: {e}", exc_info=True)
        
        logger.info("👋 UDP Listener shutting down.")

    def _record_and_send_audio_thread(self):
        """Thread to record microphone audio and send it to the server."""
        # Main loop to keep the thread alive for multiple recording sessions
        while not stop_threads.is_set() and self.session_active:
            # Wait here until the start event is set (e.g., after TTS stop)
            if not start_recording_event.wait(timeout=1):
                continue
            
            # If the main stop signal was set while waiting, exit the thread
            if stop_threads.is_set():
                break

            logger.info("🔴 Recording thread activated. Capturing audio.")
            p = pyaudio.PyAudio()
            audio_params = udp_session_details["audio_params"]
            FORMAT, CHANNELS, RATE, FRAME_DURATION_MS = pyaudio.paInt16, audio_params["channels"], audio_params["sample_rate"], audio_params["frame_duration"]
            SAMPLES_PER_FRAME = int(RATE * FRAME_DURATION_MS / 1000)
            
            try:
                encoder = opuslib.Encoder(RATE, CHANNELS, opuslib.APPLICATION_VOIP)
            except Exception as e:
                logger.error(f"❌ Failed to create Opus encoder: {e}")
                return # Exit thread if encoder fails
            
            stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=SAMPLES_PER_FRAME)
            logger.info("🎙️ Microphone stream opened. Sending audio to server...")
            server_udp_addr = (udp_session_details['udp']['server'], udp_session_details['udp']['port'])
            
            packets_sent = 0
            last_log_time = time.time()

            # Inner loop for the active recording session
            while not stop_threads.is_set() and not stop_recording_event.is_set() and self.session_active:
                try:
                    pcm_data = stream.read(SAMPLES_PER_FRAME, exception_on_overflow=False)
                    opus_data = encoder.encode(pcm_data, SAMPLES_PER_FRAME)
                    encrypted_packet = self.encrypt_packet(opus_data)
                    
                    if encrypted_packet:
                        self.udp_socket.sendto(encrypted_packet, server_udp_addr)
                        packets_sent += 1
                        
                        if time.time() - last_log_time >= 1.0:
                            logger.info(f"⬆️  Sent {packets_sent} audio packets in the last second.")
                            packets_sent = 0
                            last_log_time = time.time()
                            
                except Exception as e:
                    logger.error(f"An error occurred in the recording loop: {e}")
                    break # Exit inner loop on error
            
            # Cleanup for the current recording session
            logger.info("🎙️ Stopping microphone stream for this session.")
            stream.stop_stream()
            stream.close()
            p.terminate()

            # Clear the start event so it has to be triggered again for the next session
            start_recording_event.clear()
            
            if stop_recording_event.is_set():
                logger.info("🛑 Recording stopped by server signal. Waiting for next turn.")
            
        logger.info("🔴 Recording thread finished completely.")

    def trigger_conversation(self):
        """Starts the audio streaming threads and sends initial listen message."""
        if not self.udp_socket: return False
        logger.info("▶️ STEP 4: Starting all streaming audio threads...")
        global stop_threads, start_recording_event, stop_recording_event
        stop_threads.clear()
        # Initially, clear both events. The server's initial TTS will set start_recording_event.
        start_recording_event.clear() 
        stop_recording_event.clear() 

        self.playback_thread = threading.Thread(target=self._playback_thread, daemon=True)
        self.udp_listener_thread = threading.Thread(target=self.listen_for_udp_audio, daemon=True)
        self.audio_recording_thread = threading.Thread(target=self._record_and_send_audio_thread, daemon=True)
        self.playback_thread.start(), self.udp_listener_thread.start(), self.audio_recording_thread.start()

        logger.info("▶️ STEP 5: Sending 'listen' message to trigger initial TTS from server...")
        # The server's initial TTS will then trigger the client's recording.
        listen_payload = {"type": "listen", "session_id": udp_session_details["session_id"], "state": "detect", "text": "hello baby"}
        self.mqtt_client.publish("device-server", json.dumps(listen_payload))
        logger.info("⏳ Test running. Press Spacebar to abort TTS or Ctrl+C to stop.")

        # Start a thread to monitor spacebar press
        def monitor_spacebar():
            while not stop_threads.is_set() and self.session_active:
                if keyboard.is_pressed('space'):
                    logger.info("🚫 Spacebar pressed. Sending abort message to server...")
                    abort_payload = {
                        "type": "abort",
                        "session_id": udp_session_details["session_id"]
                    }
                    self.mqtt_client.publish("device-server", json.dumps(abort_payload))
                    logger.info(f"📤 Sent abort message: {abort_payload}")
                    # Wait for the key to be released to avoid multiple sends
                    while keyboard.is_pressed('space') and not stop_threads.is_set():
                        time.sleep(0.01)
                time.sleep(0.01)

        spacebar_thread = threading.Thread(target=monitor_spacebar, daemon=True)
        spacebar_thread.start()

        try:
            # Keep running with better timeout handling
            timeout_count = 0
            while not stop_threads.is_set() and self.session_active:
                time.sleep(1)
                
                # Check if we've been inactive for too long
                if self.tts_active and time.time() - self.last_audio_received > TTS_TIMEOUT_SECONDS:
                    logger.warning(f"⏰ No audio received for {TTS_TIMEOUT_SECONDS}s during TTS. Possible server issue.")
                    timeout_count += 1
                    if timeout_count >= 3:
                        logger.error("❌ Too many timeouts. Stopping session.")
                        self.session_active = False
                        break
                    else:
                        logger.info("🔄 Attempting to recover by sending new listen message...")
                        self.retry_conversation()
                        
        except KeyboardInterrupt:
            logger.info("Manual interruption detected. Cleaning up...")
            stop_threads.set()
            self.session_active = False
        return True

    def cleanup(self):
        """Cleans up resources and disconnects."""
        logger.info("▶️ STEP 6: Cleaning up and disconnecting...")
        global stop_threads, start_recording_event, stop_recording_event
        stop_threads.set()
        self.session_active = False
        start_recording_event.set() # Unblock if waiting
        stop_recording_event.set()  # Unblock if running
        
        # Print final sequence summary
        if ENABLE_SEQUENCE_LOGGING and self.total_packets_received > 0:
            logger.info("📊 FINAL SEQUENCE SUMMARY")
            self.print_sequence_summary()
        
        if self.audio_recording_thread:
            logger.info("Attempting to join audio_recording_thread...")
            self.audio_recording_thread.join(timeout=2)
            if self.audio_recording_thread.is_alive():
                logger.warning("Audio recording thread did not terminate gracefully.")
        
        if self.playback_thread: self.playback_thread.join(timeout=2)
        if self.udp_listener_thread: self.udp_listener_thread.join(timeout=2)
        if self.udp_socket: self.udp_socket.close()
        
        if self.mqtt_client and udp_session_details:
            goodbye_payload = { "type": "goodbye", "session_id": udp_session_details.get("session_id") }
            self.mqtt_client.publish("device-server", json.dumps(goodbye_payload))
            logger.info("👋 Sent 'goodbye' message.")
        
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            logger.info("🔌 MQTT Disconnected.")
        logger.info("✅ Test finished.")

    def run_test(self):
        """Runs the full test sequence."""
        if ENABLE_SEQUENCE_LOGGING:
            logger.info("🔢 Sequence tracking is ENABLED")
            logger.info(f"📊 Will log sequence info every {LOG_SEQUENCE_EVERY_N_PACKETS} packets")
        else:
            logger.info("🔢 Sequence tracking is DISABLED")
            
        if not self.get_ota_config(): return
        if not self.connect_mqtt(): return
        time.sleep(1) # Give MQTT a moment to connect and subscribe
        if not self.send_hello_and_get_session():
            self.cleanup()
            return
        self.trigger_conversation()
        self.cleanup()

if __name__ == "__main__":
    # You can control sequence logging from here
    print(f"🔢 Sequence logging: {'ENABLED' if ENABLE_SEQUENCE_LOGGING else 'DISABLED'}")
    print(f"📊 Log frequency: Every {LOG_SEQUENCE_EVERY_N_PACKETS} packets")
    
    client = TestClient()
    try:
        client.run_test()
    except KeyboardInterrupt:
        logger.info("Manual interruption detected. Cleaning up...")
        client.cleanup()