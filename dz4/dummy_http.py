#!/usr/bin/python

import multiprocessing
import threading
import datetime
import logging
import select
import socket
import time
import os




EOL1 = b'\n\n'
EOL2 = b'\n\r\n'
RESPONSE = b'HTTP/1.0 200 OK\r\nDate: Mon, 1 Jan 1996 01:01:01 GMT\r\n'
RESPONSE += b'Content-Type: text/plain\r\nContent-Length: 13\r\n\r\n'
RESPONSE += b'Hello, world!'

LOG_DIR = "./log"


class HTTPServ(object):

    def __init__(self, host, port, max_connections):
        self.host = host
        self.port = port
        self.max_connections = max_connections
        self.connections = {}
        self.requests = {}
        self.responses = {}

    def create_servsock(self):
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serversocket.bind((self.host, self.port))
        self.serversocket.listen(1)
        self.serversocket.setblocking(0)

    def worker(self):
        self.epoll = select.epoll()
        self.epoll.register(self.serversocket.fileno(), select.EPOLLIN)
        logging.info(os.getpid())
        try:
            while True:
                events = self.epoll.poll(1)
                for fileno, event in events:
                    #print("i'm from {} my pid is {}".format(str(fileno), str(os.getpid())))
                    if fileno == self.serversocket.fileno():
                        connection, address = self.serversocket.accept()
                        connection.setblocking(0)
                        self.epoll.register(connection.fileno(), select.EPOLLIN)
                        self.connections[connection.fileno()] = connection
                        self.requests[connection.fileno()] = b''
                        self.responses[connection.fileno()] = RESPONSE
                    elif event & select.EPOLLIN:
                        self.requests[fileno] += self.connections[fileno].recv(1024)
                        if EOL1 in self.requests[fileno] or EOL2 in self.requests[fileno]:
                            self.epoll.modify(fileno, select.EPOLLOUT)
                            print('-' * 40 + '\n' + self.requests[fileno].decode()[:-2])
                    elif event & select.EPOLLOUT:
                        byteswritten = self.connections[fileno].send(self.responses[fileno])
                        self.responses[fileno] = self.responses[fileno][byteswritten:]
                        if len(self.responses[fileno]) == 0:
                            self.epoll.modify(fileno, 0)
                            self.connections[fileno].shutdown(socket.SHUT_RDWR)
                    elif event & select.EPOLLHUP:
                        self.epoll.unregister(fileno)
                        self.connections[fileno].close()
                        del self.connections[fileno]
        finally:
            self.epoll.unregister(self.serversocket.fileno())
            self.epoll.close()
            self.serversocket.close()


def main():
    worklog_file = os.path.join(LOG_DIR,
                                'dummy_http_log-{0}.{1}'.format(datetime.datetime.now().strftime("%Y.%m.%d_%H-%M-%S"),
                                                                'log'))
    logging.basicConfig(filename=worklog_file, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    srv = HTTPServ('188.227.18.141', 8080, 5)
    srv.create_servsock()
    logging.info("server started")
    logging.info(os.getpid())
    try:
        # workers = []
        process_list = [multiprocessing.Process(target=srv.worker, args=()) for i in range(3)]
        print(process_list)
        for i, p in enumerate(process_list):
            logging.info('process {} will start'.format(i + 1))
            p.start()
            print(p, p.is_alive())
            time.sleep(0.1)
            # p.join()


    except KeyboardInterrupt:
        print(process_list)
        for worker_p in process_list:
            print (worker_p)
            if worker_p:
                worker_p.terminate()


if __name__ == '__main__':
    main()
