from server import make_server, RequestsHandler
from app import app
from autoreload import execute


def main():
    config = {
        'host': '127.0.0.1',
        'port': 3000,
        'HandlerClass': RequestsHandler,
        'debug': True,
        'app': app,
    }
    execute(make_server, **config)


if __name__ == '__main__':
    main()
