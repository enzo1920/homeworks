#!/usr/bin/python

import argparse
import datetime
import logging
import multiprocessing
import os
import select
import socket
import time


EOL1 = b'\n\n'
EOL2 = b'\n\r\n'
RESPONSE = b'HTTP/1.0 200 OK\r\nDate: Mon, 1 Jan 1996 01:01:01 GMT\r\n'
RESPONSE += b'Content-Type: text/plain\r\nContent-Length: 13\r\n\r\n'
RESPONSE += b'Hello, world!'

EPOLLEXCLUSIVE = 1 << 28
LOG_DIR = "./log"


class HTTPServ(object):
    def __init__(self, host, port, root_dir):
        self.host = host
        self.port = port
        self.rtdir = root_dir

    def create_servsock(self):
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.serversocket.bind((self.host, self.port))
        self.serversocket.listen(5000)
        self.serversocket.setblocking(0)
        print('srv pid:{}'.format(str(os.getpid())))
        return self.serversocket

    def epol_connect(self):
        ed = select.epoll()
        ed.register(self.serversocket, select.EPOLLIN | EPOLLEXCLUSIVE)
        connections = {}
        requests = {}
        responses = {}
        while True:

            events = ed.poll()
            for fileno, event in events:
                if fileno == self.serversocket.fileno():
                    try:
                        connection, address = self.serversocket.accept()
                        print(address)
                        connection.setblocking(0)
                        ed.register(connection.fileno(), select.EPOLLIN)
                        connections[connection.fileno()] = connection
                        requests[connection.fileno()] = b''
                        responses[connection.fileno()] = RESPONSE

                    except self.serversocket.error as ex:
                        logging.error('err_accept:{}'.format(ex))
                elif event & select.EPOLLIN:
                    try:
                        requests[fileno] += connections[fileno].recv(1024)
                        if EOL1 in requests[fileno] or EOL2 in requests[fileno]:
                            ed.modify(fileno, select.EPOLLOUT)
                            # TODO handle input data here
                            print('-' * 40 + '\n' + requests[fileno].decode()[:-2])
                    except Exception as ex:
                        logging.error('erorror read:{}'.format(ex))
                elif event & select.EPOLLOUT:
                    try:
                        byteswritten = connections[fileno].send(responses[fileno])
                        responses[fileno] = responses[fileno][byteswritten:]
                        if len(responses[fileno]) == 0:
                            ed.modify(fileno, 0)
                            connections[fileno].shutdown(socket.SHUT_RDWR)
                    except Exception as ex:
                        logging.error('err_write:{}'.format(ex))
                elif event & select.EPOLLHUP:
                    try:
                        ed.unregister(fileno)
                        connections[fileno].close()
                        del connections[fileno]
                    except Exception as ex:
                        logging.error('error close:{}'.format(ex))



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', help='root dir', default='./www')
    parser.add_argument('-l', help='log dir', default='./log')
    parser.add_argument('-p', help='port', type=int, default=8080)
    parser.add_argument('-w', help='worker', type=int, default=6)
    args = parser.parse_args()
    if not os.path.exists(args.l):
        os.makedirs(args.l)
    worklog_file = os.path.join(args.l,
                                'dummy_http_log-{0}.{1}'.format(datetime.datetime.now().strftime("%Y.%m.%d_%H-%M-%S"),
                                                                'log'))
    logging.basicConfig(filename=worklog_file, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    srv = HTTPServ('188.227.18.141', args.p, args.r)
    srv.create_servsock()
    logging.info("server started")
    logging.info(os.getpid())
    try:
        process_list = [multiprocessing.Process(target=srv.epol_connect, args=()) for i in range(args.w)]
        for i, p in enumerate(process_list):
            p.start()
            logging.info('process {}  started'.format(i + 1))
            logging.info(p.is_alive())
            print(p)
            time.sleep(0.1)
        for p in process_list:
            p.join()


    except KeyboardInterrupt:
        print(process_list)
        for worker_p in process_list:
            print(worker_p)
            if worker_p:
                worker_p.terminate()


if __name__ == '__main__':
    main()
