#!/usr/bin/python3.6

import logging
import os
import datetime
import argparse
from threading import Thread

import asyncio
import concurrent.futures


LOG_DIR = "./log"

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










class EchoServer(object):
    """Echo server class"""

    def __init__(self, host, port, loop=None):
        self._loop = loop or asyncio.get_event_loop()
        self._server = asyncio.start_server(self.handle_connection, host=host, port=port)

    def start(self, and_loop=True):
        self._server = self._loop.run_until_complete(self._server)
        logging.info('Listening established on {0}'.format(self._server.sockets[0].getsockname()))
        if and_loop:
            self._loop.run_forever()

    def stop(self, and_loop=True):
        self._server.close()
        if and_loop:
            self._loop.close()

    @asyncio.coroutine
    def handle_connection(self, reader, writer):
        peername = writer.get_extra_info('peername')
        logging.info('Accepted connection from {}'.format(peername))
        while not reader.at_eof():
            try:
                data = yield from asyncio.wait_for(reader.readline(), timeout=10.0)
                writer.write(data)
            except concurrent.futures.TimeoutError:
                break
        writer.close()


if __name__ == '__main__':

    num_workers = 10
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=LOG_DIR)
    (opts, args) = op.parse_args()
    if not os.path.exists(opts.log):
        os.makedirs(opts.log)
    worklog_file = os.path.join(opts.log,
                                'work_log-{0}.{1}'.format(datetime.datetime.now().strftime("%Y.%m.%d_%H-%M-%S"), 'log'))
    logging.basicConfig(filename=worklog_file, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = EchoServer('188.227.18.141', opts.port)
    try:
        server.start()
        logging.info('servrer start  on port  {}'.format(str(opts.port)))
    except KeyboardInterrupt:
        pass  # Press Ctrl+C to stop
    finally:
        server.stop()
