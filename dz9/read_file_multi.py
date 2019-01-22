#!/usr/bin/env python
# -*- coding: utf-8 -*-
import collections
import threading
import logging
import Queue
import gzip
import glob
import sys
import os
# brew install protobuf
# protoc  --python_out=. ./appsinstalled.proto
# pip install protobuf
#import appsinstalled_pb2
# pip install python-memcached
#import memcache

NORMAL_ERR_RATE = 0.01
AppsInstalled = collections.namedtuple("AppsInstalled", ["dev_type", "dev_id", "lat", "lon", "apps"])


def dot_rename(path):
    head, fn = os.path.split(path)
    # atomic in most cases
    os.rename(path, os.path.join(head, "." + fn))

#Number of threads
n_thread = 5
#Create queue
queue = Queue.Queue()

class ThreadClass(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
    #Assign thread working with queue
        self.queue = queue

    def run(self):
        while True:
        #Get from queue job
            fline = self.queue.get()
            self.parse_appsinstalled(fline)
            #print self.getName() + ":" + fline
        #signals to queue job is done
            self.queue.task_done()

    def parse_appsinstalled(self, line):
        line_parts = line.strip().split("\t")
        if len(line_parts) < 5:
            return
        dev_type, dev_id, lat, lon, raw_apps = line_parts
        if not dev_type or not dev_id:
            return
        try:
            apps = [int(a.strip()) for a in raw_apps.split(",")]
        except ValueError:
            apps = [int(a.strip()) for a in raw_apps.split(",") if a.isidigit()]
            logging.info("Not all user apps are digits: `%s`" % line)
        try:
            lat, lon = float(lat), float(lon)
        except ValueError:
            logging.info("Invalid geo coords: `%s`" % line)
        return AppsInstalled(dev_type, dev_id, lat, lon, apps)


#Create number process
for i in range(n_thread):
    t = ThreadClass(queue)
    t.setDaemon(True)
    #Start thread
    t.start()





# from first dz
def openfile(filename):
    if filename.endswith('.gz'):
        return gzip.open(filename, 'rt')
    else:
        return open(filename, 'r')

#Read file line by line
with openfile("20170929000100.tsv.gz") as sample:
  for line in sample:
      #Put line to queue
      queue.put(line)
   #wait on the queue until everything has been processed
  queue.join()