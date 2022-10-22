import socket
import threading
import struct
import signal
import sys
import json

cur_rgb = (255, 0, 0)
cur_alarm = b'06:00'

class CnC(threading.Thread):
    def __init__(self, sock: socket.socket):
        super().__init__()
        self.sock = sock
        self.running = False

    def run(self):
        self.running = True

        while self.running:
            conn, addr = self.sock.accept()
            print(f'Device connected {addr}')
            # conn.settimeout(1)
            while True:
                try:
                    b = conn.recv(1)
                    self.handle_req(conn, b)
                except TimeoutError:
                    continue
                except:
                    conn.close()
                    break

            print('Lost device connection')

    def handle_req(self, conn: socket.socket, cmd: bytes):
        global cur_rgb
        global cur_alarm

        if cmd == b'\x00':
            conn.sendall(struct.pack('>BBB', cur_rgb[0], cur_rgb[1], cur_rgb[2]))
        elif cmd == b'\x01':
            conn.sendall(cur_alarm)

    def kill(self):
        self.running = False

class WebApp(threading.Thread):
    def __init__(self, sock: socket.socket):
        super().__init__()
        self.sock = sock
        self.running = False

        self.html = open('index.html', 'rb').read()

    def run(self):
        self.running = True

        while self.running:
            global cur_rgb
            global cur_alarm

            conn, _ = self.sock.accept()
            lines = conn.recv(1024).split(b'\n')
            line = lines[0]
            body = lines[-1]

            if line.startswith(b'POST'):
                vals = json.loads(body.decode())
                print(vals)
                resp = self.post(vals)
                if resp is None:
                    conn.sendall(b'HTTP/1.1 400 Bad Request\r\n\r\n')
                else:
                    conn.sendall(b'HTTP/1.1 200 OK\r\n')
                    conn.sendall(f'Content-Length: {len(resp)}\r\n'.encode())
                    conn.sendall(b'\r\n')
                    conn.sendall(resp)
            else:
                conn.sendall(b'HTTP/1.1 200 OK\r\n\r\n')
                conn.sendall(
                    open('index.html', 'rb').read()
                        .replace(b'$RED', str(cur_rgb[0]).encode())
                        .replace(b'$GREEN', str(cur_rgb[1]).encode())
                        .replace(b'$BLUE', str(cur_rgb[2]).encode())
                        .replace(b'$ALARM', cur_alarm)
                )
            conn.close()

    def post(self, body: dict) -> bytes:
        if body.get('rgb') is not None:
            global cur_rgb

            vals = body['rgb']
            try:
                cur_rgb = (int(vals['r']), int(vals['g']), int(vals['b']))
                print(f'Set cur_rgb {cur_rgb}')
                return f'{cur_rgb}'.encode()
            except:
                return None

        if body.get('alarm') is not None:
            global cur_alarm
            cur_alarm = body['alarm'].encode()
            print(f'Set alarm {cur_alarm}')
            return cur_alarm

    def kill(self):
        self.running = False

def main():
    ip = sys.argv[1]

    cnc_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cnc_sock.bind((ip, 9001))
    print('CnC bound')
    cnc_sock.listen()

    web_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    web_sock.bind((ip, 8080))
    print('WebApp bound')
    web_sock.listen()

    command_thr = CnC(cnc_sock)
    command_thr.start()

    web_thr = WebApp(web_sock)
    web_thr.start()

    def sigint_handler(a, b):
        cnc_sock.close()
        web_sock.close()
        command_thr.kill()
        web_thr.kill()
        sys.exit(0)


    signal.signal(signal.SIGINT, sigint_handler)

    while True:
        pass


if __name__ == '__main__':
    main()
