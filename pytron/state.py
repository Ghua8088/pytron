import sys
import threading

from .exceptions import StateError
from .serializer import pytron_serialize


def _get_global_store():
    # Helper to access standard sys overrides
    # (Used for Python-mock fallback if native fails)
    SOVEREIGN_KEY = "_pytron_sovereign_state_store_"
    store = getattr(sys, SOVEREIGN_KEY, None)
    if store is None:
        import builtins

        store = getattr(builtins, SOVEREIGN_KEY, None)
    return store


def _set_global_store(store):
    SOVEREIGN_KEY = "_pytron_sovereign_state_store_"
    setattr(sys, SOVEREIGN_KEY, store)
    import builtins

    setattr(builtins, SOVEREIGN_KEY, store)


def json_safe_dump(obj):
    """
    Convert obj to a JSON-safe primitive tree.

    Thin wrapper around pytron_serialize so state serialization benefits from
    the orjson fast path.  Preserves the ``to_dict()`` special-case so that
    ReactiveState / custom store objects serialise via their own method first.
    """
    if hasattr(obj, "to_dict") and not isinstance(obj, (str, bytes, dict, list)):
        try:
            return json_safe_dump(obj.to_dict())
        except Exception:
            pass
    return pytron_serialize(obj)


def log_shield(msg):
    try:
        if getattr(sys, "frozen", False):
            # In frozen apps, stderr might be captured or lost, but it's safe
            sys.stderr.write(f"[SHIELD] {msg}\n")
            sys.stderr.flush()
    except Exception:
        # Silently ignore failure to write to stderr in frozen environment
        pass


class _ObservableList(list):
    def __init__(self, seq, callback=None):
        self._callback = None
        super().__init__([_make_observable(item, callback) for item in seq])
        self._callback = callback

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
        self._callback = None
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
        elif mapping:
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
            return super().pop(key)

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


class ReactiveState:
    def __init__(self, app):
        object.__setattr__(self, "_app", app)

        # 1. Retrieve or Create the Global Store
        store = _get_global_store()

        if store is None:
            # TRY LOAD NATIVE via CANONICAL RESOLVER
            from .utils import resolve_native_module

            native_mod = resolve_native_module()
            NativeState = (
                getattr(native_mod, "NativeState", None) if native_mod else None
            )

            if NativeState:
                try:
                    store = NativeState()
                    mode = "Rust-Backed (Sovereign)"
                except Exception as e:
                    store = self._create_mock_store()
                    mode = f"Mock-Fallback (Rust Error: {e})"
            else:
                store = self._create_mock_store()
                mode = "Python-Mock"

            _set_global_store(store)
            log_shield(f"Sovereign State Initialized (Mode: {mode})")
        else:
            log_shield("ReactiveState: Inherited Sovereign Anchor")

        object.__setattr__(self, "_store", store)
        # Cache for observable wrappers: key -> (id(raw_val), wrapped_val).
        # Avoids re-allocating _ObservableDict/_ObservableList on every read.
        object.__setattr__(self, "_obs_cache", {})

    def _create_mock_store(self):
        class MockStore:
            def __init__(self):
                self.data = {}
                self._lock = threading.RLock()

            def set(self, k, v):
                with self._lock:
                    self.data[k] = v

            def get(self, k):
                with self._lock:
                    return self.data.get(k)

            def to_dict(self):
                with self._lock:
                    return dict(self.data)

            def update(self, m):
                with self._lock:
                    self.data.update(m)

        return MockStore()

    def __setattr__(self, key, value):
        if key.startswith("_"):
            object.__setattr__(self, key, value)
            return

        store = object.__getattribute__(self, "_store")
        app_ref = object.__getattribute__(self, "_app")

        try:
            # FIX #1: Check dedup BEFORE serializing.
            # Primitives skip serialization entirely — equality check is O(1).
            # Complex objects are serialized only when the check can't be done cheaply.
            if isinstance(value, (str, int, float, bool, type(None))):
                if store.get(key) == value:
                    return
                safe_val = value
            else:
                safe_val = json_safe_dump(value)
                if store.get(key) == safe_val:
                    return

            store.set(key, safe_val)
            if app_ref and hasattr(app_ref, "config") and app_ref.config.get("debug"):
                log_shield(f"State Update: {key}")
        except Exception as e:
            raise StateError(f"Failed to set state for key '{key}': {e}") from e

        if app_ref:
            try:
                app_ref.post("pytron:state-update", {"key": key, "value": safe_val})
            except Exception as e:
                log_shield(f"State Propagation Error: {e}")

    def __getattr__(self, key):
        if key.startswith("_"):
            return object.__getattribute__(self, key)
        try:
            val = object.__getattribute__(self, "_store").get(key)
            if isinstance(val, (dict, list)):
                # FIX #2: Cache the observable wrapper by (key, id(val)).
                # id(val) changes only when the underlying object is replaced,
                # so repeated reads of the same state key return the same wrapper
                # with zero allocation overhead.
                cache = object.__getattribute__(self, "_obs_cache")
                cached = cache.get(key)
                if cached is not None and cached[0] == id(val):
                    return cached[1]

                def update_cb():
                    self.__setattr__(key, wrapped_val)

                wrapped_val = _make_observable(val, update_cb)
                cache[key] = (id(val), wrapped_val)
                return wrapped_val
            return val
        except Exception:
            return None

    def to_dict(self):
        try:
            store = object.__getattribute__(self, "_store")
            return json_safe_dump(store.to_dict())
        except Exception as e:
            log_shield(f"to_dict failure: {e}")
            return {}

    def update(self, mapping: dict):
        if not isinstance(mapping, dict):
            return
        try:
            store = object.__getattribute__(self, "_store")
            store.update(json_safe_dump(mapping))
        except Exception:
            # Silently ignore store update errors
            pass
