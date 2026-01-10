import json
import base64
import io
import datetime
import uuid
import decimal
import pathlib

# Optional dependencies
try:
    import pydantic
except ImportError:
    pydantic = None

try:
    from PIL import Image
except ImportError:
    Image = None


class PytronJSONEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        # PERFORMANCE: Capture the VAP provider if passed
        self.vap_provider = kwargs.pop("vap_provider", None)
        super().__init__(*args, **kwargs)

    def default(self, obj):
        if pydantic and isinstance(obj, pydantic.BaseModel):
            try:
                return obj.model_dump()
            except AttributeError:
                return obj.dict()

        if Image and isinstance(obj, Image.Image):
            # PERFORMANCE: Avoid Base64 overhead for images
            # Generate a virtual URL that uses the binary bridge (VAP)
            asset_id = f"gen_img_{uuid.uuid4().hex[:8]}"
            buffered = io.BytesIO()
            obj.save(buffered, format="PNG")
            
            # Note: We need a reference to the app to call serve_data.
            # Since this is a static encoder, we check if it's attached elsewhere
            # or fallback to base64 if no asset provider is found.
            if hasattr(self, "vap_provider"):
                self.vap_provider(asset_id, buffered.getvalue(), "image/png")
                return f"pytron://{asset_id}"

            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            return f"data:image/png;base64,{img_str}"

        if isinstance(obj, bytes):
            # PERFORMANCE: Avoid 33% Base64 bloat for binary blobs
            if hasattr(self, "vap_provider"):
                asset_id = f"gen_bin_{uuid.uuid4().hex[:8]}"
                self.vap_provider(asset_id, obj, "application/octet-stream")
                return f"pytron://{asset_id}"
            return base64.b64encode(obj).decode("utf-8")
        
        if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
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

        # 4. Enums
        try:
            import enum

            if isinstance(obj, enum.Enum):
                return obj.value
        except ImportError:
            pass

        # 5. Dataclasses
        try:
            import dataclasses

            if dataclasses.is_dataclass(obj):
                return dataclasses.asdict(obj)
        except ImportError:
            pass

        # 6. Universal Fallback: Try __dict__ / vars() for generic arbitrary objects
        if hasattr(obj, "__dict__"):
            try:
                return vars(obj)
            except TypeError:
                pass  # vars() argument must have __dict__ attribute

        # 6.5 Slots Fallback (for memory optimized objects without __dict__)
        if hasattr(obj, "__slots__"):
            data = {}
            slots = obj.__slots__
            if isinstance(slots, str):
                slots = [slots]
            for key in slots:
                # Skip private attributes and methods mixed into slots
                if not key.startswith("_"):
                    try:
                        data[key] = getattr(obj, key)
                    except Exception:
                        pass
            if data:
                return data

        # 7. Iterables (generators, etc)
        # Note: lists and tuples are handled by standard json encoder,
        # but generic iterators are not.
        try:
            iter(obj)
            # Check length is finite to prevent infinite loops?
            # Safer to just listify standard iterators, but careful with infinite ones.
            # We'll trust the user isn't serializing itertools.count()
            return list(obj)
        except TypeError:
            pass

        # 8. Final attempt: String representation used as last resort?
        # Or let standard encoder raise TypeError.
        # Returning str(obj) is "safe" but might be misleading (e.g. "<MyObj object at ...>")
        # Let's try str() if it has a custom __str__?
        # No, safer to standard error so user knows we couldn't structure it.
        # But user asked for "Universal". So __str__ is the ultimate fallback.
        try:
            return str(obj)
        except Exception:
            return super().default(obj)


def pytron_serialize(obj, vap_provider=None):
    """
    Helper to serialize objects to JSON-compatible primitives.
    OPTIMIZED: Avoids double serialization (dumps/loads) by recursively
    converting complex types into primitives.
    """
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    # Handle Pydantic Models
    if pydantic and isinstance(obj, pydantic.BaseModel):
        try:
            return pytron_serialize(obj.model_dump(), vap_provider)
        except AttributeError:
            return pytron_serialize(obj.dict(), vap_provider)

    # Handle PIL Images
    if Image and isinstance(obj, Image.Image):
        buffered = io.BytesIO()
        obj.save(buffered, format="PNG")
        if vap_provider:
            asset_id = f"gen_img_{uuid.uuid4().hex[:8]}"
            vap_provider(asset_id, buffered.getvalue(), "image/png")
            return f"pytron://{asset_id}"
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{img_str}"

    if isinstance(obj, bytes):
        if vap_provider:
            asset_id = f"gen_bin_{uuid.uuid4().hex[:8]}"
            vap_provider(asset_id, obj, "application/octet-stream")
            return f"pytron://{asset_id}"
        return base64.b64encode(obj).decode("utf-8")

    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
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
        return [pytron_serialize(i, vap_provider) for i in obj]
    if isinstance(obj, complex):
        return {"real": obj.real, "imag": obj.imag}

    # Dataclasses
    try:
        import dataclasses
        if dataclasses.is_dataclass(obj):
            return pytron_serialize(dataclasses.asdict(obj), vap_provider)
    except ImportError:
        pass

    # Enums
    try:
        import enum
        if isinstance(obj, enum.Enum):
            return obj.value
    except ImportError:
        pass

    # Dictionaries
    if isinstance(obj, dict):
        return {str(k): pytron_serialize(v, vap_provider) for k, v in obj.items()}

    # Iterables
    if isinstance(obj, (list, tuple)):
        return [pytron_serialize(i, vap_provider) for i in obj]

    # Universal Fallback: Try __dict__
    if hasattr(obj, "__dict__"):
        return {k: pytron_serialize(v, vap_provider) for k, v in vars(obj).items() if not k.startswith("_")}

    # Slots Fallback
    if hasattr(obj, "__slots__"):
        data = {}
        slots = obj.__slots__
        if isinstance(slots, str):
            slots = [slots]
        for key in slots:
            if not key.startswith("_"):
                try:
                    data[key] = pytron_serialize(getattr(obj, key), vap_provider)
                except Exception:
                    pass
        return data

    # Final attempt: String representation
    try:
        return str(obj)
    except Exception:
        return None
