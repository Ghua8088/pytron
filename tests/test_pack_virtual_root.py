import pytest
from pathlib import Path
from pytron.pack.virtual_root import VirtualRootGenerator
import os


def test_virtual_root_scan(tmp_path):
    # Create dummy source files with app.expose
    source_dir = tmp_path / "src"
    source_dir.mkdir()

    file1 = source_dir / "api.py"
    file1.write_text(
        """
from pytron import App
app = App()

@app.expose
def user_get():
    return "user"

@app.expose(name="login")
def auth_login():
    return "login"
"""
    )

    file2 = source_dir / "utils.py"
    file2.write_text(
        """
def helper(): pass
"""
    )

    generator = VirtualRootGenerator(source_dir)
    generator.scan()

    # Check if exposed functions were found
    # module_name for api.py in src/ should be 'api' if source_dir is 'src'
    assert len(generator.exposed_functions) >= 2
    # The generator extracts the function name or the argument to expose
    # It looks like it handles @app.expose def user_get() -> ('api', 'user_get')
    # and maybe @app.expose(name="login") if it's an attribute call

    # Re-verify based on virtual_root.py logic:
    # if isinstance(node, ast.FunctionDef): for dec in node.decorator_list: ... if dec.attr == "expose": is_exposed = True
    # if is_exposed: self.exposed_functions.append((module_name, node.name))

    found_names = [f[1] for f in generator.exposed_functions]
    assert "user_get" in found_names
    assert "auth_login" in found_names


def test_virtual_root_nested_scan(tmp_path):
    source_dir = tmp_path / "src"
    source_dir.mkdir()

    sub_dir = source_dir / "models"
    sub_dir.mkdir()

    file1 = sub_dir / "user.py"
    file1.write_text("@app.expose\ndef get_user(): pass")

    generator = VirtualRootGenerator(source_dir)
    generator.scan()

    assert any(f[0] == "models.user" for f in generator.exposed_functions)
    assert any(f[1] == "get_user" for f in generator.exposed_functions)


def test_virtual_root_generate(tmp_path):
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (source_dir / "api.py").write_text("@app.expose\ndef foo(): pass")

    generator = VirtualRootGenerator(source_dir)
    generator.scan()

    output_file = tmp_path / "_virtual_root.py"
    generator.generate(output_file)

    content = output_file.read_text()
    assert "import api" in content
    assert "from api import foo" in content
    assert "def main():" in content
