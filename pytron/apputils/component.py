from typing import Any


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

        # Avoid recursion: if we are already looking up this name on the app, stop.
        # This is a bit of a hack but necessary given the bi-directional nature.
        app = getattr(self, "_app", None)
        if app is not None and app is not self:
            # We use __dict__ check to avoid triggering App properties if we just want the instance value
            # but since properties aren't in __dict__, we need to be careful.
            if hasattr(app, name):
                # SUCCESS: Forward to App (e.g. self.logger -> self._app.logger)
                attr = getattr(app, name)
                # If the attribute is a property, it might call us back.
                # But typically we want built-ins like .logger, .config
                return attr

        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )

    def __setattr__(self, name, value):
        if name == "_app" or name.startswith("_"):
            super().__setattr__(name, value)
            return

        # If the attribute is ALREADY in the component's __dict__, don't forward it.
        # This allows components to have their own state even if App has a property with same name.
        if name in self.__dict__:
            super().__setattr__(name, value)
            return

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
