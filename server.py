import json
import socket
import struct
from threading import Thread

def wait_for_order():
    while 1:
        try:
            order = input()
        except Exception as e:
            order = "null"
            print("not normal control:", e)

        global start
        if order == "stop":
            start = False
            sock.close()
            break
        elif order == "show user":
            print(client_list)
        else:
            print("unknow command")

# set ip and port of server
host = "0.0.0.0"
port = 5000
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((host, port))

client_size = 0
client_list = {}
frame_buffer = {}
max_packet_size = 1200
current_frame_id = 0

start = True

if 1:
    thread_order = Thread(target=wait_for_order, daemon=True)
    thread_order.start()
    while start:
        try:
            packet, addr = sock.recvfrom(65535)
        except Exception as e:
            print(e)
  
        # read header
        header = packet[:struct.calcsize("IHBB")]
        frame_id, fragment_id, is_last, data_type = struct.unpack("IHBB", header)
        fragment_data = packet[struct.calcsize("IHBB"):]
        frame_size = len(fragment_data)

        src_id = None

        if data_type == 0:
            for i in client_list:
                if client_list[i] == addr:
                    src_id = i

            if not src_id:
                continue
                
            for i in client_list:
                if client_list[i] != addr:
                    for j in range(0, frame_size, max_packet_size):
                        fragment = fragment_data[j:j + max_packet_size]
                        header = struct.pack("IHBQB", frame_id, fragment_id, is_last, src_id, 0)
                        sock.sendto(header + fragment, client_list[i])
        elif data_type == 1:
            for i in client_list:
                if client_list[i] == addr:
                    src_id = i
            
            if not src_id:
                continue

            for i in client_list:
                if client_list[i] != addr:
                    for j in range(0, frame_size, max_packet_size):
                        fragment = fragment_data[j:j + max_packet_size]
                        header = struct.pack("IHBQB", frame_id, fragment_id, is_last, src_id, 1)
                        sock.sendto(header + fragment, client_list[i])
        elif data_type == 2:
            # check if is new packet
            if frame_id != current_frame_id:
                frame_buffer = {}
                current_frame_id = frame_id

            frame_buffer[fragment_id] = fragment_data

            if is_last:
                full_data = b"".join(frame_buffer[i] for i in sorted(frame_buffer.keys()))
                json_obj = json.loads(full_data.decode('utf-8'))

                if json_obj["type"] == "join":
                    client_list[client_size] = addr
                    client_size += 1

                    resend_signal = json.dumps({"type": "enter"}).encode("UTF-8")
                    resend_size = len(resend_signal)
                    for i in range(0, resend_size, max_packet_size):
                        fragment = resend_signal[i:i + max_packet_size]
                        header = struct.pack("IHBQB", 1, i // max_packet_size, i + max_packet_size >= resend_size, client_size - 1, 2)
                        sock.sendto(header + resend_signal, addr)

                    print(f"{addr} join")
                elif json_obj["type"] == "del" or json_obj["type"] == "msg":

                    for i in client_list:
                        if client_list[i] == addr:
                            src_id = i

                    if not src_id:
                        continue
                    
                    resend_signal = json.dumps(json_obj).encode("UTF-8")
                    resend_size = len(resend_signal)

                    for i in client_list:
                        if i != src_id:
                            for j in range(0, resend_size, max_packet_size):
                                fragment = resend_signal[j:j + max_packet_size]
                                header = struct.pack("IHBQB", 1, j // max_packet_size, j + max_packet_size >= resend_size, src_id, 2)
                                sock.sendto(header + fragment, client_list[i])

                    if json_obj["type"] == "del":
                        print(client_list[src_id], "leave")
                        del client_list[src_id]

sock.close()
