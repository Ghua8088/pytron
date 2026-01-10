import pytest
from unittest.mock import MagicMock, patch, mock_open
import sys
import os

from pytron.platforms.linux import LinuxImplementation
from pytron.platforms.darwin import DarwinImplementation

class TestLinuxImplementation:
    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("subprocess.run")
    def test_register_protocol(self, mock_run, mock_file, mock_mkdir):
        impl = LinuxImplementation()
        # Mock sys.executable for the desktop file
        with patch("sys.executable", "/usr/bin/python3"):
            impl.register_protocol("pytron")
            
        # Check if desktop file was written
        # It should go to ~/.local/share/applications/pytron-handler-pytron.desktop
        expected_path = os.path.join(os.path.expanduser("~/.local/share/applications"), "pytron-handler-pytron.desktop")
        
        # Verify mkdir was called
        mock_mkdir.assert_called()
        
        # Verify file write
        mock_file.assert_called()
        handle = mock_file()
        content = "".join(call.args[0] for call in handle.write.call_args_list)
        assert "python3" in content
        assert "MimeType=x-scheme-handler/pytron" in content
        
        # Verify update-desktop-database
        mock_run.assert_any_call(["update-desktop-database", os.path.expanduser("~/.local/share/applications")], capture_output=True)

class TestDarwinImplementation:
    @patch("subprocess.run")
    def test_register_protocol(self, mock_run):
        impl = DarwinImplementation()
        # On Mac it mostly calls lsregister if bundled
        with patch("sys.frozen", True, create=True), \
             patch("sys.executable", "/Applications/MyApp.app/Contents/MacOS/MyApp"), \
             patch("os.path.exists", return_value=True):
            impl.register_protocol("pytron")
        
        # Check if lsregister was called
        # The path can vary but it should contain -f
        found = False
        for call in mock_run.call_args_list:
            if "lsregister" in str(call):
                found = True
                assert "-f" in call.args[0]
        assert found
