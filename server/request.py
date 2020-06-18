""" 解析请求 """

from server.utils import Headers

__all__ = ['Request']


class Request:
    encoding = 'latin-1'

    def __init__(self):
        self.method = None
        self.path = None
        self.query_string = None
        self.version = None
        self.header = Headers()
        self.body = None
        self._request_line = None

    @classmethod
    def execute(cls, sock):
        """ :param sock:套接字对象 """
        fp = sock.makefile('rb')
        self = cls()
        request_line = str(fp.readline(), cls.encoding)
        self._request_line = request_line.rstrip()

        lst = []
        for line in fp:
            if line == b'\r\n':
                break
            lst.append(line)

        headers = ''.join(map(lambda x: x.decode(cls.encoding), lst))

        self.parse_request_line(request_line)
        self.parse_headers(headers)
        return self

    def parse_request_line(self, line):
        """:param line: "method, path, version" """
        self.method, full_path, *rest = line.split(' ')
        query_list = full_path.split('?', 1)
        self.path = query_list[0]

        if len(query_list) == 2:
            self.query_string = query_list[1]

        self.version = ''.join(rest).strip()

    def parse_headers(self, headers):
        """ :param  headers: "name-1: value-1\r\nname-2: value-2\r\n..." """
        items = headers.split('\r\n')[:-1]
        for kv in items:
            k, v = kv.split(': ', 1)
            self.header.add_header(k, v)

    def parse_body(self, body):
        """ :param :body string
        不解析，留给 application 处理"""
        self.body = body

    def __repr__(self):
        return f'<{self.__class__.__name__} {self._request_line}>'
