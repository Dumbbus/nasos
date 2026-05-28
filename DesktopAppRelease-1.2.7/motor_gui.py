import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports
import threading
import time

# ---------- CONFIGURATION ---------
SERIAL_PORT = '/dev/ttyACM0'      # Change to your port (e.g., '/dev/ttyUSB0' on Linux)
BAUD_RATE = 9600
# -----------------------------------

class MotorController:
    def __init__(self, root):
        self.root = root
        self.root.title("L298N Motor Control")
        self.root.geometry("380x520")  # slightly taller to fit burst controls
        self.root.resizable(False, False)

        self.ser = None
        self.status_var = tk.StringVar(value="Not connected")
        self.connect_serial()

        self.current_direction = None

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
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        # ---- Burst Mode (Low‑Speed) ----
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

        # ---- Status Bar ----
        status_bar = ttk.Label(root, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.pack(side="bottom", fill="x")

        # ---- Sensor Data Display ----
        sensor_frame = ttk.LabelFrame(root, text="BMP180 Sensor Data", padding=10)
        sensor_frame.pack(fill="x", padx=10, pady=10)
        self.temp_label = ttk.Label(sensor_frame, text="Temperature: -- C", font=("Arial", 12))
        self.temp_label.pack(anchor="w")
        self.pressure_label = ttk.Label(sensor_frame, text="Pressure: -- mbar", font=("Arial", 12))
        self.pressure_label.pack(anchor="w")

        # Cleanup on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Background serial reader
        self.running = True
        self.thread = threading.Thread(target=self.read_from_arduino, daemon=True)
        self.thread.start()
    def start_burst(self):
        on_ms = self.on_entry.get()
        off_ms = self.off_entry.get()
        self.send_command(f"L {on_ms} {off_ms}")
    def set_speed(self):
        rpm = self.rpm_var.get()
        self.send_command(f"V {rpm}")
    def connect_serial(self):
        try:
            self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
            time.sleep(2)  # wait for Arduino reset
            self.status_var.set(f"Connected to {SERIAL_PORT}")
        except serial.SerialException:
            self.status_var.set(f"Error: Could not open {SERIAL_PORT}")
            self.ser = None

    def send_command(self, cmd):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write((cmd + '\n').encode())
            except serial.SerialException:
                self.status_var.set("Serial write error")

    def on_slider_change(self, event=None):
        speed = self.speed_var.get()
        self.speed_label.config(text=str(speed))
        # If currently moving, update speed automatically
        if self.current_direction in ('F', 'B'):
            self.send_command(f"{self.current_direction} {speed}")

    def forward(self):
        self.current_direction = 'F'
        self.send_command(f"F {self.speed_var.get()}")

    def backward(self):
        self.current_direction = 'B'
        self.send_command(f"B {self.speed_var.get()}")

    def stop(self):
        self.current_direction = 'S'
        self.send_command("S")

    def read_from_arduino(self):
        """Continuously read responses from Arduino and update status."""
        while self.running:
            if self.ser and self.ser.is_open:
                try:
                    if self.ser.in_waiting:
                        line = self.ser.readline().decode().strip()
                        if line:
                            # Parse different message types from Arduino
                            if line.startswith("MOTOR:"):
                                # Update status with motor state (optional)
                                # self.status_var.set(line) # You can choose to show this or not
                                pass  # We know the motor command was executed
                            elif line.startswith("DATA:"):
                                # Parse and display sensor data
                                # Format: DATA:TEMP:xx.xx:PRESSURE:yyy.yy
                                parts = line.split(":")
                                if len(parts) == 5:
                                    self.temp_label.config(text=f"Temperature: {parts[2]} C")
                                    self.pressure_label.config(text=f"Pressure: {parts[4]} mbar")
                            elif line.startswith("SENSOR:"):
                                sensor_status = line.split(":")[1]
                                if sensor_status == "BMP180_READY":
                                    self.status_var.set("Sensor ready.")
                                else:
                                    self.status_var.set("Sensor ERROR!")
                            else:
                                # Any other message (like old status messages)
                                self.status_var.set(line)
                except (serial.SerialException, OSError):
                    self.status_var.set("Serial read error")
            time.sleep(0.05)

    def on_closing(self):
        # Stop motor and close serial
        self.running = False
        self.send_command("S")
        time.sleep(0.1)
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MotorController(root)
    root.mainloop()