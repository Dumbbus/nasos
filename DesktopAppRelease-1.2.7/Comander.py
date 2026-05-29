import tkinter as tk
from tkinter import ttk
import paho.mqtt.client as mqtt
import time

# ---------- MQTT CONFIGURATION ----------
MQTT_BROKER = "192.168.1.100"   # ← IP address of PC B (Mosquitto broker)
MQTT_PORT = 1883
COMMAND_TOPIC = "motor/command"
SENSOR_TOPIC = "sensor/data"
# ----------------------------------------

class MotorController:
    def __init__(self, root):
        self.root = root
        self.root.title("L298N Motor Control (MQTT)")
        self.root.geometry("380x560")
        self.root.resizable(False, False)

        # MQTT client – use new API version 2 to avoid deprecation
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_mqtt_connect
        self.client.on_message = self.on_mqtt_message
        self.client.connect_async(MQTT_BROKER, MQTT_PORT, 60)
        self.client.loop_start()

        # Status and sensor labels
        self.status_var = tk.StringVar(value="Connecting to MQTT...")
        self.temp_var = tk.StringVar(value="Temperature: -- C")
        self.pressure_var = tk.StringVar(value="Pressure: -- mbar")

        # ---- PWM Speed Control ----
        pwm_frame = ttk.LabelFrame(root, text="Speed (PWM)", padding=10)
        pwm_frame.pack(fill="x", padx=10, pady=5)
        self.speed_var = tk.IntVar(value=0)
        self.speed_label = ttk.Label(pwm_frame, text="0", font=("Arial", 16))
        self.speed_label.pack()
        self.slider = ttk.Scale(
            pwm_frame, from_=0, to=255, orient="horizontal",
            variable=self.speed_var, command=self.on_slider_change
        )
        self.slider.pack(fill="x", pady=5)

        # ---- Direction Buttons ----
        btn_frame = ttk.LabelFrame(root, text="Direction", padding=10)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(btn_frame, text="Forward", command=self.forward).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(btn_frame, text="Backward", command=self.backward).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(btn_frame, text="Stop (Coast)", command=self.stop).grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(btn_frame, text="Brake", command=self.brake).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        # ---- Burst Mode ----
        burst_frame = ttk.LabelFrame(root, text="Low‑Speed Burst Mode", padding=10)
        burst_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(burst_frame, text="ON (ms):").grid(row=0, column=0, padx=5)
        self.on_entry = ttk.Entry(burst_frame, width=6)
        self.on_entry.grid(row=0, column=1, padx=5)
        self.on_entry.insert(0, "50")
        ttk.Label(burst_frame, text="OFF (ms):").grid(row=0, column=2, padx=5)
        self.off_entry = ttk.Entry(burst_frame, width=6)
        self.off_entry.grid(row=0, column=3, padx=5)
        self.off_entry.insert(0, "300")
        ttk.Button(burst_frame, text="Start Burst", command=self.start_burst).grid(row=0, column=4, padx=5)
        ttk.Button(burst_frame, text="Stop", command=self.stop).grid(row=0, column=5, padx=5)

        # ---- Sensor Data Display ----
        sensor_frame = ttk.LabelFrame(root, text="BMP180 Sensor Data (from remote)", padding=10)
        sensor_frame.pack(fill="x", padx=10, pady=10)
        ttk.Label(sensor_frame, textvariable=self.temp_var, font=("Arial", 12)).pack(anchor="w")
        ttk.Label(sensor_frame, textvariable=self.pressure_var, font=("Arial", 12)).pack(anchor="w")

        # ---- Status Bar ----
        status_bar = ttk.Label(root, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.pack(side="bottom", fill="x")

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ---------- MQTT Callbacks (new API) ----------
    def on_mqtt_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self.status_var.set("Connected to MQTT broker")
            client.subscribe(SENSOR_TOPIC)
        else:
            self.status_var.set(f"MQTT connection failed (code {reason_code})")

    def on_mqtt_message(self, client, userdata, msg):
        # Expected format: "TEMP:23.45:PRESSURE:101325"
        if msg.topic == SENSOR_TOPIC:
            payload = msg.payload.decode().strip()
            try:
                parts = payload.split(":")
                if parts[0] == "TEMP" and len(parts) == 4:
                    self.temp_var.set(f"Temperature: {parts[1]} C")
                    self.pressure_var.set(f"Pressure: {parts[3]} mbar")
            except:
                pass  # ignore malformed messages

    # ---------- Publish Motor Commands ----------
    def publish(self, cmd):
        self.client.publish(COMMAND_TOPIC, cmd)

    def on_slider_change(self, event=None):
        speed = self.speed_var.get()
        self.speed_label.config(text=str(speed))
        if self.current_direction in ('F', 'B'):
            self.publish(f"{self.current_direction} {speed}")

    def forward(self):
        self.current_direction = 'F'
        self.publish(f"F {self.speed_var.get()}")

    def backward(self):
        self.current_direction = 'B'
        self.publish(f"B {self.speed_var.get()}")

    def stop(self):
        self.current_direction = 'S'
        self.publish("S")

    def brake(self):
        self.current_direction = 'K'
        self.publish("K")

    def start_burst(self):
        on_ms = self.on_entry.get()
        off_ms = self.off_entry.get()
        if self.current_direction not in ('F', 'B'):
            self.current_direction = 'F'
            self.publish('F')  # set direction first
        self.publish(f"L {on_ms} {off_ms}")

    def on_closing(self):
        self.publish("S")  # stop motor before exit
        self.client.loop_stop()
        self.client.disconnect()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MotorController(root)
    root.mainloop()