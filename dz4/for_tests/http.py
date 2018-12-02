#!/usr/bin/python

import argparse
import os
import select
import socket
import urllib
import multiprcosessing
from datetime import datetime as DateTime



LOG_DIR = "./log"
DOCUMENT_ROOT = None
SERVER_NAME = 'httpsrv1'


OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}

CONTENT_TYPE = {
    'html': 'text/html',
    'css': 'text/css',
    'js': 'application/javascript',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
}


class HttpRequest(object):

    def __init__(self):
        self.data = ''
        self.method = None
        self.uri = None
        self.headers = {}
        self.is_valid = None
        self.is_ready = False

    def add_data(self, data):
        self.data += data
        index = self.data.find('\r\n\r\n')
        if index != -1:
            try:
                self._parse_data(self.data[:index])
                self.is_valid = True
            except:
                self.is_valid = False
            self.is_ready = True

    def _parse_data(self, data):
        lines = data.split('\r\n')
        self.method, self.uri, ver = lines[0].split(' ')
        for line in lines[1:]:
            name, value = line.split(':', 1)
            self.headers[name.strip()] = value.strip()


class Resource(object):
    def __init__(self, path):
        self.path = path
        self.type = None
        self.length = None
        self.data = None

    def load(self):
        self.type = CONTENT_TYPE.get(self.path.rsplit('.', 1)[-1])
        with open(self.path, 'rb') as f:
            self.data = f.read()
        self.length = len(self.data)


class HttpResponse(object):




    def __init__(self, req):
        self.data = None
        self.cur = 0
        self.headers = {}
        self.resource = None
        self._build_response(req)

    def _build_response(self, req):
        self._set_headers()
        if not req.is_valid:
            self._render4xx(400)
        elif req.method in ('HEAD', 'GET'):
            path = self._path_from_uri(req.uri)
            if path[:len(self.DOCUMENT_ROOT)] != self.DOCUMENT_ROOT:
                self._render4xx(403)
                return
            self._load_resource(path)
            if self.resource:
                self.data = 'HTTP/1.1 200 OK\r\n'
                self._set_headers()
                self._render_headers()
                if req.method == 'GET':
                    self._render_body()
            else:
                if req.uri[-1] == '/':
                    self._render4xx(403)
                else:
                    self._render4xx(404)
        else:
            self._render4xx(405)

    def _render4xx(self, code):
        if code not in ERRORS:
            self.data = 'HTTP/1.1 %s %s' % ERRORS.get(code, ERRORS[code])
        else:
            self.data = 'HTTP/1.1 %s %s' % ERRORS.get(code, "Unknown Error")
        self._render_headers()

    def _path_from_uri(self, uri):
        if uri[-1] == '/':
            uri += 'index.html'
        if uri[0] == '/':
            uri = uri[1:]
        path = urllib.unquote(uri).decode('utf-8')
        path = path.split('?', 1)[0]
        path = os.path.join(self.DOCUMENT_ROOT, path)
        return os.path.abspath(path)

    def _load_resource(self, path):
        if os.path.exists(path) and os.path.isfile(path):
            self.resource = Resource(path)
            self.resource.load()

    def _set_headers(self):
        self.headers['Connection'] = 'close'
        self.headers['Date'] = self.httpdate(DateTime.utcnow())
        self.headers['Server'] = SERVER_NAME
        if self.resource:
            if self.resource.type:
                self.headers['Content-Type'] = self.resource.type
            self.headers['Content-Length'] = self.resource.length

    def _render_headers(self):
        for name, value in self.headers.items():
            self.data += '%s: %s\r\n' % (name, value)
        self.data += '\r\n'

    def _render_body(self):
        self.data += self.resource.data

    def read(self, nbytes):
        return self.data[self.cur: self.cur + nbytes]

    def seek(self, nbytes):
        self.cur += nbytes

    def is_empty(self):
        return self.cur >= len(self.data)

    @staticmethod
    def httpdate(dt):
        weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]
        month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
                 "Oct", "Nov", "Dec"][dt.month - 1]
        return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (weekday, dt.day, month,
                                                        dt.year, dt.hour, dt.minute, dt.second)


class HttpServer(object):

    def __init__(self, host, port, max_connections):
        self.host = host
        self.port = port
        self.max_connections = max_connections
        self.epoll = None
        self.servsock = None
        self.clients = {}
        self.requests = {}
        self.responses = {}

    def start(self):
        self._bind()
        try:
            while True:
                self._handle_events()
        finally:
            self._close()

    def _bind(self):
        self.servsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.servsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.servsock.bind((self.host, self.port))
        self.servsock.listen(self.max_connections)
        self.servsock.setblocking(0)#Non blocking socket server
        self.epoll = select.epoll()
        self.epoll.register(self.servsock.fileno(), select.EPOLLIN)

    def _handle_events(self):
        events = self.epoll.poll(1)# Timeout 1 second
        for fileno, event in events:
            if fileno == self.servsock.fileno():
                self._accept_client()
            elif event & select.EPOLLIN:
                self._read_from_client(fileno)
            elif event & select.EPOLLOUT:
                self._write_to_client(fileno)
            elif event & select.EPOLLHUP:
                self._close_client(fileno)

    def _accept_client(self):
        client, addr = self.servsock.accept()
        client.setblocking(0)
        self.epoll.register(client.fileno(), select.EPOLLIN)
        self.clients[client.fileno()] = client
        self.requests[client.fileno()] = HttpRequest()

    def _read_from_client(self, fileno):
        data = self.clients[fileno].recv(1024)
        req = self.requests[fileno]
        req.add_data(data)
        if req.is_ready:
            self.epoll.modify(fileno, select.EPOLLOUT)
            self.responses[fileno] = HttpResponse(req)

    def _write_to_client(self, fileno):
        client = self.clients[fileno]
        resp = self.responses[fileno]
        data = resp.read(1024)
        nbytes = client.send(data)
        resp.seek(nbytes)
        if resp.is_empty():
            client.shutdown(socket.SHUT_RDWR)
            self._close_client(fileno)

    def _close_client(self, fileno):
        self.epoll.unregister(fileno)
        self.requests.pop(fileno, None)
        self.responses.pop(fileno, None)
        client = self.clients.pop(fileno, None)
        if client:
            client.close()

    def _close(self):
        self.epoll.unregister(self.servsock.fileno())
        self.epoll.close()
        self.servsock.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', help=' root dir')
    parser.add_argument('-l', help=' log dir')
    parser.add_argument('-p', help='port', type=int, default=8080)
    parser.add_argument('-w', help='worker', type=int, default=4)
    parser.add_argument('-m', help='max_con listen', type=int, default=50)
    args = parser.parse_args()
    if not os.path.exists(opts.log):
        os.makedirs(opts.log)
    worklog_file = os.path.join(opts.log,
                                'work_log-{0}.{1}'.format(datetime.datetime.now().strftime("%Y.%m.%d_%H-%M-%S"), 'log'))
    logging.basicConfig(filename=worklog_file, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    HttpResponse.DOCUMENT_ROOT = args.r
    server = HttpServer('127.0.0.1', args.p, args.max_con)
    try:
        server.start()
        loggin.info('server start on ')


        workers = []

        for i in range(args.worker):
            worker = multiprocessing.Process(target=server._accept_client())
            workers.append(worker)
            worker.start()
            logging.info("{} worker started".format(i + 1))
            for worker in workers:
                worker.join()
    except KeyboardInterrupt:
            for worker in workers:
                if worker:
                    worker.terminate()
    finally:
        logging.info("Server shutdown")
         server._close()






if __name__ == '__main__':
    main()
