from setuptools import setup

try:
    from setuptools.dist import Distribution

    class BinaryDistribution(Distribution):
        """Force the wheel to be platform-specific."""

        def has_ext_modules(self):
            return True

        def is_pure(self):
            return False

except ImportError:
    BinaryDistribution = None

try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel

    class bdist_wheel(_bdist_wheel):
        def finalize_options(self):
            super().finalize_options()
            # This is the "Universal ABI3" tag
            self.py_limited_api = "cp37"

        def get_tag(self):
            python, abi, plat = super().get_tag()
            # Force py3-none for any platform build
            return "py3", "none", plat

except ImportError:
    bdist_wheel = None

setup(
    distclass=BinaryDistribution,
    cmdclass={"bdist_wheel": bdist_wheel} if bdist_wheel else {},
    package_data={
        "pytron": ["dependencies/*", "dependencies/**/*", "installer/*", "manifests/*"],
    },
    include_package_data=True,
    zip_safe=False,
)
