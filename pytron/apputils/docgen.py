import os
import json
import inspect
import typing
import shutil
import pathlib
from .component import AppComponent

try:
    import pydantic
except ImportError:
    pydantic = None

try:
    from PIL import Image
except ImportError:
    Image = None


class DocgenComponent(AppComponent):
    """
    Component for generating automated API documentation for Pytron apps.
    """

    def _extract_theme_colors(self, icon_path: pathlib.Path) -> typing.Tuple[str, str]:
        """
        Analyzes the icon to find a dominant accent color.
        Returns (hex_color, glow_color).
        """
        if not Image or not icon_path.exists():
            return "#8b5cf6", "rgba(139, 92, 246, 0.4)"  # Fallback to Pytron Purple

        try:
            img = Image.open(icon_path).convert("RGBA")
            img.thumbnail((50, 50))  # Resize for speed

            # Simple dominant color: get pixel with most frequency that isn't too dark/light/transparent
            colors = img.getcolors(50 * 50)
            if not colors:
                return "#8b5cf6", "rgba(139, 92, 246, 0.4)"

            # Filter for vibrant colors (skip black, white, and transparent)
            vibrant_colors = []
            for count, (r, g, b, a) in colors:
                if a < 128:
                    continue  # Skip transparent
                brightness = r * 0.299 + g * 0.587 + b * 0.114
                if 40 < brightness < 220:  # Skip very dark/very light
                    vibrant_colors.append((count, (r, g, b)))

            if not vibrant_colors:
                # Fallback to the first opaque color
                for count, (r, g, b, a) in sorted(
                    colors, key=lambda x: x[0], reverse=True
                ):
                    if a > 200:
                        vibrant_colors.append((count, (r, g, b)))
                        break

            if not vibrant_colors:
                return "#8b5cf6", "rgba(139, 92, 246, 0.4)"

            # Pick the most frequent vibrant color
            vibrant_colors.sort(key=lambda x: x[0], reverse=True)
            r, g, b = vibrant_colors[0][1]

            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            glow_color = f"rgba({r}, {g}, {b}, 0.4)"
            return hex_color, glow_color

        except Exception as e:
            self.app.logger.debug(f"Color extraction failed: {e}")
            return "#8b5cf6", "rgba(139, 92, 246, 0.4)"

    def generate_metadata(self) -> dict:
        """
        Extracts all API information into a structured dictionary.
        """
        metadata = {
            "title": self.app.config.get("title", "Pytron Application"),
            "version": self.app.config.get("version", "1.0.0"),
            "pytron_version": self.app.config.get("pytron_version", "0.2.2"),
            "icon": self.app.config.get("icon"),
            "accent_color": "#8b5cf6",
            "accent_glow": "rgba(139, 92, 246, 0.4)",
            "exposed_functions": [],
            "models": [],
            "system_apis": [],
        }

        # 1. Process Exposed User Functions
        for name, info in self.app._exposed_functions.items():
            func = info["func"]
            metadata["exposed_functions"].append(self._parse_function(name, func))

        # 2. Process Pydantic Models
        # Collect models discovered during type parsing
        processed_models = set()
        models_to_process = list(self.app._pydantic_models.items())

        while models_to_process:
            model_name, model_cls = models_to_process.pop(0)
            if model_name in processed_models:
                continue

            metadata["models"].append(self._parse_model(model_name, model_cls))
            processed_models.add(model_name)

        # 3. Add Core System APIs (Common ones)
        from ..webview import Webview

        win_map = {
            "minimize": "Minimize Window",
            "close": "Close Application",
            "show": "Show Window",
            "hide": "Hide Window",
            "notify": "Show In-App Notification",
            "set_title": "Update Window Title",
        }
        for name, desc in win_map.items():
            method = getattr(Webview, name, None)
            if method:
                parsed = self._parse_function(name, method)
                parsed["description"] = desc + (
                    f". {parsed['description']}" if parsed["description"] else ""
                )
                metadata["system_apis"].append(parsed)

        return metadata

    def build_docs(self, output_dir: str = "docs"):
        """
        Builds the static documentation site.
        """
        output_path = pathlib.Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        metadata = self.generate_metadata()

        # 1. Copy & Process Icon
        icon_name = None
        if metadata["icon"]:
            # Try to find the icon relative to the project root
            icon_src = pathlib.Path(metadata["icon"])
            if not icon_src.exists():
                # Try relative to cwd
                icon_src = pathlib.Path.cwd() / metadata["icon"]

            if icon_src.exists():
                icon_ext = icon_src.suffix
                icon_name = f"icon{icon_ext}"
                try:
                    shutil.copy2(icon_src, output_path / icon_name)
                    metadata["icon_path"] = icon_name

                    # 1.1 Extract Theme Colors
                    accent, glow = self._extract_theme_colors(icon_src)
                    metadata["accent_color"] = accent
                    metadata["accent_glow"] = glow
                except Exception as e:
                    self.app.logger.debug(f"Failed to copy icon: {e}")

        # 2. Process Template with Inlined Metadata
        # Inlining metadata prevents CORS errors when opening index.html via file://
        template_dir = pathlib.Path(__file__).parent.parent / "resources" / "docgen"
        template_file = template_dir / "index.html"

        if template_file.exists():
            with open(template_file, "r") as f:
                html_content = f.read()

            # Injection
            meta_json = json.dumps(metadata, indent=2)
            html_content = html_content.replace(
                "//---METADATA---", f"window.metadata = {meta_json};"
            )

            with open(output_path / "index.html", "w") as f:
                f.write(html_content)

            # Copy other assets if any (css/js)
            for item in template_dir.iterdir():
                if item.name == "index.html":
                    continue
                if item.is_dir():
                    shutil.copytree(item, output_path / item.name, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, output_path / item.name)
        else:
            self._generate_minimal_index(output_path, metadata)

        self.app.logger.info(f"Documentation generated at: {output_path.absolute()}")
        return str(output_path.absolute())

    def _parse_function(self, name: str, func: typing.Callable) -> dict:
        """Parses a function into metadata."""
        try:
            sig = inspect.signature(func)
            doc = inspect.getdoc(func) or ""

            params = []
            for p_name, p in sig.parameters.items():
                if p_name == "self":
                    continue

                params.append(
                    {
                        "name": p_name,
                        "type": self._get_type_name(p.annotation),
                        "default": (
                            str(p.default)
                            if p.default != inspect.Parameter.empty
                            else None
                        ),
                        "required": p.default == inspect.Parameter.empty,
                    }
                )

            return {
                "name": name,
                "description": doc,
                "parameters": params,
                "return_type": self._get_type_name(sig.return_annotation),
                "is_async": inspect.iscoroutinefunction(func),
            }
        except Exception as e:
            return {
                "name": name,
                "description": f"Parsing failed: {e}",
                "parameters": [],
                "return_type": "any",
            }

    def _parse_model(self, name: str, model_cls: typing.Any) -> dict:
        """Parses a Pydantic model into metadata."""
        fields = []
        doc = inspect.getdoc(model_cls) or ""

        # Pydantic 2.0 / 1.0 Boilerplate Cleanup
        # We strip the giant internal Usage Documentation block if it's the default BaseModel help
        if (
            '!!! abstract "Usage Documentation"' in doc
            or "A base class for creating Pydantic" in doc
        ):
            doc = ""

        # Pydantic v1 vs v2 field extraction
        field_defs = {}
        if hasattr(model_cls, "model_fields"):  # v2
            field_defs = model_cls.model_fields
        elif hasattr(model_cls, "__fields__"):  # v1
            field_defs = model_cls.__fields__

        for f_name, f in field_defs.items():
            # Skip private fields or Pydantic internal state
            if f_name.startswith("_") or f_name.startswith("__pydantic"):
                continue

            if hasattr(f, "annotation"):  # v2
                f_type = f.annotation
            elif hasattr(f, "type_"):  # v1
                f_type = f.type_
            else:
                f_type = typing.Any

            # Extract description from Field() if available
            f_doc = ""
            if hasattr(f, "description") and f.description:
                f_doc = f.description
            elif hasattr(f, "json_schema_extra") and f.json_schema_extra:
                f_doc = f.json_schema_extra.get("description", "")

            fields.append(
                {
                    "name": f_name,
                    "type": self._get_type_name(f_type),
                    "description": f_doc,
                }
            )

        return {"name": name, "description": doc, "fields": fields}

    def _get_type_name(self, py_type) -> str:
        """Converts Python type to a readable string."""
        if py_type == inspect.Parameter.empty:
            return "any"
        if hasattr(py_type, "__name__"):
            return py_type.__name__
        return str(py_type).replace("typing.", "")

    def _generate_minimal_index(self, path, metadata):
        """Generates a basic HTML if the resource template isn't found yet."""
        html = f"<html><body><h1>{metadata['title']} API Docs</h1><pre>{json.dumps(metadata, indent=2)}</pre></body></html>"
        with open(path / "index.html", "w") as f:
            f.write(html)
