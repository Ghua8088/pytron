from abc import ABC, abstractmethod
from typing import Optional, Dict, List, TypeAlias

# Defines a "Handle" type for clarity -> Zero runtime cost, high readability.
WindowHandle: TypeAlias = int


class PlatformInterface(ABC):
    """
    PINNED STABILITY CONTRACT
    -------------------------
    This interface defines the immutable core contract for all platform implementations.
    Core lifecycle and window operations are abstract and MUST be implemented.
    Extended capabilities (Notifications, Taskbar, etc.) are virtual and optional.
    """

    # Runtime ownership strategy:
    # - "platform" -> this platform layer owns native toolkit interaction.
    # - "engine"   -> the active in-process engine owns the overlapping toolkit.
    runtime_owner = "platform"
    legacy_backend = None

    # --- Core Window Operations (Pinned) ---

    @abstractmethod
    def show(self, w: WindowHandle) -> None:
        pass

    @abstractmethod
    def hide(self, w: WindowHandle) -> None:
        pass

    @abstractmethod
    def close(self, w: WindowHandle) -> None:
        pass

    @abstractmethod
    def minimize(self, w: WindowHandle) -> None:
        pass

    @abstractmethod
    def toggle_maximize(self, w: WindowHandle) -> bool:
        """Returns True if maximized, False if restored."""
        pass

    @abstractmethod
    def maximize(self, w: WindowHandle) -> None:
        pass

    @abstractmethod
    def restore(self, w: WindowHandle) -> None:
        pass

    @abstractmethod
    def set_title(self, w: WindowHandle, title: str) -> None:
        pass

    @abstractmethod
    def set_bounds(
        self, w: WindowHandle, x: int, y: int, width: int, height: int
    ) -> None:
        pass

    @abstractmethod
    def set_fullscreen(self, w: WindowHandle, fullscreen: bool) -> None:
        pass

    @abstractmethod
    def set_always_on_top(self, w: WindowHandle, enable: bool) -> None:
        pass

    @abstractmethod
    def is_visible(self, w: WindowHandle) -> bool:
        pass

    @abstractmethod
    def center(self, w: WindowHandle) -> None:
        pass

    # --- Essential extensions (Should interpret 'w') ---

    def is_alive(self, w: WindowHandle) -> bool:
        """Checks if the native window handle is still valid. Default True to prevent crashes."""
        return True

    def set_size(
        self, w: WindowHandle, width: int, height: int, hints: int = 0
    ) -> None:
        """Sets the window size. Default delegates to set_bounds with current pos."""
        self.set_bounds(w, -1, -1, width, height)

    def make_frameless(self, w: WindowHandle) -> None:
        pass

    def set_utility_window(self, w: WindowHandle, enable: bool) -> None:
        """Configures the window as a utility window (e.g. hides from taskbar on Windows)."""
        pass

    def start_drag(self, w: WindowHandle) -> None:
        pass

    def set_window_icon(self, w: WindowHandle, icon_path: str) -> None:
        pass

    def set_menu(self, w: WindowHandle, menu_bar: List) -> None:
        pass

    # --- System Dialogs & Interactions (Stable Extensions) ---

    def message_box(
        self, w: WindowHandle, title: str, message: str, style: int = 0
    ) -> int:
        return 0  # Default OK/Cancel result

    def open_file_dialog(
        self,
        w: WindowHandle,
        title: str,
        default_path: Optional[str] = None,
        file_types: Optional[str] = None,
    ) -> Optional[str]:
        return None

    def save_file_dialog(
        self,
        w: WindowHandle,
        title: str,
        default_path: Optional[str] = None,
        default_name: Optional[str] = None,
        file_types: Optional[str] = None,
    ) -> Optional[str]:
        return None

    def open_folder_dialog(
        self, w: WindowHandle, title: str, default_path: Optional[str] = None
    ) -> Optional[str]:
        return None

    def notification(
        self, w: WindowHandle, title: str, message: str, icon: Optional[str] = None
    ) -> None:
        pass

    def toast(self, w: WindowHandle, config: Dict) -> None:
        """Sends a rich, modern system notification (Windows Toast / macOS UserNotification)."""
        pass

    def set_taskbar_progress(
        self, w: WindowHandle, state: str, value: int, max_value: int
    ) -> None:
        """
        Sets the taskbar/dock progress bar state.
        state: 'normal', 'error', 'paused', 'indeterminate', 'none'
        """
        pass

    # --- System Integration (OS Hooks) ---

    def register_protocol(self, scheme: str) -> bool:
        return False

    def set_launch_on_boot(
        self, app_name: str, exe_path: str, enable: bool = True
    ) -> bool:
        return False

    def set_app_id(self, app_id: str) -> None:
        pass

    def get_system_info(self) -> Dict:
        return {}

    # --- Clipboard ---

    def set_clipboard_text(self, text: str) -> bool:
        return False

    def get_clipboard_text(self) -> Optional[str]:
        return None

    # --- UI Polish ---

    def set_slim_titlebar(self, w: WindowHandle, enabled: bool) -> None:
        pass

    def set_border_color(self, w: WindowHandle, color_hex: str) -> None:
        """Sets the native window border color (Windows 11+)."""
        pass

    def runtime_strategy(self) -> Dict[str, str]:
        """Exposes how this implementation interacts with native runtime ownership."""
        return {
            "runtime_owner": self.runtime_owner,
            "legacy_backend": self.legacy_backend or "none",
        }
