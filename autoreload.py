__all__ = ['execute']

import os
import sys
import time
import _thread
import subprocess

from server.utils import log

# 记录变化的文件名
_changed_filename = None

# 子进程
_sub_p = None


def _iter_module_files():
    """获取所有导入的模块文件"""
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            if filename[-4:] in ('.pyo', '.pyc'):
                filename = filename[:-1]
            yield filename


def _is_any_file_changed(mtimes):
    """有任何文件改动则返回 True
    :param mtimes 是个字典"""

    global _changed_filename

    for filename in _iter_module_files():
        try:
            mtime = os.stat(filename).st_mtime
        except IOError:
            continue
        old_time = mtimes.get(filename, None)
        if old_time is None:
            mtimes[filename] = mtime
        elif mtime > old_time:
            _changed_filename = filename
            return 1
    return 0


def _reload():
    global _sub_p
    if _sub_p:
        _sub_p.terminate()
    cmd = [sys.executable] + sys.argv
    # 启动一个新子进程
    _sub_p = subprocess.Popen(cmd)


def _observe():
    mtimes = {}
    while True:
        if _is_any_file_changed(mtimes):
            log(f'Changed {_changed_filename}')
            try:
                _reload()
            finally:
                sys.exit(0)
        time.sleep(1)


def execute(func, *args, **kwargs):
    try:
        if kwargs.get('debug', None):
            # 创建守护线程
            _thread.start_new_thread(func, args, kwargs)
            # 开启主线程循环
            _observe()
        else:
            func(*args, **kwargs)
    except KeyboardInterrupt:
        sys.exit(0)
