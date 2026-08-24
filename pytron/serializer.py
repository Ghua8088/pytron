"""
pytron.serializer
-----------------
Single-pass, VAP-aware JSON serialization.

Architecture
~~~~~~~~~~~~
When orjson is available the entire pipeline collapses to a single Rust-speed
traversal: orjson handles all stdlib-compatible types natively (datetime, UUID,
dataclass, Enum, list, dict, tuple, …) and only calls back into Python for the
exotic types we care about (PIL.Image, pydantic.BaseModel, bytes, Decimal, …).

VAP side-effects (registering binary assets and rewriting them as
``pytron://`` URIs) are fused into that callback via a closure, so the tree is
visited exactly once and no intermediate dict tree is allocated.

When orjson is absent the stdlib fallback uses pytron_serialize() + json.dumps,
which visits the tree twice.  That path exists only for environments that
cannot install Rust extensions.

Public API
~~~~~~~~~~
fast_ipc_dump(data, vap_provider=None) -> str
    Single-pass encode for the IPC hot path.  Prefer this over all other
    combinations.

_fast_loads(s) -> object
    Decode a JSON string.  Uses orjson when available.

pytron_serialize(obj, vap_provider=None) -> object
    Recursive primitive converter.  Used only by the stdlib fallback path and
    by callers that explicitly need a Python primitive tree (e.g. state sync).

PytronJSONEncoder
    stdlib json.JSONEncoder subclass.  Used only when orjson is absent.
"""

import base64
import dataclasses
import datetime
import decimal
import enum
import io
import json
import pathlib
import uuid

# ── Optional rich-type dependencies ──────────────────────────────────────────
try:
    import pydantic
except ImportError:
    pydantic = None

try:
    from PIL import Image
except ImportError:
    Image = None

# ── Fast JSON backend (Rust) ──────────────────────────────────────────────────
try:
    import orjson as _orjson
    _ORJSON_AVAILABLE = True
except ImportError:
    _orjson = None
    _ORJSON_AVAILABLE = False

# Pre-compute the orjson option flags once at import time.
# OPT_NON_STR_KEYS  – serialize dicts whose keys are int/UUID/etc.
# OPT_SERIALIZE_DATACLASS is the default in modern orjson; listed explicitly
# for clarity and forward-compatibility.
_ORJSON_OPTIONS = (
    _orjson.OPT_NON_STR_KEYS | _orjson.OPT_SERIALIZE_DATACLASS
    if _orjson
    else 0
)

# Module-level type tuple for the common datetime branch (avoids repeated
# attribute lookups inside hot paths).
_DATETIME_TYPES = (datetime.datetime, datetime.date, datetime.time)


# ─────────────────────────────────────────────────────────────────────────────
# SINGLE-PASS UNIFIED ENCODER
# ─────────────────────────────────────────────────────────────────────────────

def _make_orjson_default(vap_provider):
    """
    Returns a *closure* that serves as orjson's ``default`` callback.

    orjson calls this function ONLY when it encounters a type it cannot
    serialize natively.  Everything orjson handles at Rust speed (datetime,
    UUID, dataclass, Enum, list, dict, tuple, str, int, float, bool, None)
    never enters this function at all.

    The closure captures ``vap_provider`` so VAP side-effects (registering
    binary assets) are fused into the single traversal pass.

    The return value must itself be orjson-serializable; orjson will continue
    encoding it without a second Python call.
    """
    def _default(obj):
        # ── PIL Image ────────────────────────────────────────────────────────
        if Image and isinstance(obj, Image.Image):
            buffered = io.BytesIO()
            obj.save(buffered, format="PNG")
            raw = buffered.getvalue()
            if vap_provider:
                asset_id = f"gen_img_{uuid.uuid4().hex[:8]}"
                vap_provider(asset_id, raw, "image/png")
                return f"pytron://{asset_id}"
            return f"data:image/png;base64,{base64.b64encode(raw).decode('ascii')}"

        # ── Pydantic BaseModel ───────────────────────────────────────────────
        # model_dump() / dict() return a plain dict that orjson encodes natively.
        if pydantic and isinstance(obj, pydantic.BaseModel):
            try:
                return obj.model_dump()
            except AttributeError:
                return obj.dict()

        # ── Raw bytes ────────────────────────────────────────────────────────
        # orjson raises TypeError on bytes; we handle VAP or base64 here.
        if isinstance(obj, bytes):
            if vap_provider:
                asset_id = f"gen_bin_{uuid.uuid4().hex[:8]}"
                vap_provider(asset_id, obj, "application/octet-stream")
                return f"pytron://{asset_id}"
            return base64.b64encode(obj).decode("ascii")

        # ── Types not covered by orjson's native pass ────────────────────────
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        if isinstance(obj, pathlib.Path):
            return str(obj)
        if isinstance(obj, set):
            # Return as list; orjson encodes it natively from here.
            return list(obj)
        if isinstance(obj, complex):
            return {"real": obj.real, "imag": obj.imag}
        if isinstance(obj, datetime.timedelta):
            return obj.total_seconds()

        # ── Generic objects ──────────────────────────────────────────────────
        # __dict__ covers most user-defined classes.
        if hasattr(obj, "__dict__"):
            return {k: v for k, v in vars(obj).items() if not k.startswith("_")}

        # __slots__ objects have no __dict__.
        if hasattr(obj, "__slots__"):
            slots = obj.__slots__
            if isinstance(slots, str):
                slots = (slots,)
            return {
                k: getattr(obj, k)
                for k in slots
                if not k.startswith("_") and hasattr(obj, k)
            }

        # Iterables (generators, custom collections, …)
        try:
            return list(obj)
        except TypeError:
            pass

        return str(obj)

    return _default


def fast_ipc_dump(data, vap_provider=None) -> str:
    """
    Single-pass, VAP-aware JSON encode.  Use this everywhere on the IPC path.

    With orjson installed
    ~~~~~~~~~~~~~~~~~~~~~
    * orjson traverses the tree once at Rust speed.
    * Only exotic types (PIL.Image, Pydantic, bytes, …) yield back to the
      Python ``_default`` closure, which also handles VAP registration.
    * The result bytes are decoded to str for the IPC bridge.

    Without orjson
    ~~~~~~~~~~~~~~
    * pytron_serialize() converts the tree to primitives (visit #1).
    * json.dumps() encodes the primitive tree (visit #2).
    * Slower, but fully correct. Install ``pytron-kit[speed]`` to avoid this.
    """
    if _ORJSON_AVAILABLE:
        return _orjson.dumps(
            data,
            default=_make_orjson_default(vap_provider),
            option=_ORJSON_OPTIONS,
        ).decode("utf-8")

    # Stdlib fallback: two-pass (acceptable when orjson is absent)
    return json.dumps(pytron_serialize(data, vap_provider), cls=PytronJSONEncoder)


def _fast_loads(s: str):
    """Decode a JSON string using orjson when available."""
    if _ORJSON_AVAILABLE:
        return _orjson.loads(s)
    return json.loads(s)


# ─────────────────────────────────────────────────────────────────────────────
# STDLIB FALLBACK ENCODER  (used only when orjson is absent)
# ─────────────────────────────────────────────────────────────────────────────

class PytronJSONEncoder(json.JSONEncoder):
    """
    stdlib JSONEncoder subclass.  Only used when orjson is not installed.
    Callers on the IPC hot path should use fast_ipc_dump() instead.
    """

    def __init__(self, *args, **kwargs):
        self.vap_provider = kwargs.pop("vap_provider", None)
        super().__init__(*args, **kwargs)

    def default(self, obj):
        if pydantic and isinstance(obj, pydantic.BaseModel):
            try:
                return obj.model_dump()
            except AttributeError:
                return obj.dict()

        if Image and isinstance(obj, Image.Image):
            asset_id = f"gen_img_{uuid.uuid4().hex[:8]}"
            buffered = io.BytesIO()
            obj.save(buffered, format="PNG")
            if self.vap_provider:
                self.vap_provider(asset_id, buffered.getvalue(), "image/png")
                return f"pytron://{asset_id}"
            return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode('ascii')}"

        if isinstance(obj, bytes):
            if self.vap_provider:
                asset_id = f"gen_bin_{uuid.uuid4().hex[:8]}"
                self.vap_provider(asset_id, obj, "application/octet-stream")
                return f"pytron://{asset_id}"
            return base64.b64encode(obj).decode("ascii")

        if isinstance(obj, _DATETIME_TYPES):
            return obj.isoformat()
        if isinstance(obj, datetime.timedelta):
            return obj.total_seconds()
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        if isinstance(obj, pathlib.Path):
            return str(obj)
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, complex):
            return {"real": obj.real, "imag": obj.imag}
        if isinstance(obj, enum.Enum):
            return obj.value
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return dataclasses.asdict(obj)

        if hasattr(obj, "__dict__"):
            try:
                return {k: v for k, v in vars(obj).items() if not k.startswith("_")}
            except TypeError:
                pass

        if hasattr(obj, "__slots__"):
            slots = obj.__slots__
            if isinstance(slots, str):
                slots = (slots,)
            data = {}
            for key in slots:
                if not key.startswith("_"):
                    try:
                        data[key] = getattr(obj, key)
                    except Exception:
                        pass
            if data:
                return data

        try:
            return list(obj)
        except TypeError:
            pass

        try:
            return str(obj)
        except Exception:
            return super().default(obj)


# ─────────────────────────────────────────────────────────────────────────────
# PRIMITIVE CONVERTER  (stdlib fallback path + explicit primitive-tree callers)
# ─────────────────────────────────────────────────────────────────────────────

def pytron_serialize(obj, vap_provider=None):
    """
    Recursively converts arbitrary objects into JSON-safe primitives.

    This function is retained for two purposes:
    1. The stdlib fallback path inside fast_ipc_dump() when orjson is absent.
    2. Callers that explicitly need a Python primitive tree (e.g. state sync,
       store serialization) rather than a JSON string.

    On the IPC hot path, prefer fast_ipc_dump() which avoids this pre-pass
    entirely when orjson is available.
    """
    # Fast path: already a primitive
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj

    # ── Most common collection types first ───────────────────────────────────
    if isinstance(obj, dict):
        return {str(k): pytron_serialize(v, vap_provider) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [pytron_serialize(i, vap_provider) for i in obj]

    # ── stdlib types ─────────────────────────────────────────────────────────
    if isinstance(obj, _DATETIME_TYPES):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    if isinstance(obj, pathlib.Path):
        return str(obj)
    if isinstance(obj, set):
        return [pytron_serialize(i, vap_provider) for i in obj]
    if isinstance(obj, datetime.timedelta):
        return obj.total_seconds()
    if isinstance(obj, complex):
        return {"real": obj.real, "imag": obj.imag}

    # ── Enum / Dataclass ─────────────────────────────────────────────────────
    if isinstance(obj, enum.Enum):
        return obj.value
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return pytron_serialize(dataclasses.asdict(obj), vap_provider)

    # ── Rich optional types ───────────────────────────────────────────────────
    if pydantic and isinstance(obj, pydantic.BaseModel):
        try:
            return pytron_serialize(obj.model_dump(), vap_provider)
        except AttributeError:
            return pytron_serialize(obj.dict(), vap_provider)

    if Image and isinstance(obj, Image.Image):
        buffered = io.BytesIO()
        obj.save(buffered, format="PNG")
        if vap_provider:
            asset_id = f"gen_img_{uuid.uuid4().hex[:8]}"
            vap_provider(asset_id, buffered.getvalue(), "image/png")
            return f"pytron://{asset_id}"
        return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode('ascii')}"

    if isinstance(obj, bytes):
        if vap_provider:
            asset_id = f"gen_bin_{uuid.uuid4().hex[:8]}"
            vap_provider(asset_id, obj, "application/octet-stream")
            return f"pytron://{asset_id}"
        return base64.b64encode(obj).decode("ascii")

    # ── Generic objects ───────────────────────────────────────────────────────
    if hasattr(obj, "__dict__"):
        return {
            k: pytron_serialize(v, vap_provider)
            for k, v in vars(obj).items()
            if not k.startswith("_")
        }
    if hasattr(obj, "__slots__"):
        slots = obj.__slots__
        if isinstance(slots, str):
            slots = (slots,)
        data = {}
        for key in slots:
            if not key.startswith("_"):
                try:
                    data[key] = pytron_serialize(getattr(obj, key), vap_provider)
                except Exception:
                    pass
        return data

    try:
        return [pytron_serialize(i, vap_provider) for i in obj]
    except TypeError:
        pass

    try:
        return str(obj)
    except Exception:
        return None
