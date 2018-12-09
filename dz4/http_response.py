#!/usr/bin/python
import os
import urllib
from datetime import datetime as DateTime

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
  'swf': 'application/x-shockwave-flash',
  'jpg': 'image/jpeg',
  'jpeg': 'image/jpeg',
  'png': 'image/png',
  'gif': 'image/gif',
}
METHODS = ['GET', 'HEAD']

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

  def __init__(self, req, root_directory, srv_name):
    self.data = None
    self.cur = 0
    self.headers = {}
    self.resource = None
    self.root_dir = os.path.abspath(root_directory)
    self.srv_name = srv_name
    self.build_response(req)

  def build_response(self, req):
    self.set_headers()
    if not req.is_valid:
      self.get_error(400, req.version)
    elif req.method in METHODS:
      path = self.path_from_url(req.url)
      if path[:len(self.root_dir)] != self.root_dir:
        self.get_error(403, req.version)
        return
      self.load_resource(path)
      if self.resource:
        self.data = '{} 200 OK\r\n'.format(req.version)
        self.set_headers()
        self.render_headers()
        if req.method == 'GET':
          self.render_body()
      else:
          self.get_error(404, req.version)
    else:
      self.get_error(405, req.version)

  def get_error(self, code, http_ver):
    self.data = '{} {} {} '.format(http_ver, code, ERRORS.get(code))
    self.render_headers()

  def path_from_url(self, url):
    if url[-1] == '/':
      url += 'index.html'
    if url[0] == '/':
      url = url[1:]
    path = urllib.unquote(url).decode('utf-8')
    path = path.split('?', 1)[0]
    path = os.path.join(self.root_dir, path)
    return os.path.abspath(path)

  def load_resource(self, path):
    if os.path.exists(path) and os.path.isfile(path):
      self.resource = Resource(path)
      self.resource.load()

  def set_headers(self):
    self.headers['Connection'] = 'close'
    self.headers['Date'] = self.httpdate(DateTime.utcnow())
    self.headers['Server'] = self.srv_name
    if self.resource:
      if self.resource.type:
        self.headers['Content-Type'] = self.resource.type
      self.headers['Content-Length'] = self.resource.length

  def render_headers(self):
    for name, value in self.headers.items():
      self.data += '%s: %s\r\n' % (name, value)
    self.data += '\r\n'

  def render_body(self):
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
