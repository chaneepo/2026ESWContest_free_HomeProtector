import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import threading
import time

class MotorUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ESP32 스텝모터 제어")
        self.root.geometry("540x580")
        self.ser = None

        main = ttk.Frame(root, padding=16)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="ESP32 스텝모터 제어", font=("맑은 고딕", 16, "bold")).pack(pady=(0, 12))

        conn = ttk.LabelFrame(main, text="연결", padding=10)
        conn.pack(fill="x", pady=6)

        row = ttk.Frame(conn)
        row.pack(fill="x")
        ttk.Label(row, text="COM 포트").pack(side="left")

        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(row, textvariable=self.port_var, width=15, state="readonly")
        self.port_combo.pack(side="left", padx=8)

        ttk.Button(row, text="새로고침", command=self.refresh_ports).pack(side="left")
        self.connect_btn = ttk.Button(row, text="연결", command=self.toggle_connection)
        self.connect_btn.pack(side="right")

        move = ttk.LabelFrame(main, text="메인 이동", padding=10)
        move.pack(fill="x", pady=6)

        self.angle_var = tk.DoubleVar(value=90.0)
        self.speed_var = tk.IntVar(value=2)

        ttk.Label(move, text="이동 각도 (D 방향)").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Spinbox(move, from_=1, to=360, increment=1, textvariable=self.angle_var, width=10).grid(row=0, column=1, sticky="w")

        ttk.Label(move, text="속도 (1=매우 느림)").grid(row=1, column=0, sticky="w", pady=5)
        speed_scale = ttk.Scale(
            move, from_=1, to=20, orient="horizontal",
            command=lambda v: self.speed_var.set(max(1, round(float(v))))
        )
        speed_scale.set(2)
        speed_scale.grid(row=1, column=1, sticky="ew", padx=(0, 8))
        ttk.Label(move, textvariable=self.speed_var, width=3).grid(row=1, column=2)

        move.columnconfigure(1, weight=1)

        shake = ttk.LabelFrame(main, text="끝점 털기", padding=10)
        shake.pack(fill="x", pady=6)

        self.shake_angle_var = tk.DoubleVar(value=10.0)
        self.shake_count_var = tk.IntVar(value=5)
        self.shake_speed_var = tk.IntVar(value=20)
        self.shake_interval_var = tk.IntVar(value=300)

        ttk.Label(shake, text="털기 각도").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Spinbox(shake, from_=1, to=45, increment=1,
                    textvariable=self.shake_angle_var, width=10).grid(row=0, column=1, sticky="w")

        ttk.Label(shake, text="반복 횟수").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Spinbox(shake, from_=1, to=20, increment=1,
                    textvariable=self.shake_count_var, width=10).grid(row=1, column=1, sticky="w")

        ttk.Label(shake, text="털기 속도").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Spinbox(shake, from_=1, to=127, increment=1,
                    textvariable=self.shake_speed_var, width=10).grid(row=2, column=1, sticky="w")

        ttk.Label(shake, text="털기 간격 (ms)").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Spinbox(shake, from_=0, to=3000, increment=50,
                    textvariable=self.shake_interval_var, width=10).grid(row=3, column=1, sticky="w")
        ttk.Label(shake, text="예: 100=0.1초, 500=0.5초").grid(row=3, column=2, sticky="w", padx=(8,0))

        buttons = ttk.Frame(main)
        buttons.pack(fill="x", pady=12)

        ttk.Button(buttons, text="▶ 전체 실행", command=self.run_sequence).pack(side="left", expand=True, fill="x", padx=3)
        ttk.Button(buttons, text="◀ A 10°", command=lambda: self.jog("A")).pack(side="left", expand=True, fill="x", padx=3)
        ttk.Button(buttons, text="D 10° ▶", command=lambda: self.jog("D")).pack(side="left", expand=True, fill="x", padx=3)

        status_frame = ttk.LabelFrame(main, text="상태", padding=10)
        status_frame.pack(fill="both", expand=True, pady=6)

        self.status = tk.Text(status_frame, height=10, state="disabled")
        self.status.pack(fill="both", expand=True)

        self.refresh_ports()
        self.log("Arduino IDE 시리얼 모니터는 닫아두세요.")
        self.log("털기 간격(ms)을 UI에서 직접 조절할 수 있습니다.")

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo["values"] = ports
        if ports and self.port_var.get() not in ports:
            self.port_var.set(ports[0])

    def toggle_connection(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.ser = None
            self.connect_btn.config(text="연결")
            self.log("연결 해제")
            return

        port = self.port_var.get()
        if not port:
            messagebox.showwarning("COM 포트", "COM 포트를 선택하세요.")
            return

        try:
            self.ser = serial.Serial(port, 115200, timeout=0.2)
            time.sleep(2)
            self.connect_btn.config(text="연결 해제")
            self.log(f"{port} 연결 완료")
            threading.Thread(target=self.read_serial, daemon=True).start()
        except Exception as e:
            messagebox.showerror("연결 실패", str(e))

    def send(self, text):
        if not self.ser or not self.ser.is_open:
            messagebox.showwarning("연결 필요", "먼저 ESP32에 연결하세요.")
            return False

        try:
            self.ser.write((text + "\n").encode("ascii"))
            self.log("전송: " + text)
            return True
        except Exception as e:
            messagebox.showerror("전송 실패", str(e))
            return False

    def run_sequence(self):
        angle = max(1.0, min(360.0, float(self.angle_var.get())))
        speed = max(1, min(127, int(self.speed_var.get())))
        shake_angle = max(1.0, min(45.0, float(self.shake_angle_var.get())))
        shake_count = max(1, min(20, int(self.shake_count_var.get())))
        shake_speed = max(1, min(127, int(self.shake_speed_var.get())))
        shake_interval = max(0, min(3000, int(self.shake_interval_var.get())))

        self.send(
            f"RUN,{angle:.1f},{speed},{shake_angle:.1f},"
            f"{shake_count},{shake_speed},{shake_interval}"
        )

    def jog(self, direction):
        self.send(f"JOG,{direction},10,3")

    def read_serial(self):
        while self.ser and self.ser.is_open:
            try:
                line = self.ser.readline().decode(errors="ignore").strip()
                if line:
                    self.root.after(0, self.log, "ESP32: " + line)
            except Exception:
                break

    def log(self, msg):
        self.status.config(state="normal")
        self.status.insert("end", msg + "\n")
        self.status.see("end")
        self.status.config(state="disabled")

    def on_close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    MotorUI(root)
    root.mainloop()
