"""Request类，从 WSGI 服务器拿到请求并解析"""

from urllib.parse import unquote, quote
from io import BytesIO

from server.utils import Headers, cache_property, log


class Request:
    MEMFILE_MAX = 102400  # 内存最大缓存100k
    headers_cls = Headers

    def __init__(self, environ):
        self.environ = environ

    def __repr__(self):
        return f'<{type(self).__name__}: {self.method} {self.url}>'

    @cache_property
    def headers(self):
        return self._initiate_headers()

    @cache_property
    def cookies(self):
        return self._parse_cookies()

    @property
    def body(self):
        fp = self._body
        fp.seek(0)
        return fp

    def files(self):
        pass

    @cache_property
    def form(self):
        return self._parse_form()

    @cache_property
    def params(self):
        params = self.query.copy()
        params.update(self.form)
        return params

    @cache_property
    def method(self):
        return self.environ.get('REQUEST_METHOD', 'GET').upper()

    @property
    def scheme(self):
        return self.environ.get('wsgi.url_scheme', 'http')

    @cache_property
    def host(self):
        host = self.headers.get('Host', None)
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

    @cache_property
    def content_type(self):
        return self._parse_content_type()

    @cache_property
    def content_encoding(self):
        return self.content_type.get('charset', 'utf-8')

    def _initiate_headers(self):
        headers = self.headers_cls()

        def repair(k):
            return k.replace("_", "-").title()

        for key, value in self.environ.items():
            if key in ("CONTENT_TYPE", "CONTENT_LENGTH") and value:
                key = repair(key)

            if key.startswith("HTTP_") and key:
                key = repair(key[5:])

            headers.add_header(key, value)

        return headers

    def _parse_cookies(self):
        cookies = {}
        cookies_str = self.environ.get('HTTP_COOKIE', None)

        if cookies_str is not None:
            param_lst = cookies_str.split(';')
            for param in param_lst:
                param = param.strip()
                k, v = param.split('=', 1)
                k, v = k.strip(), v.strip()
                cookies[k] = v

        return cookies

    @cache_property
    def _body(self):
        input_stream = self.environ.get('wsgi.input', BytesIO())
        buffer = BytesIO()
        try:
            content_length = int(self.environ.get('CONTENT_LENGTH'))
        except ValueError:
            content_length = 0

        read_size = min(4096, content_length)

        if 'chunked' in self.environ.get('HTTP_TRANSFER_ENCODING', '').lower():
            log('Not supported chunked file upload')
            return
            # TODO: 处理 chunk 数据

        buffer.write(input_stream.read(read_size))
        pos = buffer.tell()
        while pos < content_length and pos < self.MEMFILE_MAX:
            buffer.write(input_stream.read(read_size))
            pos = buffer.tell()

        buffer.flush()

        return buffer

    def _parse_content_type(self):
        content_type = {}
        content = self.environ.get('CONTENT_TYPE', '').lower()
        mime_type, *options = content.split(';')

        content_type['mime_type'] = mime_type.strip()

        if options:
            for opt in options:
                k, v = opt.split('=')
                k, v = k.strip(), v.strip()
                content_type[k] = v

        return content_type

    def _parse_form(self):
        forms = {}
        mime_type = self.content_type.get('mime_type')
        forms_str = self.body.read().decode(self.content_encoding)

        if (self.method == 'POST'
                and mime_type == 'application/x-www-form-urlencoded'
        ):
            param_lst = forms_str.split('&')
            for param in param_lst:
                k, v = param.split('=')
                k, v = k.strip(), v.strip()
                forms[k] = v

        return forms
