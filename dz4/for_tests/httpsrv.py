#!/usr/bin/python

from optparse import OptionParser
import os
import select
import socket
import urllib
import datetime

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

class HttpServer(object):

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.epoll = None
        self.servsock = None
        self.clients = {}
        self.requests = {}
        self.responses = {}

    def bind(self):
        self.servsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.servsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.servsock.bind((self.host, self.port))
        self.servsock.listen(50)
        self.servsock.setblocking(0)
        self.epoll.register(self.servsock.fileno(), select.EPOLLIN)




def main():
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    op.add_option("-d", "--directory", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')

    server = HttpServer(("localhost", opts.port), HttpServer)
    logging.info("Starting server at %s" % opts.port)

r

    try:
        server.start()
    except KeyboardInterrupt:
        pass
    server._close()



if __name__ == '__main__':
    main()
