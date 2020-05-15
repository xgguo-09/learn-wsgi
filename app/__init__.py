from .request import Request


def app(environ, start_response):
    req = Request(environ)
    status = '200 OK'
    response_headers = [('Content-type', 'text/plain')]
    start_response(status, response_headers)
    return [b'Hello word!']
