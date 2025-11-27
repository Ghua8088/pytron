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
    def default(self, obj):
        if pydantic and isinstance(obj, pydantic.BaseModel):
            try:
                return obj.model_dump()
            except AttributeError:
                return obj.dict()
        if Image and isinstance(obj, Image.Image):
            buffered = io.BytesIO()
            obj.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            return f"data:image/png;base64,{img_str}"
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode('utf-8')
        if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
            return obj.isoformat()
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        if isinstance(obj, pathlib.Path):
            return str(obj)
        if isinstance(obj, set):
            return list(obj)
        return super().default(obj)

def pytron_serialize(obj):
    """
    Helper to serialize objects to JSON-compatible primitives.
    This ensures that return values from Python functions are safe for pywebview to serialize.
    """
    # Optimization: if it's already a primitive, return it
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
        
    # Use the encoder to handle everything else recursively
    return json.loads(json.dumps(obj, cls=PytronJSONEncoder))
