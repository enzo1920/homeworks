#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import gzip
import time
import glob
import logging
import collections
from optparse import OptionParser
from argparse import ArgumentParser
import memcache
from multiprocessing import Pool, cpu_count
from threading import Thread
from multiprocessing import Queue as queue


class MemcacheClient(Thread):

    def __init__(self, addr):
        super(MemcacheClient, self).__init__()
        self.daemon = True
        self.queue = queue()
        self.addr = addr
        self.errors = 0

    def set(self, msg):
        self.queue.put(msg)

    def try_to_stop(self):
        self.queue.put(None)

    def get(self, key):
        mc = memcache.Client([self.addr])
        get_val = mc.get(key)
        print(get_val)

    def run(self):
        mc = memcache.Client([self.addr])
        while True:
            msg = self.queue.get()
            if msg is None:
                break
            mc.set(msg['key'], msg['data'])



class Worker(object):

    def __init__(self, devtype2addr):
        self.addr = devtype2addr.get("adid")

    def getName(self):
        return self.__class__.__name__

    def starter(self, fname):
        head, fn = os.path.split(fname)
        print('worker_{}'.format(fn))
        mc = MemcacheClient(self.addr)
        mc.start()
        for i in range(0,12):
           msg = {'key': "{0:b}".format(i), 'data': '{} forty two'.format(str(i))}
           mc.set(msg)
           time.sleep(0.5)
           mc.get("{0:b}".format(i))
        mc.try_to_stop()
        mc.join()
        return fname

def main(options):
    devtype2addr = {
        "idfa": options.idfa,
        "gaid": options.gaid,
        "adid": options.adid,
        "dvid": options.dvid,
    }

    max_worker_count = cpu_count()
    fnames = glob.glob(options.pattern)
    fnames = sorted(fnames)
    for fname in Pool(options.workers).imap(Worker(devtype2addr).starter, fnames):
        print("start file {}".format(str(fname)))
        #head, fn = os.path.split(fname)

if __name__ == '__main__':
    op = OptionParser()
    op.add_option("--workers", action="store", type="int", default=2)
    op.add_option("--pattern", action="store", default="/home/OTUS/homeworks/dz9/tsv/*.tsv.gz")
    op.add_option("--idfa", action="store", default="127.0.0.1:13305")
    op.add_option("--gaid", action="store", default="127.0.0.1:13306")
    op.add_option("--adid", action="store", default="127.0.0.1:13307")
    op.add_option("--dvid", action="store", default="127.0.0.1:13308")
    (opts, args) = op.parse_args()

    print("Memc loader started with options: {}".format(opts))
    try:
        main(opts)
    except Exception as e:
        print("Unexpected error:{}".format(str(e)))
        sys.exit(1)
