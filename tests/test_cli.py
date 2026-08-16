import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

from pytron.commands.helpers import locate_frontend_dir
from pytron.commands.run import PytronFilter, cmd_run, run_dev_mode


class TestPytronFilter:
    def test_filter_ignores_common_dirs(self, tmp_path):
        f = PytronFilter(project_root=tmp_path)
        # Should ignore .git
        assert f(1, str(tmp_path / ".git" / "config")) is False
        # Should ignore __pycache__
        assert f(1, str(tmp_path / "src" / "__pycache__" / "file.pyc")) is False
        # Should allow app.py
        assert f(1, str(tmp_path / "app.py")) is True

    def test_filter_ignores_frontend_src(self, tmp_path):
        frontend = tmp_path / "frontend"
        frontend.mkdir()
        f = PytronFilter(project_root=tmp_path, frontend_dir=frontend)

        # Should ignore frontend/src
        assert f(change=1, path=str(frontend / "src" / "App.jsx")) is False
        # Should ignore node_modules in root
        assert f(change=1, path=str(tmp_path / "node_modules" / "some-pkg")) is False
        # Should allow backend/api.py
        assert f(change=1, path=str(tmp_path / "backend" / "api.py")) is True


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
            script=str(app_py), dev=False, engine=None, extra_args=[], no_build=False
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
            no_build=False,
        )

        cmd_run(args)
        mock_dev.assert_called_once_with(Path(app_py), ["--foo"], engine="edge")

    @patch("watchfiles.watch")
    @patch("subprocess.run")
    @patch("subprocess.Popen")
    @patch("pytron.commands.run.get_python_executable", return_value="python")
    @patch("pytron.commands.run.locate_frontend_dir", return_value=None)
    def test_run_dev_mode_loop(
        self, mock_locate, mock_py, mock_popen, mock_run, mock_watch, tmp_path
    ):
        app_py = tmp_path / "app.py"
        app_py.touch()

        # Setup watch to exit immediately
        mock_watch.return_value = []

        # Mock proc
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc

        code = run_dev_mode(app_py, ["--arg"])

        assert code == 0
        mock_popen.assert_called()
        # Should have started the app at least once
        args = mock_popen.call_args_list[0][0][0]
        assert "python" in args
        assert str(app_py) in args
        assert "--arg" in args
