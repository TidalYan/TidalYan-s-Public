import cv2
import numpy as np
import pyautogui
import time
import tkinter as tk
from tkinter import filedialog
import threading
import os
import json
import pygame
import sys

# 初始化变量
selected_region = None
delay_time = 1
music_path = "default_music.wav"
is_running = False
is_playing = False
template_paths = ["Evil.png", "Bad.png", "Not_Good.png", "League_Against.png",
                  "Unsafe.png", "Dangerous.png", "Criminal.png", "Suspect.png",
                  "Team_Against.png", "Shooting.png"]
templates, template_colors = [], []

# 加载模板图像和颜色信息
def load_templates():
    global templates, template_colors
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    for template_path in template_paths:
        img_path = os.path.join(base_path, template_path)
        template = cv2.imread(img_path)
        templates.append(template)
        template_colors.append(cv2.mean(template)[:3])  # 获取平均颜色


load_templates()

# 加载保存的设置
def load_settings():
    global music_path, delay_time, selected_region
    if os.path.exists("settings.json"):
        with open("settings.json", "r") as f:
            settings = json.load(f)
            music_path = settings.get("music_path", "default_music.mp3")
            delay_time = settings.get("delay_time", 1)
            selected_region = settings.get("selected_region", None)

# 保存设置
def save_settings():
    with open("settings.json", "w") as f:
        json.dump({
            "music_path": music_path,
            "delay_time": delay_time,
            "selected_region": selected_region,
        }, f)

# 停止和播放音乐
def stop_music():
    global is_playing
    if is_playing:
        pygame.mixer.music.stop()
        is_playing = False

def play_music():
    global is_playing
    is_playing = True
    pygame.mixer.init()
    pygame.mixer.music.load(music_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
    is_playing = False

# 计算颜色相似度的函数
def is_color_similar(template_color, screenshot_color, threshold=80):
    return np.linalg.norm(np.array(template_color) - np.array(screenshot_color)) < threshold

# 图像相似度检测线程
def detect_image_similarity():
    global is_running, selected_region, delay_time
    is_running = True
    while is_running:
        if selected_region:
            x1, y1 = selected_region[0]
            x2, y2 = selected_region[1]
            screenshot = pyautogui.screenshot(region=(x1, y1, abs(x2 - x1), abs(y2 - y1)))
            screenshot_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
            screenshot_rgb = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

            for i, template in enumerate(templates):
                result = cv2.matchTemplate(screenshot_gray, cv2.cvtColor(template, cv2.COLOR_BGR2GRAY), cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                if max_val > 0.9:
                    matched_color = cv2.mean(screenshot_rgb[max_loc[1]:max_loc[1]+template.shape[0],
                                                            max_loc[0]:max_loc[0]+template.shape[1]])[:3]
                    if is_color_similar(template_colors[i], matched_color):
                        if not is_playing:
                            threading.Thread(target=play_music).start()
                        break
        time.sleep(delay_time)

# 选择音乐文件
def select_music():
    global music_path
    music_path = filedialog.askopenfilename(title="选择音乐文件", filetypes=[("音频文件", "*.mp3;*.wav")])
    save_settings()

# 启动和停止检测
def start_detection():
    if selected_region and not is_running:
        threading.Thread(target=detect_image_similarity).start()
    update_status_label()

def stop_detection():
    global is_running
    is_running = False
    stop_music()
    update_status_label()

# 更新状态标签
def update_status_label():
    status_text.set("正在运行" if is_running else "不在运行")

# 选择屏幕区域
def select_screen_area():
    def on_mouse_drag(event):
        nonlocal start_x, start_y
        canvas.coords(selection_rect, start_x, start_y, event.x, event.y)

    def on_mouse_release(event):
        global selected_region
        selected_region = [(start_x, start_y), (event.x, event.y)]
        root.destroy()
        save_settings()

    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.3)
    canvas = tk.Canvas(root, cursor="cross")
    canvas.pack(fill=tk.BOTH, expand=True)
    start_x, start_y = 0, 0

    def on_mouse_press(event):
        nonlocal start_x, start_y
        start_x, start_y = event.x, event.y
        global selection_rect
        selection_rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline="Green", width=2)

    canvas.bind("<ButtonPress-1>", on_mouse_press)
    canvas.bind("<B1-Motion>", on_mouse_drag)
    canvas.bind("<ButtonRelease-1>", on_mouse_release)
    root.mainloop()

# 启动UI窗口
def create_ui():
    load_settings()
    root = tk.Tk()
    root.title("EWSC频道预警系统v2.0")
    root.geometry("400x500")
    root.attributes('-topmost', True)

    tk.Label(root, text="检测时间 (秒):").pack()
    delay_scale = tk.Scale(root, from_=1, to=10, orient=tk.HORIZONTAL, command=lambda val: update_delay(int(val)))
    delay_scale.set(delay_time)
    delay_scale.pack()
    
    # 定义并直接在delay_scale中使用更新延迟时间的函数
    def update_delay(val):
        global delay_time
        delay_time = int(val)
        save_settings()

    delay_scale.config(command=update_delay)

    tk.Button(root, text="选择音乐文件", command=select_music).pack()
    tk.Button(root, text="选择检测区域", command=select_screen_area).pack()
    tk.Button(root, text="开始检测", command=start_detection).pack()
    tk.Button(root, text="停止检测", command=stop_detection).pack()

    global status_text
    status_text = tk.StringVar()
    update_status_label()
    tk.Label(root, textvariable=status_text).pack()
    
    # 添加复选框
    def toggle_auto_restart():
        global auto_restart_enabled
        auto_restart_enabled = not auto_restart_enabled  # 切换复选框的状态

    auto_restart_checkbox = tk.Checkbutton(root, text="鼠标静止活动两分钟后，自动开始检测", command=toggle_auto_restart)
    auto_restart_checkbox.pack()
    auto_restart_checkbox.deselect()  # 默认不勾选

    root.protocol("WM_DELETE_WINDOW", lambda: [stop_detection(), stop_music(), root.destroy()])
    root.mainloop()

if __name__ == "__main__":
    threading.Thread(target=create_ui).start()
