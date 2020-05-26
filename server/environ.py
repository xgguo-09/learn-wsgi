import os
import sys

__all__ = ['setup_environ']


OS_ENVIRON = os.environ


CGI_ENVIRON = {
    'REQUEST_METHOD': '',
    'SCRIPT_NAME': '',     # CGI脚本名字
    'PATH_INFO': '',       # CGI脚本程序附加路径
    'QUERY_STRING': '',    # d=1&q=1
    'CONTENT_TYPE': '',
    'CONTENT_LENGTH': '',
    'SERVER_PROTOCOL': '',
    'SERVER_NAME': '',
    'SERVER_PORT': '',
}


WSGI_ENVIRON = {
    'wsgi.version': (1, 0),
    'wsgi.multithread': True,
    'wsgi.multiprocess': False,
    'wsgi.run_once': False,
    'wsgi.url_scheme': '',
    'wsgi.input': '',
    'wsgi.errors': sys.stderr,
}


def setup_environ(request, server):
    header = request.header
    env = {}
    env.update(OS_ENVIRON)
    env.update(CGI_ENVIRON)
    env.update(WSGI_ENVIRON)

    env['wsgi.input'] = ''
    env['wsgi.url_scheme'] = 'http'
    env['REQUEST_METHOD'] = request.method
    env['PATH_INTO'] = request.path
    env['QUERY_STRING'] = request.query_string
    env['SERVER_PROTOCOL'] = request.version
    env['SERVER_NAME'] = server.server_address[0]
    env['SERVER_PORT'] = server.server_address[1]

    for k, v in header:
        k = k.upper().replace("-", "_")
        if k not in ("CONTENT_TYPE", "CONTENT_LENGTH"):
            k = f"HTTP_{k}"
            if k in env:
                v = f'{env[k]},{v}'
        env[k] = v

    return env
