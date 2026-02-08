# Credits & Third-Party Acknowledgments

Pytron Kit is built on the shoulders of giants. We are grateful to the following open-source projects and their communities for providing the foundational technologies that make this framework possible.

## Core Rendering & Windowing
*   **[Wry](https://github.com/tauri-apps/wry)**: A cross-platform webview rendering library in Rust. Used for our high-performance Native Engine.
*   **[Tao](https://github.com/tauri-apps/tao)**: A cross-platform window creation library in Rust.
*   **[Electron](https://www.electronjs.org/)**: Used as our optional rendering engine for maximum compatibility and parity with Chromium.

## Internal Engineering
*   **[Rust](https://www.rust-lang.org/)**: Powers our secure bootloader and native extensions. Huge thanks for providing the memory safety and performance required for the Agentic Shield.
*   **[Zig](https://ziglang.org/)**: Utilized for cross-compilation and native toolchain orchestration. We are grateful for Zig's incredible "it just works" approach to C/C++ toolchains.
*   **[Cython](https://cython.org/)**: Used for compiling performance-critical modules and securing the "Agentic Shield" pipeline. Thanks for bridging the gap between Python and C so elegantly.
*   **[PyInstaller](https://pyinstaller.org/)**: The reliable workhorse for standard application packaging. Thank you for the years of work that make Python distribution possible.
*   **[Nuitka](https://nuitka.net/)**: A Python-to-C++ compiler used for our high-performance machine code builds.

## Python Ecosystem
*   **[PyPI](https://pypi.org/)**: The Python Package Index. Huge thanks for hosting the worldwide community of Python software. We'd be nothing without you.
*   **[Keyring](https://github.com/jaraco/keyring)**: For providing a secure way to handle secrets and credentials across different OS environments.
*   **[Requests](https://requests.readthedocs.io/)**: For making HTTP requests human-friendly and reliable.
*   **[Pytest](https://pytest.org/)**: For providing the backbone of our testing suite and ensuring Pytron stays stable.
*   **[Comtypes](https://github.com/enthought/comtypes)**: Essential for our deep Win32 COM integrations on Windows.

## Frontend Ecosystem
*   **[Vite](https://vitejs.dev/)**: The lightning-fast build tool used for our project scavenging and HMR.
*   **[React](https://reactjs.org/)**: The default frontend framework for Pytron project templates.

## Inspiration & Community
*   **[pywebview](https://github.com/r0x0r/pywebview)**: Our native engine implementation was heavily inspired by the pioneering work of the pywebview team in bringing web technologies to Python.
*   **[Tauri](https://tauri.app/)**: For setting the gold standard in secure, lightweight cross-platform development.

---

### License Note
The use of these libraries is governed by their respective licenses (MIT, Apache 2.0, or BSD). Pytron Kit's use of a "Commons Clause" rider on its own license does not affect the licensing of these dependencies, nor does it claim ownership over their work. We strictly adhere to all attribution requirements for these upstream projects.
