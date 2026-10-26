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

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

CONFIG_FILE = "macropad_config.json"

# Добавили действия для комбинации
ACTIONS = [
    "Ничего",
    "Напечатать 'а'",
    "Напечатать 'б'",
    "Запустить программу",
    "Свернуть все окна (Win+D)",
    "Заблокировать ПК (Win+L)",
    "Сделать скриншот",
    "Быстрый Alt+Tab",
    "Закрыть окно (Alt+F4)",
    "Громкость +",
    "Громкость -"
]

class SetupWizard(ctk.CTkToplevel):
    def __init__(self, parent, current_config, on_save):
        super().__init__(parent)
        self.title("Настройки MacroPad")
        self.geometry("350x350") # Чуть увеличили высоту
        self.on_save = on_save
        self.resizable(False, False)
        self.grab_set() 
        
        ctk.CTkLabel(self, text="Настройка кнопок", font=("Arial", 18, "bold")).pack(pady=10)
        
        ctk.CTkLabel(self, text="Количество кнопок:").pack(pady=2)
        self.num_buttons = ctk.CTkOptionMenu(self, values=["1", "2", "3", "4"])
        self.num_buttons.pack(pady=2)
        self.num_buttons.set(str(current_config.get("num_buttons", 2)))
        
        ctk.CTkLabel(self, text="Пины (через запятую):").pack(pady=2)
        self.pins_entry = ctk.CTkEntry(self, placeholder_text="2,4")
        self.pins_entry.pack(pady=2)
        current_pins = current_config.get("pins", [2, 4])
        self.pins_entry.insert(0, ",".join(map(str, current_pins)))
        
        # --- НОВОЕ: Настройка комбинации ---
        ctk.CTkLabel(self, text="Действие при нажатии 2-х кнопок:").pack(pady=(10, 2))
        self.combo_action = ctk.CTkOptionMenu(self, values=ACTIONS)
        self.combo_action.pack(pady=2)
        self.combo_action.set(current_config.get("combo_action", "Быстрый Alt+Tab"))
        
        ctk.CTkButton(self, text="Сохранить и применить", command=self.save_and_close).pack(pady=15)
        
    def save_and_close(self):
        try:
            num = int(self.num_buttons.get())
            pins = [int(x.strip()) for x in self.pins_entry.get().split(",")]
            if len(pins) != num:
                raise ValueError("Количество пинов не совпадает!")
                
            config = {
                "num_buttons": num, 
                "pins": pins,
                "combo_action": self.combo_action.get() # Сохраняем действие для комбинации
            }
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f)
            
            self.on_save(config)
            self.destroy()
        except Exception as e:
            ctk.CTkLabel(self, text=f"Ошибка: {e}", text_color="red").pack()

class MacroPadApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Arduino MacroPad PRO")
        self.geometry("500x750")
        
        self.serial_port = None
        self.config = self.load_config()
        
        if not self.config:
            self.config = {"num_buttons": 2, "pins": [2, 4], "combo_action": "Быстрый Alt+Tab"}
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f)

        self.build_ui()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        return None

    def build_ui(self):
        for widget in self.winfo_children():
            widget.destroy()

        self.num_buttons = self.config.get("num_buttons", 2)
        self.pins = self.config.get("pins", [2, 4])
        
        # --- Заголовок и кнопка настроек ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(header_frame, text="MACROPAD PRO", font=("Arial", 24, "bold"), text_color="#00ffcc").pack(side="left")
        ctk.CTkButton(header_frame, text="⚙ Настройки", command=self.open_settings, width=100).pack(side="right")

        # --- Подключение ---
        self.frame_conn = ctk.CTkFrame(self)
        self.frame_conn.pack(pady=5, padx=20, fill="x")
        
        row_conn = ctk.CTkFrame(self.frame_conn, fg_color="transparent")
        row_conn.pack(fill="x", padx=10, pady=5)
        
        self.cb_ports = ctk.CTkComboBox(row_conn, values=["COM1"], width=120)
        self.cb_ports.pack(side="left", padx=5)
        
        ctk.CTkButton(row_conn, text="Подключить", command=self.connect_port, width=100).pack(side="left", padx=5)
        ctk.CTkButton(row_conn, text="Обновить", command=self.scan_ports, width=80).pack(side="left", padx=5)

        # --- Динамические кнопки ---
        self.frame_buttons = ctk.CTkScrollableFrame(self, height=350)
        self.frame_buttons.pack(pady=10, padx=20, fill="x")
        
        self.button_widgets = [] 
        
        for i in range(self.num_buttons):
            frame = ctk.CTkFrame(self.frame_buttons)
            frame.pack(pady=5, fill="x")
            ctk.CTkLabel(frame, text=f"Кнопка {i+1} (Pin {self.pins[i]}):", font=("Arial", 14, "bold")).pack(anchor="w", padx=10)
            
            opt = ctk.CTkOptionMenu(frame, values=ACTIONS)
            opt.pack(padx=10, pady=5, fill="x")
            opt.set("Ничего")
            self.button_widgets.append(opt)
            
            exe_frame = ctk.CTkFrame(frame, fg_color="transparent")
            entry = ctk.CTkEntry(exe_frame, placeholder_text="Путь к .exe", state="readonly")
            entry.pack(side="left", fill="x", expand=True, padx=5)
            btn = ctk.CTkButton(exe_frame, text="Обзор", width=50, command=lambda idx=i, ent=entry: self.browse_exe(ent))
            btn.pack(side="right", padx=5)
            
            def toggle_exe(choice, f=exe_frame):
                if choice == "Запустить программу":
                    f.pack(fill="x", padx=10, pady=5)
                else:
                    f.pack_forget()
                    
            opt.configure(command=lambda choice, func=toggle_exe: func(choice))
            self.button_widgets.append(entry)

        # --- Информация о комбинации ---
        combo_frame = ctk.CTkFrame(self, fg_color="#252525")
        combo_frame.pack(pady=5, padx=20, fill="x")
        combo_text = self.config.get("combo_action", "Быстрый Alt+Tab")
        ctk.CTkLabel(combo_frame, text=f"Комбинация (2 кнопки): {combo_text}", text_color="#00ffcc").pack(pady=5)

        # --- Статус ---
        self.lbl_status = ctk.CTkLabel(self, text="Статус: Не подключено", text_color="gray")
        self.lbl_status.pack(pady=10)

        self.scan_ports()

    def open_settings(self):
        SetupWizard(self, self.config, self.apply_settings)

    def apply_settings(self, new_config):
        self.config = new_config
        self.build_ui()
        self.lbl_status.configure(text="Настройки применены!", text_color="#00ffcc")

    def browse_exe(self, entry_widget):
        file_path = filedialog.askopenfilename(title="Выберите .exe", filetypes=[("Executable", "*.exe")])
        if file_path:
            entry_widget.configure(state="normal")
            entry_widget.delete(0, 'end')
            entry_widget.insert(0, file_path)
            entry_widget.configure(state="readonly")

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
            self.lbl_status.configure(text=f"Подключено к {port}", text_color="#00ffcc")
            threading.Thread(target=self.read_serial, daemon=True).start()
        except Exception:
            self.lbl_status.configure(text=f"Ошибка порта {port}", text_color="red")

    def execute_action(self, action, exe_path=""):
        try:
            if action == "Напечатать 'а'": keyboard.press_and_release('f')
            elif action == "Напечатать 'б'": keyboard.press_and_release(',')
            elif action == "Запустить программу":
                if exe_path and os.path.exists(exe_path): os.startfile(exe_path)
            elif action == "Свернуть все окна (Win+D)": keyboard.press_and_release('win+d')
            elif action == "Заблокировать ПК (Win+L)": keyboard.press_and_release('win+l')
            elif action == "Сделать скриншот": keyboard.press_and_release('win+prtscr')
            elif action == "Быстрый Alt+Tab": keyboard.press_and_release('alt+tab')
            elif action == "Закрыть окно (Alt+F4)": keyboard.press_and_release('alt+f4')
            elif action == "Громкость +": keyboard.press_and_release('volume up')
            elif action == "Громкость -": keyboard.press_and_release('volume down')
        except Exception as e:
            print(f"Ошибка: {e}")

    def read_serial(self):
        while self.serial_port and self.serial_port.is_open:
            try:
                line = self.serial_port.readline().decode('utf-8').strip()
                if line.startswith("CLICK"):
                    if line == "CLICK_BOTH":
                        # ВЫПОЛНЯЕМ ДЕЙСТВИЕ ДЛЯ КОМБИНАЦИИ
                        combo_action = self.config.get("combo_action", "Быстрый Alt+Tab")
                        self.lbl_status.configure(text=f"Комбинация: {combo_action}", text_color="purple")
                        self.execute_action(combo_action)
                    else:
                        try:
                            btn_num = int(line.replace("CLICK", "")) - 1
                            if 0 <= btn_num < self.num_buttons:
                                opt = self.button_widgets[btn_num * 2] 
                                entry = self.button_widgets[btn_num * 2 + 1] 
                                action = opt.get()
                                self.lbl_status.configure(text=f"Кнопка {btn_num+1}: {action}", text_color="blue")
                                self.execute_action(action, entry.get())
                        except ValueError:
                            pass
            except Exception:
                time.sleep(0.1)

if __name__ == "__main__":
    app = MacroPadApp()
    app.mainloop()