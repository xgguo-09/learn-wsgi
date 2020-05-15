import functools
from time import ctime, gmtime
from os.path import dirname, abspath, join

cur_dir = abspath(dirname(__name__))


def log(*args, **kwargs):
    """ 日志打印，同时保存至文件中 """
    curr_time = ctime()
    print(curr_time, *args, **kwargs)
    with open(join(cur_dir, 'server-run.log'), 'a+') as f:
        print(curr_time, *args, **kwargs, file=f)


def logged(message=None):
    """ 装饰器，函数执行前加上消息日志 message """
    def log_wrapper(func):
        m = message
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if m == 'Connected':
                log(m, args[-1])
            elif m == 'Running on':
                log(m, f"http://{kwargs.get('host')}:{kwargs.get('port')}")
            else:
                log(m)
            return func(*args, **kwargs)

        return wrapper

    return log_wrapper


def _to_string(value):
    if isinstance(value, bytes):
        value = value.decode("latin-1")
    if not isinstance(value, str):
        value = str(value)
    return value


_weekdayname = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_monthname = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def format_date_time(timestamp):
    year, month, day, hh, mm, ss, wd, y, z = gmtime(timestamp)
    return "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
        _weekdayname[wd], day, _monthname[month], year, hh, mm, ss
    )


class Headers:
    """响应头数据结构，实现了类似字典的操作接口，可添加相同的键。

    Headers -> [(key-1, value-1), (key-2, value-2)...]
    """

    def __init__(self, headers=None):
        headers = headers if headers is not None else []
        if not isinstance(headers, list):
            raise TypeError("Headers must be a list of name/value tuples")
        self._headers = headers

    def __len__(self):
        return len(self._headers)

    def __str__(self):
        return '\r\n'.join(["%s: %s" % kv for kv in self._headers] + ['', ''])

    def __repr__(self):
        return f'{self.__class__.__name__}({self._headers})'

    def __bytes__(self):
        return str(self).encode('latin-1')

    def __contains__(self, name):
        return self.get(name) is not None

    def __iter__(self):
        return iter(self._headers)

    def __getitem__(self, name):
        iname = _to_string(name).lower()
        for k, v in self._headers:
            if k.lower() == iname:
                return v

    def __setitem__(self, name, value):
        name, value = _to_string(name), _to_string(value)
        del self[name]
        self._headers.append((name, value))

    def __delitem__(self, name):
        iname = _to_string(name).lower()
        new = []
        for k, v in self._headers:
            if k.lower() != iname:
                new.append((k, v))
        self._headers[:] = new

    def get(self, name, default_value=None):
        result = self[name]
        if not result:
            result = default_value
        return result

    def get_all(self, name):
        iname = _to_string(name).lower()
        return [v for k, v in self._headers if k.lower() == iname]

    def keys(self):
        return (k for k, _ in self._headers)

    def values(self):
        return (v for _, v in self._headers)

    def items(self):
        for k, v in self._headers:
            yield k, v

    def setdefault(self, name, default):
        name, default = _to_string(name), _to_string(default)
        if name in self:
            return self[name]
        self._headers.append((name, default))
        return default

    def add_header(self, _name, _value, **kwargs):
        _name, _value = _to_string(_name), _to_string(_value)
        self._headers.append((_name, _value))

    def clear(self):
        del self._headers[:]


class _Missing:
    def __repr__(self):
        return "no value"

    def __reduce__(self):
        return "_missing"


_missing = _Missing()


class cache_property(property):
    """缓存属性，用于类里面方法的装饰器
    描述符 __get__ 里参数 type，是类 property 里的参数
    """
    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __set__(self, obj, value):
        obj.__dict__[self.__name__] = value

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, _missing)
        if value is _missing:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value
