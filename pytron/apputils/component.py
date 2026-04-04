import threading
from typing import Any

# Global thread-local storage for tracking active lookups to prevent recursion loops
_active_lookups = threading.local()


class AppComponent:
    """Base class for all discrete Pytron capabilities replacing old Mixins."""

    def __init__(self, app: Any):
        self._app = app

    @property
    def app(self):
        return self._app

    def __getattr__(self, name):
        if name == "_app":
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'"
            )

        # Initialize thread-local set if it doesn't exist
        if not hasattr(_active_lookups, "active"):
            _active_lookups.active = set()

        lookup_key = (id(self), name)
        if lookup_key in _active_lookups.active:
            # We are already in the middle of looking this up on THIS component.
            # Bail out to avoid RecursionError.
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}' (Recursion detected)"
            )

        _active_lookups.active.add(lookup_key)

        try:
            # Avoid recursion: if we are already looking up this name on the app, stop.
            # This is a bit of a hack but necessary given the bi-directional nature.
            app = getattr(self, "_app", None)
            if app is not None and app is not self:
                # We use hasattr which might trigger properties, but our shield above
                # will catch us if the property calls us back.
                if hasattr(app, name):
                    # SUCCESS: Forward to App (e.g. self.logger -> self._app.logger)
                    attr = getattr(app, name)
                    return attr

            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'"
            )
        finally:
            _active_lookups.active.discard(lookup_key)

    def __setattr__(self, name, value):
        if name == "_app" or name.startswith("_"):
            super().__setattr__(name, value)
            return

        # If the attribute is ALREADY in the component's __dict__, don't forward it.
        # This allows components to have their own state even if App has a property with same name.
        if name in self.__dict__:
            super().__setattr__(name, value)
            return

        # Initialize thread-local set if it doesn't exist
        if not hasattr(_active_lookups, "active_set"):
            _active_lookups.active_set = set()

        set_key = (id(self), name)
        if set_key in _active_lookups.active_set:
            super().__setattr__(name, value)
            return

        _active_lookups.active_set.add(set_key)

        try:
            app = getattr(self, "_app", None)
            # ONLY forward if the app actually HAS this attribute and it's NOT a property we're
            # masking or if we're in the middle of a loop.
            # To keep it simple: if it's in our init, we want it locally.

            # High-order fix: If the attribute is 'plugin_statuses', we DEFINITELY want it locally
            # because the App property is just a facade for us.
            if name == "plugin_statuses":
                super().__setattr__(name, value)
                return

            if app is not None and app is not self and hasattr(app, name):
                setattr(app, name, value)
            else:
                super().__setattr__(name, value)
        finally:
            _active_lookups.active_set.discard(set_key)
