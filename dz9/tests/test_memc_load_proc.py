import unittest
import logging
from memc_load_proc import Worker
from memc_load_proc import MemcacheClient

class Memc_loader(unittest.TestCase):

    def setUp(self):
        pass
    def tearDown(self):
        pass

    def test_worker_fileread(self):

        device_memc = {
            "idfa": "127.0.0.1:13305",
            "gaid": "127.0.0.1:13306",
            "adid": "127.0.0.1:13307",
            "dvid": "127.0.0.1:13308",
        }
        wc = Worker(device_memc, False, 2, 0.1, 5)
        #file not found
        wc.starter('aaaaaa.gz')
        #file without .gz
        wc.starter('aaaaaa.tsv')

    def test_memcclient_upload(self):
        #simple test for insert
        msg = {'key': "{0:b}".format(42), 'val': '{} forty two'.format(str(42))}
        mc = MemcacheClient("127.0.0.1:13305", 10, 3)
        mc.set(msg)
        mc.get("{0:b}".format(42))
        mc.start()

    def test_memcclient_notbinary(self):
        #simple test for insert not binary key
        msg = {'key': 42, 'val': '{} forty two'.format(str(42))}
        mc = MemcacheClient("127.0.0.1:13305", 10, 3)
        mc.set(msg)
        mc.start()


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr)
    logging.getLogger("SomeTest.testSomething").setLevel(logging.DEBUG)
    unittest.main()