import subprocess
import threading
import tkinter as tk
from tkinter import messagebox
import time
import os

# -------------------------------
# Config: use ADBB instead of ADB
# -------------------------------
ADB_BIN = "adbb"   # 👈 your internal tool

# -------------------------------
# Global state
# -------------------------------
recording = False
record_thread = None
root = None
status_label = None

# -------------------------------
# Helpers
# -------------------------------

def set_status(text: str):
    """Update status label safely from any thread."""
    if root and status_label:
        root.after(0, lambda: status_label.config(text=text))
    print(text)


def adb_cmd(args_list):
    """
    Run an adbb command.
    args_list: list like ["shell", "screencap", "-p", "/sdcard/tmp.png"]
    Returns (stdout, stderr).
    """
    try:
        result = subprocess.run(
            [ADB_BIN] + args_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return "", str(e)


def check_device_connected() -> bool:
    out, err = adb_cmd(["devices"])
    if err:
        messagebox.showerror("ADBB Error", f"{ADB_BIN} devices failed:\n{err}")
        return False
    # Parse connected devices
    lines = out.splitlines()
    devices = [ln for ln in lines[1:] if ln.strip() and "device" in ln]
    if not devices:
        messagebox.showwarning(
            "No Device",
            f"No {ADB_BIN} device detected.\n\nCheck USB/debugging and try again."
        )
        return False
    return True

# -------------------------------
# Screen Recording
# -------------------------------

def start_recording():
    global recording, record_thread

    if recording:
        messagebox.showinfo("Info", "Recording is already in progress.")
        return

    if not check_device_connected():
        return

    recording = True
    record_thread = threading.Thread(target=_record_worker, daemon=True)
    record_thread.start()
    set_status("Recording: ON")


def _record_worker():
    global recording

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_filename = f"record_{timestamp}.mp4"
    device_tmp = "/sdcard/tre_record_tmp.mp4"

    # Start recording on device (max duration depends on platform)
    set_status(f"Starting {ADB_BIN} screenrecord...")
    try:
        proc = subprocess.Popen(
            [ADB_BIN, "shell", "screenrecord", device_tmp],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        recording = False
        set_status(f"Failed to start screenrecord: {e}")
        return

    # Wait until recording flag is turned off
    while recording:
        time.sleep(0.2)

    # Stop screenrecord
    set_status("Stopping recording, please wait...")
    try:
        proc.terminate()
    except Exception:
        pass
    time.sleep(1.0)

    # Pull the file from device
    set_status("Pulling video from device...")
    stdout, stderr = adb_cmd(["pull", device_tmp, out_filename])
    if stderr:
        set_status(f"Pull error: {stderr}")
    else:
        set_status(f"Saved recording: {out_filename}")

    # Clean up temp on device
    adb_cmd(["shell", "rm", device_tmp])


def stop_recording():
    global recording
    if not recording:
        messagebox.showinfo("Info", "No recording is currently running.")
        return
    recording = False
    set_status("Recording: Stopping...")

# -------------------------------
# Screenshot
# -------------------------------

def take_screenshot():
    if not check_device_connected():
        return

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_filename = f"screenshot_{timestamp}.png"
    device_tmp = "/sdcard/tre_screenshot_tmp.png"

    set_status("Capturing screenshot on device...")
    stdout, stderr = adb_cmd(["shell", "screencap", "-p", device_tmp])
    if stderr:
        messagebox.showerror("ADBB Error", f"screencap failed:\n{stderr}")
        return

    set_status("Pulling screenshot from device...")
    stdout, stderr = adb_cmd(["pull", device_tmp, out_filename])
    if stderr:
        messagebox.showerror("ADBB Error", f"pull failed:\n{stderr}")
        return

    adb_cmd(["shell", "rm", device_tmp])
    set_status(f"Saved screenshot: {out_filename}")

# -------------------------------
# Tkinter UI Setup
# -------------------------------

def main():
    global root, status_label

    # Ensure we save in script folder
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    root = tk.Tk()
    root.title("ADBB Screen Tool")
    root.geometry("320x210")
    root.resizable(False, False)

    # Title
    title = tk.Label(root, text="ADBB Screen Tool", font=("Segoe UI", 14, "bold"))
    title.pack(pady=8)

    # Buttons
    btn_start = tk.Button(
        root, text="▶ Start Recording",
        width=22, command=start_recording,
        bg="#4CAF50", fg="white", relief="raised"
    )
    btn_start.pack(pady=4)

    btn_stop = tk.Button(
        root, text="⏹ Stop Recording",
        width=22, command=stop_recording,
        bg="#f44336", fg="white", relief="raised"
    )
    btn_stop.pack(pady=4)

    btn_ss = tk.Button(
        root, text="📸 Take Screenshot",
        width=22, command=take_screenshot,
        relief="raised"
    )
    btn_ss.pack(pady=4)

    # Status label
    status_label = tk.Label(root, text="Ready.", fg="#555")
    status_label.pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    main()