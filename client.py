import cv2
import time
import json
import socket
import struct
import pyaudio
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk
from threading import Thread

host = "192.168.0.173"
port = 5000

local_host = "192.168.0.173"
local_port = 5001

# setting for pyaudio
FORMAT = pyaudio.paInt16
CHANNELS = 1 # 單聲道
RATE = 44100 # 取樣率
CHUNK = 1024 # 每塊數據大小

msg_str = ""
frame_buffer = {}
current_frame_id = -1
other_list = {}
max_packet_size = 1200
camera_open = True
mic_open = True
already_join = False

class ImageCapture:
    def __init__(self, image_path):
        self.frame = cv2.imread(image_path)
        self.is_opened = self.frame is not None

    def isOpened(self):
        return self.is_opened

    def read(self):
        return (self.is_opened, self.frame)

class my_canvas(tk.Canvas):
    def __init__(self):
        super().__init__()
        self.current_frame_id = None
        self.frame_buffer = {}

    def get(self, frame_id, fragment_id, is_last, fragment_data):
        if frame_id != self.current_frame_id:
            self.frame_buffer = {}
            self.current_frame_id = frame_id

        self.frame_buffer[fragment_id] = fragment_data

        if is_last:
            # 按序号合并数据
            frame_data = b"".join(self.frame_buffer[i] for i in sorted(self.frame_buffer.keys()))
            frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            self.create_image(0, 0, anchor=tk.NW, image=imgtk)
            self.image = imgtk

def receive():
    while 1:
        data, addr = sock.recvfrom(65535)

        if addr != (host, port):
            print("unknow transfer", addr)
            continue

        header = data[:struct.calcsize("IHBQB")]
        frame_id, fragment_id, is_last, other_id, data_type = struct.unpack("IHBQB", header)
        fragment_data = data[struct.calcsize("IHBQB"):]

        if data_type == 0:
            if other_id not in other_list:
                other_list[other_id] = my_canvas()
                other_list[other_id].config(bg="skyblue")
                other_list[other_id].place(x=220*((len(other_list.keys()))%3), y=150*((len(other_list.keys()))//3), width=220, height=150)

            other_list[other_id].get(frame_id, fragment_id, is_last, fragment_data)
        elif data_type == 1:
            stream_in.write(fragment_data)
        elif data_type == 2:
            global frame_buffer, current_frame_id
            if frame_id != current_frame_id:
                frame_buffer = {}
                current_frame_id = frame_id

            frame_buffer[fragment_id] = fragment_data

            if is_last:
                full_data = b"".join(frame_buffer[i] for i in sorted(frame_buffer.keys()))
                json_obj = json.loads(full_data.decode('utf-8'))

                if json_obj["type"] == "del":
                    print(other_id, "leave")
                    other_list[other_id].delete("all")
                    other_list[other_id].destroy()
                    del other_list[other_id]
                elif json_obj["type"] == "msg":
                    print(json_obj)
                    global msg_str
                    msg_str += json_obj["msg"] + "\n"
                    text_label.config(text=msg_str)
                elif json_obj["type"] == "enter":
                    global already_join
                    already_join = True

def update_canvas():
    # take camera
    while 1:
        if camera_open:
            ret, frame = cap.read()
        else:
            ret, frame = no_camera.read()

        if not ret:
            switch_camera()
            ret, frame = no_camera.read()

        frame = cv2.resize(frame, (220, 150))

        _, buffer = cv2.imencode('.jpg', frame)

        # bgr to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # change to pil img
        img = Image.fromarray(frame)

        # change to tk img
        imgtk = ImageTk.PhotoImage(image=img)

        # update to canvas
        local_video.create_image(0, 0, anchor=tk.NW, image=imgtk)
        local_video.image = imgtk  # 防止被垃圾回收

        frame_data = buffer.tobytes()
        frame_size = len(frame_data)

        for i in range(0, frame_size, max_packet_size):
            fragment = frame_data[i:i + max_packet_size]
            # hearder：id (4 byte) + piece number (2 byte) + if is last one (1byte) + data type (1 byte)
            header = struct.pack("IHBB", 1, i // max_packet_size, i + max_packet_size >= frame_size, 0)
            sock.sendto(header + fragment, (host, port))

def update_audio():
    # take audio
    while 1:
        if not mic_open:
            time.sleep(1)
            continue
        audio_data = stream_out.read(CHUNK)
        frame_size = len(audio_data)

        for i in range(0, frame_size, max_packet_size):
            fragment = audio_data[i:i + max_packet_size]
            header = struct.pack("IHBB", 1, i // max_packet_size, i + max_packet_size >= frame_size, 1)
            sock.sendto(header + fragment, (host, port))

def switch_camera():
    global camera_open
    camera_open = not camera_open
    global camera_lock
    if camera_open:
        camera_lock.config(bg="skyblue")
    else:
        camera_lock.config(bg="red")

def switch_mic():
    global mic_open
    mic_open = not mic_open
    if mic_open:
        mic_lock.config(bg="skyblue")
    else:
        mic_lock.config(bg="red")

def send_msg():
    global msg_str
    msg = text_input.get()
    msg_str += msg + "\n"
    text_label.config(text=msg_str)
    msg_signal = json.dumps({"type": "msg", "msg": msg}).encode("UTF-8")
    frame_size = len(msg_signal)

    for i in range(0, frame_size, max_packet_size):
        fragment = msg_signal[i:i + max_packet_size]
        header = struct.pack("IHBB", 1, i // max_packet_size, i + max_packet_size >= frame_size, 2)
        sock.sendto(header + fragment, (host, port))

# 清暫存
def on_closing():

    global already_join
    del_signal = json.dumps({"type": "del"}).encode("UTF-8")
    frame_size = len(del_signal)

    for i in range(0, frame_size, max_packet_size):
        fragment = del_signal[i:i + max_packet_size]
        header = struct.pack("IHBB", 1, i // max_packet_size, i + max_packet_size >= frame_size, 2)
        sock.sendto(header + fragment, (host, port))

    sock.close()
    audio.close(stream_in)
    audio.close(stream_out)
    cap.release()
    win.destroy()

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((local_host, local_port))

# init pyaudio
audio = pyaudio.PyAudio()
stream_out = audio.open(format=FORMAT, channels=CHANNELS,
                    rate=RATE, input=True,
                    frames_per_buffer=CHUNK)
stream_in = audio.open(format=FORMAT, channels=CHANNELS,
                    rate=RATE, output=True)

cap = cv2.VideoCapture(0)
no_camera = ImageCapture("no_camera.png")

win = tk.Tk()
win.title = "meeting room"
win.geometry("1200x700")
win.resizable(False, False)

local_video = tk.Canvas()
local_video.config(bg="black")
local_video.place(x=0, y=0, width=220, height=150)

camera_lock = tk.Button(text="camera")
camera_lock.config(bg="skyblue", command=switch_camera)
camera_lock.place(x=100, y=600, width=100, height=50)

mic_lock = tk.Button(text="mic")
mic_lock.config(bg="skyblue", command=switch_mic)
mic_lock.place(x=200, y=600, width=100, height=50)

leave_button = tk.Button(text="leave")
leave_button.config(bg="skyblue", command=on_closing)
leave_button.place(x=300, y=600, width=100, height=50)

text_label = tk.Label()
text_label.config(bg="skyblue", anchor="nw", justify="left")
text_label.place(x=800, y=0, width=400, height=700)

text_input = tk.Entry()
text_input.place(x=810, y=650, width=350, height=30)

send_msg_button = tk.Button(text="send")
send_msg_button.config(command=send_msg)
send_msg_button.place(x=1160, y=650, width=30, height=30)

thread_1 = Thread(target=update_canvas, daemon=True)
thread_2 = Thread(target=receive, daemon=True)
thread_3 = Thread(target=update_audio, daemon=True)
thread_1.start()
thread_2.start()
thread_3.start()

win.protocol("WM_DELETE_WINDOW", on_closing)

join_signal = json.dumps({"type": "join"}).encode("UTF-8")
frame_size = len(join_signal)

for i in range(0, frame_size, max_packet_size):
    fragment = join_signal[i:i + max_packet_size]
    # 帧头：帧ID（4字节） + 分片序号（2字節） + 是否是最後一個片段（1字節）
    header = struct.pack("IHBB", 1, i // max_packet_size, i + max_packet_size >= frame_size, 2)
    sock.sendto(header + fragment, (host, port))

win.mainloop()