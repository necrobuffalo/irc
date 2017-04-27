import socket
import threading


class ConnectionData(threading.local):
    def __init__(self, conn, addr):
        self.conn = conn
        self.addr = addr


class ConnectionThread(threading.Thread):
    def __init__(self, conn, addr):
        self.ns = ConnectionData(conn, addr)
        threading.Thread.__init__(self)

    def run(self):
        print(self.ns.__dict__)
        print('Connected by', self.ns.addr)
        while True:
            data = self.ns.conn.recv(1024)
            if not data: break
            self.ns.conn.sendall(data)
        print('Disconnected from', self.ns.addr)
        self.ns.conn.close()


HOST = ''
PORT = 9000

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen(1)
    while True:
        conn, addr = s.accept()
        ConnectionThread(conn, addr).start()
