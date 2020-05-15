""" 请求处理 """

import time
from io import BufferedIOBase

from server.environ import setup_environ
from server.request import Request
from server.utils import logged, log, Headers, format_date_time


class _SocketWriter(BufferedIOBase):
    """接受一个套接字对象"""

    def __init__(self, sock):
        self._sock = sock

    def writable(self):
        return True

    def write(self, b):
        self._sock.sendall(b)
        with memoryview(b) as view:
            return view.nbytes

    def fileno(self):
        return self._sock.fileno()

    def flush(self):
        """"直接写入内存试图，不用调用刷新 flush"""
        pass


class RequestsHandler:
    timeout = 3  # 套接字超时
    headers_class = Headers
    headers = None  # http headers
    headers_sent = None  # 是否发送 header 标志
    status = None  # app 响应状态码， app 是否响应标志
    bytes_sent = None  # 已发送字节大小
    app_result = None  # app 返回的 body

    def __init__(self, connection, client_address, server):
        self.conn = connection
        self.conn.settimeout(self.timeout)
        self.client_address = client_address
        self.server = server
        self.app = self.server.app
        self._wfile = _SocketWriter(self.conn)
        self.request = None
        self.env = None

        try:
            self.setup()
            self.handle()
        finally:
            self.finish()

    def setup(self):
        self.request = Request.execute(self.conn)
        self.env = setup_environ(self.request, self.server)
        self.env['wsgi.input'] = self.conn.makefile('rb')

    def handle(self):
        log(self.request)
        self.run_wsgi()

    def run_wsgi(self):
        """WSGI 服务器调用 application 响应客户端请求"""
        self.app_result = self.app(self.env, self.start_response)
        self.finish_response()

    def start_response(self, status, response_headers, exc_info=None):
        """WSGI 服务器需要实现 `start_response`方法被 application 调用"""
        if exc_info:
            try:
                if self.headers_sent:
                    # 触发错误如果 app 未响应前已发送数据
                    raise exc_info[0](exc_info[1]).with_traceback(exc_info[2])
            finally:
                exc_info = None
        elif self.headers is not None:
            #  app 未响应前 self.headers 应该为空
            raise AssertionError("Headers already set!")

        assert isinstance(status, str), '`status` must be a str instance'
        self.status = status  # 供写入时 write() 判断使用
        self.headers = self.headers_class(response_headers)
        return self.write

    def finish_response(self):
        try:
            for data in self.app_result:
                self.write(data)

            if not self.headers_sent:
                self.headers.setdefault('Content-Length', "0")
                self.send_headers()
            else:
                pass  # XXX check if content-length was too short?
        except Exception:
            if hasattr(self.app_result, 'close'):
                self.app_result.close()
            raise

    def set_content_length(self):
        """设置 `Content-Length`大小， pep3333 规定如下：

        app 调用 `start_response` 后, 如果返回一个 len() 值为 1 的可迭代对象
        那么 WSGI 服务器端就可以自行通过可迭代对象生成的第一个 bytestring 字符串
        来得到这个 Content-Length 的值。
        """
        if 'Content-Length' in self.headers:
            return
        try:
            blocks = len(self.app_result)
        except (TypeError, AttributeError, NotImplementedError):
            pass
        else:
            if blocks == 1:
                self.headers['Content-Length'] = str(self.bytes_sent)
                return

        # TODO：支持 http chunk 数据传输

    def send_response_line(self):
        response_line = f'HTTP/1.1 {self.status}\r\n'
        log(f'<Response {response_line.strip()}>')
        self._write(response_line.encode('latin-1'))

    def send_headers(self):
        self.set_content_length()
        self.headers_sent = True
        self.send_response_line()

        if 'Date' not in self.headers:
            fmt_time = format_date_time(time.time())
            self._write(f'Date: {fmt_time}\r\n'.encode('latin-1'))

        self._write(bytes(self.headers))

    def write(self, data):
        """:param data: 必须是 bytes 类型"""
        assert isinstance(data, bytes), '`write(data) data must be a bytes'

        if not self.status:
            # 表示 app 还没响应，禁止发送数据
            raise AssertionError('write(data) before `start_response`')

        elif not self.headers_sent:
            # 发送 app body 数据之前需要先发送 headers
            self.bytes_sent = len(data)  # 计算已发送字节大小 (headers)
            self.send_headers()

        else:
            # 计算已发送字节大小 (headers+body)
            self.bytes_sent += len(data)

        self._write(data)
        self._flush()

    def _write(self, data):
        """写入套接字, 真正发送数据的接口"""
        data_length = self._wfile.write(data)
        if data_length is None or data_length == len(data):
            # 表示数据为空，或者已经全部写入了缓冲
            return
        else:
            # 输出警告，不建议分片写入
            from warnings import warn
            warn("write() should not do partial writes", DeprecationWarning)

            while True:
                data = data[data_length:]
                if not data:
                    break
                data_length = self._wfile.write(data)

    def _flush(self):
        self._wfile.flush()

    @logged('Connection closed')
    def finish(self):
        self.app_result = self.headers = self.status = self.env = None
        self.bytes_sent = 0
        self.headers_sent = False
        self.conn.close()
