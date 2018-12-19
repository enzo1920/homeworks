#!/usr/bin/env python
# -*- coding: utf-8 -*-


import urllib2
from functools import wraps
import configparser
import logging
import json
import time
import socket
import os


OK = 200
BAD_REQUEST = 400
INTERNAL_ERROR = 500
ERRORS = {
  BAD_REQUEST: "Bad Request",
  OK: "OK",
  INTERNAL_ERROR: "Internal Server Error",
}

CONFIG_PATH = '/usr/local/etc/ip2w/ip2w.ini'
SECRET = '/usr/local/etc/ip2w/secret.json'

def set_logging(log_path):
  if not os.path.exists(os.path.dirname(log_path)):
    os.makedirs(os.path.dirname(log_path))
  logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S', filename=log_path, filemode='w', encoding='UTF-8')
  logging.info("worker_log is set")

def read_config(path):
  config = configparser.ConfigParser()
  config.read(path)
  config = dict(config["ip2w"])
  config["max_retries"] = int(config["max_retries"])
  config["timeout"] = float(config["timeout"])

  return config

'''retry decorator'''
def deco_retry(f,tries,delay):
    @wraps(f)
    def f_retry(*args, **kwargs):
      mtries, mdelay = tries, delay
      while mtries > 1:
          try:
            return f(*args, **kwargs)
          except:
            time.sleep(mdelay)
            mtries -= 1
            return f(*args, **kwargs)
    return f_retry

def is_valid_ipv4_address(address):
    try:
        socket.inet_pton(socket.AF_INET, address)
    except AttributeError:  # no inet_pton here, sorry
        try:
            socket.inet_aton(address)
        except socket.error:
            return False
        return address.count('.') == 3
    except socket.error:  # not a valid address
        return False
    return True

def get_location_by_ip(ip):
  url = 'https://ipinfo.io/%s/loc'% ip
  response = urllib2.urlopen(url, timeout=20).read()
  try:
    location = [float(n.strip()) for n in response.split(',')]
    logging.info(location)
  except Exception as ex:
      logging.error('get location by ip error {}'.format(str(ex)))
  return location

def get_weather(lat, lon):
  with open(SECRET) as fd:
    whether_apikey = json.loads(fd.read())['apikey']
  url = 'http://api.openweathermap.org/data/2.5/weather?lat=%s&lon=%s&APPID=%s' % (lat, lon, whether_apikey)
  response = urllib2.urlopen(url, timeout=20).read()
  response = json.loads(response)
  city = response['name']
  temp = float(response['main']['temp']) - 273.15
  conditions = response['weather'][0]['description']
  print(city, temp, conditions)
  return {'city': city, 'temp': temp, 'conditions': conditions}

def application(environ, start_response):
  config = read_config(CONFIG_PATH)
  set_logging(config["logto"])
  url = environ['REQUEST_URI']
  logging.info('url {} '.format(url))
  try:
    ip = url.split('/')[-1]
    if is_valid_ipv4_address(ip):
      dec_get_location_by_ip = deco_retry(get_location_by_ip, config["max_retries"], config["timeout"])
      dec_get_weather = deco_retry(get_weather, config["max_retries"], config["timeout"])
      lat, lon = dec_get_location_by_ip(ip)
      weather = dec_get_weather(lat, lon)
      code = 200
      status = '{} {}'.format(code, ERRORS.get(code))
      body = json.dumps(weather)
    else:
      code = 400
      status = '{} {}'.format(code, ERRORS.get(code))
      body = json.dumps({'error': 'invalid IP'})
      logging.error('not valid ip {}'.format(str(ip)))
  except Exception as ex:
    code = 500
    status = '{} {}'.format(code, ERRORS.get(code))
    body = json.dumps({'error': str(ex)})
    logging.error('application {} '.format(str(ex)))
  start_response(status, [('Content-Type', 'application/json'),
                            ('Content-Length', str(len(body)))])
  return [body]
