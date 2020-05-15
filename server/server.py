"""简单的 WEB 服务器, 符合 WSGI 接口规范"""

import socket
import selectors
import threading

from .utils import logged

# windows 系统没有 PollSelector
if hasattr(selectors, 'PollSelector'):
    _ServerSelector = selectors.PollSelector
else:
    _ServerSelector = selectors.SelectSelector


class BaseServer:
    request_queue_size = 128
    timeout = None

    def __init__(self, host, port, HandlerClass, *args, **kwargs):
        self.HandlerClass = HandlerClass
        self.server_address = (host, port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 设置端口马上复用
        # 端口被 socket 使用过，执行 socket.close() 关闭连接后，但此时端口还没有释放
        # 需要经过一个 TIME_WAIT 过程后才能使用， setsockopt() 可设置立即使用
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)
        self.socket.listen(self.request_queue_size)

        # Event 是线程同步对象，内部标志默认是 False
        # Event.clear() 恢复初始化，标志置为 False
        # Event.wait() 一直阻塞线程直到标志变为 True
        # Event.set() 把内部标志置为 True
        self.__is_shut_down = threading.Event()
        self.__shutdown_request = False

    def run(self, poll_interval=0.5):
        """启动服务
        :param poll_interval 轮询间隔事件，单位秒
        """
        self.__is_shut_down.clear()
        try:
            with _ServerSelector() as selector:
                # 套接字注册一个读事件
                selector.register(self.socket.fileno(), selectors.EVENT_READ)

                while not self.__shutdown_request:
                    ready = selector.select(poll_interval)
                    # 关闭请求立即退出
                    if self.__shutdown_request:
                        break
                    if ready:
                        # 套接字可读，开始接受并处理请求
                        self.process_request(*self.socket.accept())
        finally:
            self.__shutdown_request = False
            self.__is_shut_down.set()

    def shutdown(self):
        """停止服务"""
        self.__shutdown_request = True
        self.__is_shut_down.wait()

    def process_request(self, request, client_address):
        """  MinIn子类复写 """
        self.HandlerClass(request, client_address, self)

    def server_close(self):
        self.socket.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.server_close()


class ThreadingMixIn:
    """MixIn 模式"""
    # 每个请求默认设置为守护线程, 进程退出时不等待每个子线程就结束
    # 由于服务器是个死循环，所以主线程(进程）是不会退出的
    daemon_threads = True
    # 进程退出时，不等待立即结束
    block_on_close = False

    _threads = None

    def process_request_thread(self, request, client_address):
        self.HandlerClass(request, client_address, self)

    @logged('Connected')
    def process_request(self, request, client_address):
        """Start a new thread to process the request."""
        t = threading.Thread(target=self.process_request_thread,
                             args=(request, client_address))
        t.daemon = self.daemon_threads
        if not t.daemon and self.block_on_close:
            if self._threads is None:
                self._threads = []
            self._threads.append(t)
        t.start()

    @logged('Server closed')
    def server_close(self):
        super().server_close()
        if self.block_on_close:
            # 如果为设置为非守护线程，则阻塞等待子线程
            threads = self._threads
            self._threads = None
            if threads:
                for thread in threads:
                    # 子线程加入主线程，阻塞等待每个线程结束
                    thread.join()


class WSGIServer(ThreadingMixIn, BaseServer):
    """继承 ThreadingMixIn, BaseServer"""
    def __init__(self, host, port, HandlerClass, app, *args, **kwargs):
        super().__init__(host, port, HandlerClass)
        self.app = app


@logged('Running on')
def make_server(**options):
    with WSGIServer(**options) as httpd:
        httpd.run()
