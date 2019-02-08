#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import gzip
import sys
import gzip
import glob
import logging
import time
import datetime
import argparse
import threading
import collections
from itertools import chain
from multiprocessing import Queue as queue
from multiprocessing import Pool, cpu_count
# brew install protobuf
# protoc  --python_out=. ./appsinstalled.proto
# pip install protobuf
import appsinstalled_pb2
# pip install python-memcached
import memcache

# NORMAL_ERR_RATE = 0.01
AppsInstalled = collections.namedtuple("AppsInstalled", ["dev_type", "dev_id", "lat", "lon", "apps"])

CONFIG = {
    "TRIES": 4,
    "SOCKET_TIMEOUT": 15,
    "NORMAL_ERR_RATE": 0.01,
}


class MemcacheClient(threading.Thread):
    def __init__(self, addr, timeout, tries):
        super(MemcacheClient, self).__init__()
        self.daemon = True
        self.queue = queue()
        self.addr = addr
        self.timeout = timeout
        self.tries = tries
        self.errors = 0
        self.client = memcache.Client([self.addr], socket_timeout=self.timeout)

    def get(self, key):
        return self.client.get(key)

    def set(self, msg):
        self.queue.put(msg)

    def try_to_stop(self):
        self.queue.put(None)

    def run(self):

        while True:
            msg = self.queue.get()
            if msg is None:
                break
            try:
                #return: List of keys which failed to be stored
                ret_list = self.client.set_multi(msg)
                for _ in range(self.tries):
                    if not ret_list:
                        break
                    ret_list = self.client.set_multi(msg)
                if ret_list:
                    self.errors += 1
                    logging.error("client insert err, not ok ")
            except Exception as ex:
                logging.error("Error: {} . memc set".format(str(ex)))


class Worker(object):
    def __init__(self, device_memc, dry, tries, norm_err_rate, sock_timeout, buffer_portion):
        self.device_memc = device_memc
        self.dry = dry
        self.norm_err_rate = norm_err_rate
        self.tries = tries
        self.buffer_portion = buffer_portion
        self.sock_timeout = sock_timeout

    def openfile(self, filename):
        if not os.path.isfile(filename):
            logging.error(" file: {} not found".format(filename))
        if filename.endswith('.gz'):
            return gzip.open(filename, 'rb')
        else:
            return open(filename, 'rb')

    def starter(self, fname):

        logging.info('Process {}  work with file'.format(fname))
        processed = errors = 0
        buffer = {}
        memclients = {}
        for devtype, addr in self.device_memc.items():
            mc = MemcacheClient(addr, self.sock_timeout, self.tries)
            mc.setName(str(devtype))
            mc.start()
            memclients[devtype] = mc
            dict_dev = devtype
            dict_dev = {}
            buffer[devtype] = dict_dev

            logging.info('Proc is {} mmc_thread {} '.format(str(os.getpid()), str(mc.getName())))
        try:
            with self.openfile(fname) as fd:
                for line in fd:
                    line = line.decode().strip()
                    if not line:
                        continue
                    appsinstalled = self.parse_appsinstalled(line)
                    if not appsinstalled:
                        errors += 1
                        logging.error(" not appsinstalled: {} in file {}".format(line, fname))
                        continue
                    mc = memclients.get(appsinstalled.dev_type)
                    dict_dev_type = buffer.get(appsinstalled.dev_type)
                    if not mc:
                        errors += 1
                        logging.error(" unknow device type: {} in file {}".format(appsinstalled.dev_type, fname))
                        continue
                    key, packed = self.memc_serialyzer(appsinstalled)
                    if key:
                        processed += 1
                        dict_dev_type[key] = packed
                    else:
                        errors += 1
                        logging.error(" memc_serialyzer: {} in file {}".format(line, fname))
                    if self.dry:
                        logging.debug("{} work with {}: {}".format(fname, str(chunk)))
                    else:
                        if len(dict_dev_type) == self.buffer_portion:
                            mc.set(dict_dev_type)
                            dict_dev_type.clear()

                for mc in memclients.values():
                    mc.try_to_stop()
                    mc.join()
                    errors += mc.errors
            if processed == 0:
                logging.info(" wrong file {} ".format(fname))
                err_rate = 0
            else:
                err_rate = float(errors) / processed
            if err_rate < self.norm_err_rate:
                logging.info("File {} acceptable error rate {}. Successfull load".format(fname, err_rate))
            else:
                logging.error("File {}. err_rate is high {} > {}. Failed load".format(fname, err_rate, self.norm_err_rate))
            return fname
        except IOError:
            logging.error("File {} not found".format(fname))
            return

    def memc_serialyzer(self, appsinstalled):
        ua = appsinstalled_pb2.UserApps()
        ua.lat = appsinstalled.lat
        ua.lon = appsinstalled.lon
        key = "{}:{}".format(appsinstalled.dev_type, appsinstalled.dev_id)
        ua.apps.extend(appsinstalled.apps)
        packed = ua.SerializeToString()
        return  key, packed

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
            logging.info("Not all user apps are digits: `{}`".format(line))
        try:
            lat, lon = float(lat), float(lon)
        except ValueError:
            logging.info("Invalid geo coords: `%s`" % line)
        return AppsInstalled(dev_type, dev_id, lat, lon, apps)


def dot_rename(path):
    head, fn = os.path.split(path)
    # atomic in most cases
    os.rename(path, os.path.join(head, "." + fn))


def config_reader(config_dict):
    config_tuple = collections.namedtuple('config_tuple', ['tries', 'sock_timeout', 'norm_err_rate'])
    config = config_tuple(config_dict["TRIES"], config_dict["SOCKET_TIMEOUT"],
                          config_dict["NORMAL_ERR_RATE"])
    return config


def main(options, config):
    device_memc = {
        "idfa": options.idfa,
        "gaid": options.gaid,
        "adid": options.adid,
        "dvid": options.dvid,
    }
    wc = Worker(device_memc, options.dry, config.tries, config.norm_err_rate, config.sock_timeout, options.flush_threshold)
    fnames = glob.glob(options.pattern)
    fnames = sorted(fnames)
    for fname in Pool(options.workers).imap(wc.starter, fnames):
        dot_rename(fname)


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
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--test", action="store_true", default=False)
    parser.add_argument("-l", "--log", action="store", default="memc_proc.log")
    parser.add_argument("--dry", action="store_true", default=False)
    parser.add_argument("--workers", action="store", default=2)
    parser.add_argument("-b", "--flush_threshold", action="store", default=10)
    #parser.add_argument("--pattern", action="store", default="/data/appsinstalled/*.tsv.gz")
    parser.add_argument("--pattern", action="store", default="/home/OTUS/homeworks/dz9/tsv/*.tsv.gz")
    parser.add_argument("--idfa", action="store", default="127.0.0.1:13305")
    parser.add_argument("--gaid", action="store", default="127.0.0.1:13306")
    parser.add_argument("--adid", action="store", default="127.0.0.1:13307")
    parser.add_argument("--dvid", action="store", default="127.0.0.1:13308")
    args = parser.parse_args()

    logging.basicConfig(filename=args.log, level=logging.INFO if not args.dry else logging.DEBUG,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    cfg = config_reader(CONFIG)
    if args.test:
        prototest()
        sys.exit(0)

    logging.info("Memc loader started with options: %s" % args)
    try:
        main(args, cfg)
    except Exception as e:
        logging.exception("Unexpected error: %s" % e)
        sys.exit(1)
