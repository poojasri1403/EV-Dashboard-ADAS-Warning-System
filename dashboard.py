"""
Vehicle Safety Dashboard - reads data from the ESP32 over USB serial.

Install once:   pip install pyserial
Run:            python dashboard.py            (auto-detects the port)
or:             python dashboard.py COM5       (if auto-detect fails)
Close the Arduino Serial Monitor before running this!
"""
import sys
import threading
import tkinter as tk
from tkinter import ttk

import serial
import serial.tools.list_ports

BAUD = 115200
GREEN, YELLOW, RED, GREY = "#2ecc71", "#f1c40f", "#e74c3c", "#7f8c8d"
LEVEL_COLOR = {0: GREEN, 1: YELLOW, 2: RED}

data = {"D": 0.0, "V": 0, "T": 0.0, "O": 0, "P": 0, "H": 0, "S": 0}
connected = False


def find_port():
    if len(sys.argv) > 1:
        return sys.argv[1]
    for p in serial.tools.list_ports.comports():
        name = (p.description or "").upper()
        if any(k in name for k in ("CP210", "CH340", "USB SERIAL", "USB-SERIAL")):
            return p.device
    ports = list(serial.tools.list_ports.comports())
    return ports[0].device if ports else None


def reader():
    global connected
    port = find_port()
    if not port:
        print("No serial port found. Plug in the ESP32.")
        return
    print("Using port:", port)
    try:
        ser = serial.Serial(port, BAUD, timeout=1)
    except Exception as e:
        print("Cannot open port:", e)
        return
    connected = True
    while True:
        try:
            line = ser.readline().decode(errors="ignore").strip()
            if not line:
                continue
            parsed = {}
            for part in line.split(","):
                k, v = part.split(":")
                parsed[k] = float(v)
            if all(k in parsed for k in data):
                data.update(parsed)
        except Exception:
            pass  # ignore half-received lines


root = tk.Tk()
root.title("Vehicle Safety Dashboard")
root.geometry("820x520")
root.configure(bg="#1e1e2e")

banner = tk.Label(root, text="WAITING FOR DATA...", font=("Arial", 26, "bold"),
                  bg=GREY, fg="white", pady=18)
banner.pack(fill="x", padx=15, pady=15)

frame = tk.Frame(root, bg="#1e1e2e")
frame.pack(fill="both", expand=True, padx=15)


def make_card(col, title):
    card = tk.Frame(frame, bg="#2b2b3d", padx=10, pady=10)
    card.grid(row=0, column=col, padx=8, sticky="nsew")
    frame.columnconfigure(col, weight=1)
    tk.Label(card, text=title, font=("Arial", 14), bg="#2b2b3d", fg="white").pack()
    value = tk.Label(card, text="--", font=("Arial", 32, "bold"), bg="#2b2b3d", fg="white")
    value.pack(pady=10)
    status = tk.Label(card, text="--", font=("Arial", 14, "bold"), bg=GREY, fg="white", width=14)
    status.pack(pady=5)
    return value, status


dist_val, dist_st = make_card(0, "Obstacle Distance")
spd_val, spd_st = make_card(1, "Speed")
tmp_val, tmp_st = make_card(2, "Temperature")

bar = ttk.Progressbar(root, length=700, maximum=120)
bar.pack(pady=20)
tk.Label(root, text="Speed (km/h)", bg="#1e1e2e", fg="white").pack()


def update():
    d = data
    if connected:
        # distance
        dist_val.config(text="Clear" if d["D"] >= 400 else f'{d["D"]:.0f} cm')
        dist_st.config(text=["SAFE", "OBSTACLE NEAR", "DANGER!"][int(d["O"])],
                       bg=LEVEL_COLOR[int(d["O"])])
        # speed
        spd_val.config(text=f'{int(d["V"])} km/h')
        spd_st.config(text="HIGH SPEED" if d["P"] else "NORMAL",
                      bg=YELLOW if d["P"] else GREEN)
        bar["value"] = d["V"]
        # temperature
        tmp_val.config(text=f'{d["T"]:.1f} °C')
        tmp_st.config(text=["NORMAL", "HIGH TEMP", "OVERHEAT!"][int(d["H"])],
                      bg=LEVEL_COLOR[int(d["H"])])
        # banner
        issues = []
        if d["O"] >= 1:
            issues.append("Obstacle")
        if d["P"]:
            issues.append("High speed")
        if d["H"] >= 1:
            issues.append("High temp")
        level = int(d["S"])
        banner.config(text="ALL SAFE" if level == 0 else
                      ("WARNING: " if level == 1 else "DANGER: ") + ", ".join(issues),
                      bg=LEVEL_COLOR[level])
    root.after(200, update)


threading.Thread(target=reader, daemon=True).start()
update()
root.mainloop()
