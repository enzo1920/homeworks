#!/usr/bin/python


class HttpRequest(object):
    def __init__(self):
        self.data = ''
        self.method = None
        self.uri = None
        self.headers = {}
        self.is_valid = None
        self.is_ready = False

    def add_data(self, data):
        self.data += data
        index = self.data.find('\r\n\r\n')
        if index != -1:
            try:
                self.parse_data(self.data[:index])
                self.is_valid = True
            except:
                self.is_valid = False
            self.is_ready = True
        #print(self.data)

    def parse_data(self, data):
        lines = data.split('\r\n')
        self.method, self.uri, ver = lines[0].split(' ')
        for line in lines[1:]:
            name, value = line.split(':', 1)
            self.headers[name.strip()] = value.strip()
