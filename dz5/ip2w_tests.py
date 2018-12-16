#!/usr/bin/env python

import httplib
import unittest


class Ip2w_tester(unittest.TestCase):
    host = "194.48.97.234"
    port = 8080

    def setUp(self):
        self.conn = httplib.HTTPConnection(self.host, self.port, timeout=10)

    def tearDown(self):
        self.conn.close()

    def test_empty_ip(self):
        """Send empty IP (server must take it from headers)"""
        self.conn.request("GET", "/")
        r = self.conn.getresponse()
        self.assertIn(int(r.status), [200, 400])

    def test_bad_ip(self):
        """Send malformed IP"""
        self.conn.request("GET", "/bad_ip")
        r = self.conn.getresponse()
        self.assertEqual(int(r.status), 400)

    def test_long_path(self):
        """Send URL with large level of nesting"""
        self.conn.request("GET", "/188.227.18.141/subdir/subdir")
        r = self.conn.getresponse()
        self.assertEqual(int(r.status), 400)

    def test_reserved_ip(self):
        """Send IP from reserved range"""
        self.conn.request("GET", "/127.0.0.1")
        r = self.conn.getresponse()
        self.assertEqual(int(r.status), 500)

    def test_good_ip(self):
        """Send good IP"""
        self.conn.request("GET", "/188.227.18.141")
        r = self.conn.getresponse()
        self.assertEqual(int(r.status), 200)


loader = unittest.TestLoader()
suite = unittest.TestSuite()
a = loader.loadTestsFromTestCase(Ip2w_tester)
suite.addTest(a)


class NewResult(unittest.TextTestResult):
    def getDescription(self, test):
        doc_first_line = test.shortDescription()
        return doc_first_line or ""


class NewRunner(unittest.TextTestRunner):
    resultclass = NewResult


runner = NewRunner(verbosity=2)
runner.run(suite)
