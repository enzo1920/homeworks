#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import gzip
import sys
import gzip
import glob
import Queue
import logging
import datetime
import threading
import collections
from optparse import OptionParser
# brew install protobuf
# protoc  --python_out=. ./appsinstalled.proto
# pip install protobuf
#import appsinstalled_pb2
# pip install python-memcached
#import memcache

NORMAL_ERR_RATE = 0.01
AppsInstalled = collections.namedtuple("AppsInstalled", ["dev_type", "dev_id", "lat", "lon", "apps"])
#Number of threads
NUM_THREADS = 6


CONFIG = {
    "TRIES": 4,
    "SOCKET_TIMEOUT": 2,
    "NORMAL_ERR_RATE": 0.01,
}



class MemcacheClient(threading.Thread):

    def __init__(self, addr):
        super(MemcacheClient, self).__init__()
        self.daemon = True
        self.queue = Queue()
        self.addr = addr
        self.errors = 0

    def set(self, msg):
        self.queue.put(msg)

    def try_to_stop(self):
        self.queue.put(None)

    def run(self):
        client = memcache.Client([self.addr],socket_timeout=CONFIG["SOCKET_TIMEOUT"])
        while True:
            msg = self.queue.get()
            if msg is None:
                break
            ok = client.set(msg['key'], msg['data'])
            for _ in xrange(3):
                if ok:
                    break
                ok = client.set(msg['key'], msg['data'])
            if not ok:
                self.errors += 1



class Worker(object):
    def __init__(self, device_memc, dry, fname):
        self.device_memc = device_memc
        self.dry = dry
        self.fname = fname


    def getName(self):
        return self.__class__.__name__

    def process_file_grabber(self):
        logging.info('Process {}  work with file').format(self.getName(),self.fname)

        processed = errors = 0
        memclients = {}
        for devtype, addr in self.devtype2addr.items():
            mc = MemcacheClient(addr)
            mc.start()
            memclients[devtype] = mc

        with gzip.open(fn) as fd:
        for line in fd:
            line = line.strip()
            if not line:
                continue
                appsinstalled = self.parse_appsinstalled(self.fname, line)
            if not appsinstalled:
                errors += 1
                continue
            mc = memclients.get(appsinstalled.dev_type)
            if not mc:
                errors += 1
                logging.error("{} unknow device type: {} in file {}".format(self.getName(),appsinstalled.dev_type, self.fname))
                continue
            chunk = self.memc_serialyzer(appsinstalled)
            if chunk:
                processed += 1
            else:
                errors += 1
            if self.dry:
                logging.debug("{} work with {}: {}".format (fname, str(chunk)))
            else:
                mc.set(chunk)

        for mc in memclients.values():
            mc.try_to_stop()
            mc.join()
            errors += mc.errors

        err_rate = float(errors) / processed
#config!!!!
        if err_rate < NORMAL_ERR_RATE:
            logging.info("File {} acceptable error rate {}. Successfull load".format(fname, err_rate))
        else:
            logging.error("File {}. err_rate is high {} > {}. Failed load".format(fname, err_rate, NORMAL_ERR_RATE))
        return fname


    def memc_serialyzer(self, appsinstalled):
        ua = appsinstalled_pb2.UserApps()
        ua.lat = appsinstalled.lat
        ua.lon = appsinstalled.lon
        key = "{}:{}".format(appsinstalled.dev_type, appsinstalled.dev_id)
        ua.apps.extend(appsinstalled.apps)
        packed = ua.SerializeToString()
        return {'key': key, 'val': packed}

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
            logging.info("Not all user apps are digits: `{}`") % line)
        try:
            lat, lon = float(lat), float(lon)
        except ValueError:
            logging.info("Invalid geo coords: `%s`" % line)
        return AppsInstalled(dev_type, dev_id, lat, lon, apps)


def dot_rename(path):
    head, fn = os.path.split(path)
    # atomic in most cases
    os.rename(path, os.path.join(head, "." + fn))



'''
    try:
        if dry_run:
            logging.debug("%s - %s -> %s" % (memc_addr, key, str(ua).replace("\n", " ")))
        else:
            memc = memcache.Client([memc_addr])
            memc.set(key, packed)
    except Exception, e:
        logging.exception("Cannot write to memc %s: %s" % (memc_addr, e))
        return False
    return True
'''




def main(options):
    device_memc = {
        "idfa": options.idfa,
        "gaid": options.gaid,
        "adid": options.adid,
        "dvid": options.dvid,
    }





def prototest():
    sample = "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23\ngaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424"
    for line in sample.splitlines():
        dev_type, dev_id, lat, lon, raw_apps = line.strip().split("\t")
        apps = [int(a) for a in raw_apps.split(",") if a.isdigit()]
        lat, lon = float(lat), float(lon)
        ua = appsinstalled_pb2.UserApps()
        ua.lat = lat
        ua.lon = lon
        ua.apps.extend(apps)
        packed = ua.SerializeToString()
        unpacked = appsinstalled_pb2.UserApps()
        unpacked.ParseFromString(packed)
        assert ua == unpacked


if __name__ == '__main__':
    op = OptionParser()
    op.add_option("-t", "--test", action="store_true", default=False)
    op.add_option("-l", "--log", action="store", default=None)
    op.add_option("--dry", action="store_true", default=False)
    #op.add_option("--pattern", action="store", default="/data/appsinstalled/*.tsv.gz")
    op.add_option("--pattern", action="store", default="/home/OTUS/homeworks/dz9/*.tsv.gz")
    op.add_option("--idfa", action="store", default="127.0.0.1:33013")
    op.add_option("--gaid", action="store", default="127.0.0.1:33014")
    op.add_option("--adid", action="store", default="127.0.0.1:33015")
    op.add_option("--dvid", action="store", default="127.0.0.1:33016")
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO if not opts.dry else logging.DEBUG,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    if opts.test:
        prototest()
        sys.exit(0)

    logging.info("Memc loader started with options: %s" % opts)
    try:
        main(opts)
    except Exception, e:
        logging.exception("Unexpected error: %s" % e)
        sys.exit(1)
