

class _ObservableList(list):
    def __init__(self, seq, callback=None):
        self._callback = callback
        super().__init__([_make_observable(item, callback) for item in seq])

    def __setitem__(self, index, value):
        super().__setitem__(index, _make_observable(value, self._callback))
        if self._callback:
            self._callback()

    def __delitem__(self, index):
        super().__delitem__(index)
        if self._callback:
            self._callback()

    def append(self, o):
        super().append(_make_observable(o, self._callback))
        if self._callback:
            self._callback()

    def extend(self, iterable):
        super().extend([_make_observable(x, self._callback) for x in iterable])
        if self._callback:
            self._callback()

    def insert(self, index, obj):
        super().insert(index, _make_observable(obj, self._callback))
        if self._callback:
            self._callback()

    def pop(self, index=-1):
        res = super().pop(index)
        if self._callback:
            self._callback()
        return res

    def remove(self, value):
        super().remove(value)
        if self._callback:
            self._callback()

    def clear(self):
        super().clear()
        if self._callback:
            self._callback()

    def reverse(self):
        super().reverse()
        if self._callback:
            self._callback()

    def sort(self, *args, **kwds):
        super().sort(*args, **kwds)
        if self._callback:
            self._callback()


class _ObservableDict(dict):
    def __init__(self, mapping=(), callback=None, **kwargs):
        self._callback = None  # prevent firing during init
        super().__init__()
        self.update(mapping, **kwargs)
        self._callback = callback

    def __setitem__(self, key, value):
        super().__setitem__(key, _make_observable(value, self._callback))
        if self._callback:
            self._callback()

    def __delitem__(self, key):
        super().__delitem__(key)
        if self._callback:
            self._callback()

    def update(self, mapping=(), **kwargs):
        if hasattr(mapping, "keys"):
            for k in mapping.keys():
                super().__setitem__(k, _make_observable(mapping[k], self._callback))
        else:
            for k, v in mapping:
                super().__setitem__(k, _make_observable(v, self._callback))
        for k, v in kwargs.items():
            super().__setitem__(k, _make_observable(v, self._callback))
        if self._callback:
            self._callback()

    def pop(self, key, default=None):
        if key in self:
            res = super().pop(key)
            if self._callback:
                self._callback()
            return res
        elif default is not None:
            return default
        else:
            return super().pop(key)  # raise KeyError

    def popitem(self):
        res = super().popitem()
        if self._callback:
            self._callback()
        return res

    def clear(self):
        super().clear()
        if self._callback:
            self._callback()

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]


def _make_observable(obj, callback):
    if isinstance(obj, dict) and not isinstance(obj, _ObservableDict):
        return _ObservableDict(obj, callback)
    if isinstance(obj, list) and not isinstance(obj, _ObservableList):
        return _ObservableList(obj, callback)
    return obj


def test():
    def cb():
        print("Updated!!", val)

    val = _make_observable([{"a": 1}], cb)
    val[0]["a"] = 2
    val.append(5)


test()
