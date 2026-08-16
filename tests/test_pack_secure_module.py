from unittest.mock import patch

from pytron.pack.secure import BuildContext, SecurityModule


def test_security_module_prepare(tmp_path):
    module = SecurityModule()
    context = BuildContext(script=tmp_path / "main.py", out_name="testapp")

    # We need to mock build_dir to point to tmp_path
    module.build_dir = tmp_path / "build"

    module.prepare(context)

    assert (tmp_path / "build" / "bootstrap_env.py").exists()
    assert context.script.name == "bootstrap_env.py"
    assert "app" in context.excludes
    assert "main" in context.excludes


def test_security_module_compact_library(tmp_path):
    module = SecurityModule()
    dist_dir = tmp_path / "dist"
    internal_dir = dist_dir / "_internal"
    internal_dir.mkdir(parents=True)

    import zipfile

    # Create a real zip file so zipfile.ZipFile(base_zip, "r") doesn't fail
    base_zip = internal_dir / "base_library.zip"
    with zipfile.ZipFile(base_zip, "w") as z:
        z.writestr("test.txt", "content")

    (internal_dir / "useful.pyc").write_text("dummy pyc")

    # Bundle path
    bundle_path = internal_dir / "app.bundle"

    # We need to mock log to avoid console output issues in tests
    with patch("pytron.pack.secure.log"):
        module.compact_library(dist_dir, bundle_path)

    assert bundle_path.exists()
    # base_library.zip should be gone if it was fused
    assert not (internal_dir / "base_library.zip").exists()
    assert not (internal_dir / "useful.pyc").exists()


@patch("pytron.pack.secure.log")
@patch("pytron.pack.secure.cython_compile")
@patch("shutil.copy2")
@patch("os.remove")
def test_security_module_build_wrapper_success(
    mock_remove, mock_copy, mock_compile, mock_log, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    module = SecurityModule()
    context = BuildContext(script=tmp_path / "main.py", out_name="testapp")
    context.package_dir = tmp_path / "pkg"

    # Mock bootloader lib — create both Windows and Unix variants so this test
    # passes on any CI platform (Windows uses .lib, macOS/Linux uses .a)
    bootloader_bin = context.package_dir / "pytron" / "pack" / "secure_loader" / "bin"
    bootloader_bin.mkdir(parents=True)
    (bootloader_bin / "pytron_rust_bootloader.lib").write_text("dummy lib")
    (bootloader_bin / "libpytron_rust_bootloader.a").write_text("dummy lib")

    # Mock compiled exe
    mock_compile.return_value = tmp_path / "compiled.exe"
    (tmp_path / "compiled.exe").write_text("dummy exe")

    # Mock dist dirs
    (tmp_path / "dist" / "testapp_base").mkdir(parents=True)

    def dummy_build(ctx):
        # Create base dist files
        (tmp_path / "dist" / "testapp_base" / "testapp_base.exe").write_text("base")
        return 0

    result = module.build_wrapper(context, dummy_build)
    assert result == 0
    assert mock_compile.called
    assert mock_copy.called
