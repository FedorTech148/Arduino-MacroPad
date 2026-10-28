import customtkinter as ctk
from tkinter import filedialog
import serial
import serial.tools.list_ports
import keyboard
import time
import threading
import json
import os
import sys
import ctypes

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

# Расширенный список действий
ACTIONS = [
    "Ничего",
    "Медиа: Пауза/Играть",
    "Медиа: Следующий трек",
    "Медиа: Предыдущий трек",
    "Напечатать 'а'",
    "Напечатать 'б'",
    "Запустить программу",
    "Свернуть программу",
    "Открыть проводник",
    "Свернуть все окна (Win+D)",
    "Сделать скриншот",
    "Быстрый Alt+Tab"
]

# Функция для сворачивания окна по названию (через системные вызовы Windows)
def minimize_window_by_title(title_part):
    if sys.platform != 'win32':
        return
        
    user32 = ctypes.windll.user32
    
    def enum_windows_proc(hwnd, lParam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            # Если название окна содержит введенный текст (без учета регистра)
            if title_part.lower() in buff.value.lower():
                user32.ShowWindow(hwnd, 6) # 6 = SW_MINIMIZE
        return True
        
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    callback = EnumWindowsProc(enum_windows_proc)
    user32.EnumWindows(callback, 0)

class MacroPadApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Arduino MacroPad")
        self.geometry("450x620") # Сделали окно чуть выше
        self.resizable(False, False)

        self.serial_port = None

        # Заголовок
        self.label_title = ctk.CTkLabel(self, text="MACROPAD", font=("Arial", 24, "bold"), text_color="#00ffcc")
        self.label_title.pack(pady=10)

        # Блок подключения
        self.frame_conn = ctk.CTkFrame(self)
        self.frame_conn.pack(pady=5, padx=20, fill="x")
        
        row_conn = ctk.CTkFrame(self.frame_conn, fg_color="transparent")
        row_conn.pack(fill="x", padx=10, pady=5)
        
        self.cb_ports = ctk.CTkComboBox(row_conn, values=["COM1"], width=120)
        self.cb_ports.pack(side="left", padx=5)
        
        self.btn_connect = ctk.CTkButton(row_conn, text="Подключить", command=self.connect_port, width=100)
        self.btn_connect.pack(side="left", padx=5)
        
        self.btn_refresh = ctk.CTkButton(row_conn, text="Обновить", command=self.scan_ports, width=80)
        self.btn_refresh.pack(side="left", padx=5)

        # Блок Кнопки 1
        self.frame_btn1 = ctk.CTkFrame(self)
        self.frame_btn1.pack(pady=5, padx=20, fill="x")
        
        ctk.CTkLabel(self.frame_btn1, text="Кнопка 1 (Pin 2)", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=2)
        
        self.opt_btn1 = ctk.CTkOptionMenu(self.frame_btn1, values=ACTIONS, command=lambda e: self.toggle_exe(1))
        self.opt_btn1.pack(padx=10, pady=5, fill="x")
        self.opt_btn1.set("Медиа: Пауза/Играть")
        
        # Поле для пути к EXE
        self.frame_exe1 = ctk.CTkFrame(self.frame_btn1, fg_color="transparent")
        self.entry_exe1 = ctk.CTkEntry(self.frame_exe1, placeholder_text="Путь к .exe", state="readonly")
        self.entry_exe1.pack(side="left", fill="x", expand=True, padx=5)
        self.btn_browse1 = ctk.CTkButton(self.frame_exe1, text="Обзор...", command=lambda: self.browse_exe(1), width=60)
        self.btn_browse1.pack(side="right", padx=5)
        
        # Поле для названия окна (сворачивание)
        self.frame_win1 = ctk.CTkFrame(self.frame_btn1, fg_color="transparent")
        self.entry_win1 = ctk.CTkEntry(self.frame_win1, placeholder_text="Название окна (напр. Roblox)")
        self.entry_win1.pack(side="left", fill="x", expand=True, padx=5)

        # Блок Кнопки 2
        self.frame_btn2 = ctk.CTkFrame(self)
        self.frame_btn2.pack(pady=5, padx=20, fill="x")
        
        ctk.CTkLabel(self.frame_btn2, text="Кнопка 2 (Pin 4)", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=2)
        
        self.opt_btn2 = ctk.CTkOptionMenu(self.frame_btn2, values=ACTIONS, command=lambda e: self.toggle_exe(2))
        self.opt_btn2.pack(padx=10, pady=5, fill="x")
        self.opt_btn2.set("Медиа: Следующий трек")
        
        # Поле для пути к EXE
        self.frame_exe2 = ctk.CTkFrame(self.frame_btn2, fg_color="transparent")
        self.entry_exe2 = ctk.CTkEntry(self.frame_exe2, placeholder_text="Путь к .exe", state="readonly")
        self.entry_exe2.pack(side="left", fill="x", expand=True, padx=5)
        self.btn_browse2 = ctk.CTkButton(self.frame_exe2, text="Обзор...", command=lambda: self.browse_exe(2), width=60)
        self.btn_browse2.pack(side="right", padx=5)
        
        # Поле для названия окна (сворачивание)
        self.frame_win2 = ctk.CTkFrame(self.frame_btn2, fg_color="transparent")
        self.entry_win2 = ctk.CTkEntry(self.frame_win2, placeholder_text="Название окна (напр. Chrome)")
        self.entry_win2.pack(side="left", fill="x", expand=True, padx=5)

        # Статус
        self.lbl_status = ctk.CTkLabel(self, text="Статус: Не подключено", text_color="gray")
        self.lbl_status.pack(pady=10)

        self.scan_ports()
        self.toggle_exe(1)
        self.toggle_exe(2)

    def toggle_exe(self, btn_num):
        # Скрываем все дополнительные поля для этой кнопки
        if btn_num == 1:
            self.frame_exe1.pack_forget()
            self.frame_win1.pack_forget()
            action = self.opt_btn1.get()
            if action == "Запустить программу":
                self.frame_exe1.pack(fill="x", padx=10, pady=5)
            elif action == "Свернуть программу":
                self.frame_win1.pack(fill="x", padx=10, pady=5)
        else:
            self.frame_exe2.pack_forget()
            self.frame_win2.pack_forget()
            action = self.opt_btn2.get()
            if action == "Запустить программу":
                self.frame_exe2.pack(fill="x", padx=10, pady=5)
            elif action == "Свернуть программу":
                self.frame_win2.pack(fill="x", padx=10, pady=5)

    def browse_exe(self, btn_num):
        file_path = filedialog.askopenfilename(title="Выберите .exe", filetypes=[("Executable", "*.exe")])
        if file_path:
            if btn_num == 1:
                self.entry_exe1.configure(state="normal")
                self.entry_exe1.delete(0, 'end')
                self.entry_exe1.insert(0, file_path)
                self.entry_exe1.configure(state="readonly")
            else:
                self.entry_exe2.configure(state="normal")
                self.entry_exe2.delete(0, 'end')
                self.entry_exe2.insert(0, file_path)
                self.entry_exe2.configure(state="readonly")

    def scan_ports(self):
        ports = serial.tools.list_ports.comports()
        port_list = [p.device for p in ports]
        if port_list:
            self.cb_ports.configure(values=port_list)
            self.cb_ports.set(port_list[0])

    def connect_port(self):
        port = self.cb_ports.get()
        if not port: return
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            self.serial_port = serial.Serial(port, 9600, timeout=1)
            self.lbl_status.configure(text=f"Статус: Подключено к {port}", text_color="#00ffcc")
            threading.Thread(target=self.read_serial, daemon=True).start()
        except Exception:
            self.lbl_status.configure(text=f"Ошибка порта {port}", text_color="red")

    def execute_action(self, btn_num):
        if btn_num == 1:
            action = self.opt_btn1.get()
            exe_path = self.entry_exe1.get()
            win_title = self.entry_win1.get()
        else:
            action = self.opt_btn2.get()
            exe_path = self.entry_exe2.get()
            win_title = self.entry_win2.get()

        try:
            if action == "Медиа: Пауза/Играть": 
                keyboard.press_and_release('play/pause media')
            elif action == "Медиа: Следующий трек": 
                keyboard.press_and_release('next track')
            elif action == "Медиа: Предыдущий трек": 
                keyboard.press_and_release('previous track')
            elif action == "Напечатать 'а'": 
                keyboard.press_and_release('f')
            elif action == "Напечатать 'б'": 
                keyboard.press_and_release(',')
            elif action == "Запустить программу":
                if exe_path and os.path.exists(exe_path): 
                    os.startfile(exe_path)
            elif action == "Свернуть программу":
                if win_title:
                    minimize_window_by_title(win_title)
            elif action == "Открыть проводник": 
                os.startfile("C:\\")
            elif action == "Свернуть все окна (Win+D)": 
                keyboard.press_and_release('win+d')
            elif action == "Сделать скриншот": 
                keyboard.press_and_release('win+prtscr')
            elif action == "Быстрый Alt+Tab": 
                keyboard.press_and_release('alt+tab')
        except Exception as e:
            print(f"Ошибка: {e}")

    def read_serial(self):
        while self.serial_port and self.serial_port.is_open:
            try:
                line = self.serial_port.readline().decode('utf-8').strip()
                
                if line == "CLICK1":
                    action = self.opt_btn1.get()
                    self.lbl_status.configure(text=f"Кнопка 1: {action}", text_color="blue")
                    self.execute_action(1) 
                    
                elif line == "CLICK2":
                    action = self.opt_btn2.get()
                    self.lbl_status.configure(text=f"Кнопка 2: {action}", text_color="blue")
                    self.execute_action(2)
            except Exception:
                time.sleep(0.1)

if __name__ == "__main__":
    app = MacroPadApp()
    app.mainloop()