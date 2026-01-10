import pytest
import argparse
from pathlib import Path
from pytron.commands.run import PytronFilter, cmd_run, run_dev_mode
from pytron.commands.helpers import locate_frontend_dir
from unittest.mock import MagicMock, patch

class TestPytronFilter:
    def test_filter_ignores_common_dirs(self, tmp_path):
        f = PytronFilter()
        # Should ignore .git
        assert f(1, str(tmp_path / ".git" / "config")) is False
        # Should ignore __pycache__
        assert f(1, str(tmp_path / "src" / "__pycache__" / "file.pyc")) is False
        # Should allow app.py
        assert f(1, str(tmp_path / "app.py")) is True

    def test_filter_ignores_frontend_src(self, tmp_path):
        frontend = tmp_path / "frontend"
        frontend.mkdir()
        f = PytronFilter(frontend_dir=frontend)
        
        # Should ignore frontend/src
        assert f(1, str(frontend / "src" / "App.jsx")) is False
        # Should allow backend/api.py
        assert f(1, str(tmp_path / "backend" / "api.py")) is True

class TestHelpers:
    def test_locate_frontend_dir(self, tmp_path):
        frontend = tmp_path / "frontend"
        frontend.mkdir()
        (frontend / "package.json").write_text('{"scripts": {"build": "vite build"}}')
        
        assert locate_frontend_dir(tmp_path) == frontend
        
    def test_locate_frontend_dir_missing(self, tmp_path):
        assert locate_frontend_dir(tmp_path) is None

class TestCLICommands:
    @patch("subprocess.call")
    @patch("pytron.commands.run.run_frontend_build")
    @patch("pytron.commands.run.get_python_executable", return_value="python")
    def test_cmd_run_basic(self, mock_py, mock_build, mock_call, tmp_path):
        app_py = tmp_path / "app.py"
        app_py.touch()
        
        args = argparse.Namespace(
            script=str(app_py),
            dev=False,
            engine=None,
            extra_args=[],
            no_build=False
        )
        
        code = cmd_run(args)
        assert code == mock_call.return_value
        mock_call.assert_called_once()
        assert "python" in mock_call.call_args[0][0]
        assert str(app_py) in mock_call.call_args[0][0]

    @patch("pytron.commands.run.run_dev_mode")
    def test_cmd_run_dev_flag(self, mock_dev, tmp_path):
        app_py = tmp_path / "app.py"
        app_py.touch()
        
        args = argparse.Namespace(
            script=str(app_py),
            dev=True,
            engine="edge",
            extra_args=["--foo"],
            no_build=False
        )
        
        cmd_run(args)
        mock_dev.assert_called_once_with(Path(app_py), ["--foo"], engine="edge")
