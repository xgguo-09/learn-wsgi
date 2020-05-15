"""Request类，从 WSGI 服务器拿到请求并解析"""

from urllib.parse import unquote, quote
from http.cookiejar import split_header_words

from server.utils import Headers, cache_property


class Request:
    def __init__(self, environ):
        self.environ = environ

    def __repr__(self):
        return f'<{type(self).__name__}: {self.method} {self.url}>'

    @cache_property
    def headers(self):
        return self._initiate_headers()

    def _initiate_headers(self):
        headers = Headers()

        def repair(k):
            k.replace("_", "-").title()

        for key, value in self.environ.items():
            if key in ("CONTENT_TYPE", "CONTENT_LENGTH") and value:
                headers.add_header(repair(key), value)

            elif key.startswith("HTTP_") and key:
                headers.add_header(repair(key[5:]), value)
            headers.add_header(key, value)

        return headers

    def cookies(self):
        cookies_header = (self.environ.get('HTTP_COOKIE', '')).values()
        cookies = split_header_words(cookies_header)
        return cookies

    def form(self):
        pass

    def params(self):
        pass

    def body(self):
        read_func = self.environ['wsgi.input'].read

    def files(self):
        pass

    @cache_property
    def method(self):
        return self.environ.get('REQUEST_METHOD', 'GET').upper()

    @property
    def scheme(self):
        return self.environ.get('wsgi.url_scheme', 'http')

    @cache_property
    def host(self):
        host = self.headers.get('host', None)
        assert (host is not None and host), ValueError('Host error')
        return host

    @cache_property
    def path(self):
        path = self.environ.get('PATH_INFO', '/')
        return '/' + path.lstrip('/')

    @cache_property
    def full_path(self):
        return f'{self.path}?{self.query_string}'

    @cache_property
    def base_url(self):
        return f'{self.scheme}://{self.host}{self.path}'

    @cache_property
    def url(self):
        return quote(f'{self.scheme}://{self.host}{self.full_path}')

    @cache_property
    def script_name(self):
        name = self.environ.get('SCRIPT_NAME', '')
        return '/' + name if name else '/'

    @property
    def query_string(self):
        return self.environ.get('QUERY_STRING', '')

    @cache_property
    def query(self):
        q = {}
        query_string = self.query_string
        if query_string == '' or query_string is None:
            return q

        for pair in query_string.split(';'):
            if not pair:
                continue

            kv_list = pair[:].split('=', 1)
            if len(kv_list) == 2:
                key = unquote(kv_list[0].replace('+', ' '))
                value = unquote(kv_list[1].replace('+', ' '))
                q[key] = value
        return q

    @property
    def remote_addr(self):
        return self.environ.get("REMOTE_ADDR")
