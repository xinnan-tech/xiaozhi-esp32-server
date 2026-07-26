# Native MQTT/UDP integration

The server can accept device MQTT control messages and encrypted UDP audio
without running `xiaozhi-mqtt-gateway`. Native MQTT is optional. The existing
Gateway path and direct WebSocket path remain supported.

## Compatibility modes

| Mode | Device control | Device audio | Server business runtime |
| --- | --- | --- | --- |
| Direct WebSocket | WebSocket JSON | WebSocket binary | Shared runtime |
| MQTT Gateway | MQTT via Gateway WebSocket | UDP via Gateway WebSocket | Shared runtime |
| Native MQTT | MQTT 3.1.1 QoS 0 | AES-128-CTR UDP | Shared runtime |

Native MQTT keeps the physical MQTT connection alive between conversations.
Each device `hello` creates a new logical conversation and UDP encryption
session. `goodbye` ends only that logical conversation; MQTT is closed only by
MQTT disconnect, duplicate client takeover, keepAlive expiry, server shutdown,
or a protocol/authentication error.

## Enable Native MQTT

Native MQTT is disabled by default. Both the protocol and server switches must
be enabled:

```yaml
protocols:
  enabled_protocols: [websocket, mqtt]
  websocket_enabled: true
  mqtt_enabled: true

mqtt_server:
  enabled: true
  host: 0.0.0.0
  port: 1883
  udp_port: 1883
  udp_bind_host: ""
  public_endpoint: mqtt.example.com
  signature_key: replace-with-a-strong-secret
  max_connections: 1000
  max_pending_connections: 128
  heartbeat_interval: 30
  max_payload_size: 8192
  message_queue_size: 128
  business_ready_timeout: 30
  goodbye_timeout: 1
  close_timeout: 2

# Includes the common model and any Agent-specific local ASR variants.
shared_asr_max_models: 3
```

`host` is the local MQTT listen address. `public_endpoint` must be reachable by
the device and may be either `host` or `host:port`; manager-api normalizes it
and does not append the port twice. When `host` is a wildcard and
`public_endpoint` is a local IPv4 address, the UDP socket binds that address so
reply datagrams use the same source IP advertised to the device. Set
`udp_bind_host` only when the local UDP bind address must differ from the
advertised endpoint (for example, behind NAT); leaving it empty enables the
automatic behavior. Open the configured MQTT TCP and UDP ports in the firewall.

When configuration is read from manager-api, configure the equivalent
`protocols.*` and `mqtt_server.*` system parameters. The OTA response prefers a
valid Native endpoint when Native is enabled. If Native is disabled or invalid,
manager-api falls back to `server.mqtt_gateway`. If neither is configured, OTA
returns only WebSocket information.

The current firmware persists the OTA `mqtt` object. The UDP server, key and
nonce used by Native mode are negotiated in the MQTT `hello` response, so
manager-api does not send a separate top-level OTA `udp` object.

Long-lived Native connections refresh Agent-private components at logical
`hello` boundaries. Local ASR variants are shared by effective configuration
instead of loaded once per device. `shared_asr_max_models` bounds resident
models; when capacity is exhausted, the replacement runtime is rejected and
the previous healthy runtime remains active.
The default capacity reserves one transition slot so a single Agent can replace
an active private local model without dropping its healthy runtime first. Idle
variants are cached and evicted before another model is loaded; resident models
never exceed this limit.

MQTT application packets are dispatched in order outside the socket read loop,
so PINGREQ remains responsive while a logical Hello waits for private runtime
refresh. `business_ready_timeout` bounds that wait and closes an unusable
connection instead of leaving the device in a half-negotiated session.
`max_connections` limits authenticated client identities, while
`max_pending_connections` separately bounds sockets that have not completed
CONNECT. A connection using an existing client id may therefore replace its
previous owner even when active capacity is full. The server sends the success
CONNACK only after the previous owner has been reclaimed. `goodbye_timeout` and
`close_timeout` bound best-effort device reset and physical resource cleanup so
a stalled peer cannot block heartbeat or shutdown indefinitely.

## Authentication and topics

manager-api generates the device credentials and topics:

- client id: `<group>@@@<mac_with_underscores>@@@<mac_with_underscores>`
- publish topic: `device-server`
- subscribe topic: `devices/p2p/<mac_with_underscores>`
- username: Base64-encoded JSON metadata
- password: Base64(HMAC-SHA256(`client_id + "|" + username`, signature key))

Use the same secret for manager-api `mqtt_server.signature_key` and
xiaozhi-server `mqtt_server.signature_key`. The legacy
`server.mqtt_signature_key` remains a fallback for Gateway compatibility.

Native MQTT accepts MQTT 3.1.1 CONNECT, SUBSCRIBE, PUBLISH QoS 0, PING and
DISCONNECT. Unsupported protocol versions, QoS levels, malformed packets, or
invalid credentials close the physical connection.

## Session and UDP flow

1. Device connects and subscribes over MQTT.
2. Server validates CONNECT credentials and replaces any older connection with
   the same client id.
3. Device publishes protocol version 3 `hello`.
4. Server waits until private configuration and business components are ready.
5. Server creates a logical session and returns the UDP server, AES key, nonce,
   output audio parameters and session id.
6. The first valid UDP packet from the MQTT peer binds the UDP source tuple for
   that logical session. Source changes are rejected until the next `hello`.
7. MQTT JSON and decrypted Opus frames enter the same message processors used
   by WebSocket and Gateway connections.
8. Server `goodbye` returns the device to Idle and finalizes conversation tasks
   while preserving the MQTT connection.

The 16-byte UDP header is also the AES-CTR nonce:

| Bytes | Field |
| --- | --- |
| 0 | packet type (`1`) |
| 1 | reserved |
| 2..3 | encrypted payload length, big endian |
| 4..7 | connection id, big endian |
| 8..11 | timestamp, big endian |
| 12..15 | sequence, big endian |

Datagrams with an invalid type, header, payload length, connection id, source
address or stale sequence are discarded. Sequence gaps are tolerated because
UDP can lose packets; late and duplicate packets are discarded. AES-CTR
provides confidentiality but not integrity, so Native MQTT and UDP should be
exposed only with a strong signature key and appropriate network controls.

## Verification

From `main/xiaozhi-server`:

```bash
python -m compileall -q .
```

From `main/manager-api` with JDK 21:

```bash
mvn clean package
```

Before deployment, verify Native and Gateway separately with real hardware:
multiple conversations, TTS interruption, exit to Idle, duplicate reconnect,
server restart, short network loss and a 30-60 minute keepAlive soak.
