#!/usr/bin/python

from http_response import HttpResponse, Resource
from http_request import HttpRequest
import multiprocessing
import datetime
import argparse
import logging
import select
import socket
import time
import os

EPOLLEXCLUSIVE = 1 << 28
LOG_DIR = "./log"
SERVER_NAME = 'dummy_http'
SERVER_IP = '127.0.0.1'

class HTTPServ(object):
  def __init__(self, host, port, root_dir,server_name):
    self.host = host
    self.port = port
    self.rtdir = root_dir
    self.srv_name = server_name

  def create_servsock(self):
    self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.serversocket.bind((self.host, self.port))
    self.serversocket.listen(50)
    self.serversocket.setblocking(0)

  def ephandle(self):
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
            connection.setblocking(0)
            ed.register(connection.fileno(), select.EPOLLIN)
            connections[connection.fileno()] = connection
            requests[connection.fileno()] = HttpRequest()
          except Exception as ex:
            logging.error('err_accept:{}'.format(ex))
        elif event & select.EPOLLIN:
          # handle input data
          try:
            data = connections[fileno].recv(1024)
            req = requests[fileno]
            req.add_data(data)
            if req.is_ready:
              ed.modify(fileno, select.EPOLLOUT)
              responses[fileno] = HttpResponse(req, self.rtdir, self.srv_name)
          except Exception as ex:
            logging.exception('erorror read:{}'.format(ex))
        elif event & select.EPOLLOUT:
          try:
            connection = connections[fileno]
            resp = responses[fileno]
            data = resp.read(1024)
            nbytes = connection.send(data)
            resp.seek(nbytes)
            if resp.is_empty():
              connection.shutdown(socket.SHUT_RDWR)
              ed.unregister(fileno)
              requests.pop(fileno, None)
              responses.pop(fileno, None)
              connection = connections.pop(fileno, None)
              if connection:
                  connection.close()
          except Exception as ex:
            logging.exception('err_write:{}'.format(ex))
        elif event & select.EPOLLHUP:
          try:
            ed.unregister(fileno)
            connections[fileno].close()
            del connections[fileno]
          except Exception as ex:
            logging.exception('error close:{}'.format(ex))


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
  srv = HTTPServ(SERVER_IP, args.p, args.r, SERVER_NAME)
  srv.create_servsock()
  logging.info("server {} started".format(SERVER_NAME))
  logging.info(os.getpid())
  try:
    process_list = [multiprocessing.Process(target=srv.ephandle, args=()) for i in range(args.w)]
    for i, p in enumerate(process_list):
      p.start()
      logging.info('process {}  started'.format(i + 1))
      logging.info(p)
      time.sleep(0.1)
    for p in process_list:
      p.join()
  except KeyboardInterrupt:
    for worker_p in process_list:
      if worker_p:
        worker_p.terminate()

if __name__ == '__main__':
  try:
    main()
  except Exception as exc:
    logging.exception(exc)
