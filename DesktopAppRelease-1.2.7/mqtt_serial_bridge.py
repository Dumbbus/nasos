import serial
import time
import paho.mqtt.client as mqtt

# ---------- CONFIGURATION ----------
SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 9600
MQTT_BROKER = 'localhost'
MQTT_PORT = 1883
COMMAND_TOPIC = 'motor/command'
SENSOR_TOPIC = 'sensor/data'
# -----------------------------------

# Connect to Arduino
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    time.sleep(2)
    print(f"Connected to Arduino on {SERIAL_PORT}")
except serial.SerialException as e:
    print(f"Error opening serial port: {e}")
    exit(1)

# MQTT callbacks (new API)
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Connected to MQTT broker")
        client.subscribe(COMMAND_TOPIC)
    else:
        print(f"Connection failed with reason code {reason_code}")

def on_message(client, userdata, msg):
    cmd = msg.payload.decode().strip()
    if cmd:
        ser.write((cmd + '\n').encode())
        print(f"Forwarded to Arduino: {cmd}")

# Setup MQTT client with API version 2
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

# Main loop: read from Arduino and publish sensor data
try:
    while True:
        if ser.in_waiting:
            line = ser.readline().decode().strip()
            if line:
                print(f"Arduino: {line}")
                if line.startswith("DATA:"):
                    parts = line.split(":")
                    if len(parts) == 5 and parts[1] == "TEMP" and parts[3] == "PRESSURE":
                        temp = parts[2]
                        pressure = parts[4]
                        client.publish(SENSOR_TOPIC, f"TEMP:{temp}:PRESSURE:{pressure}")
                        print(f"Published sensor: TEMP={temp}, PRESSURE={pressure}")
        time.sleep(0.01)
except KeyboardInterrupt:
    print("Shutting down...")
    ser.close()
    client.loop_stop()
    client.disconnect()