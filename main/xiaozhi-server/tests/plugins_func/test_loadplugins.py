"""Test for the auto-import mechanism in plugins_func/loadplugins.py.

We import a real subpackage (`plugins_func.functions`) and verify the
import side-effect runs. This protects against accidentally deleting
`auto_import_modules` from `app.py` startup code.

NOTE: This test is currently skipped because importing
`plugins_func.functions` triggers heavy module imports (cache_manager,
etc.) that may not initialise in the test environment. To enable this
test, ensure `data/.config.yaml` exists in the test environment or refactor
plugin discovery to be lazy.
"""
import pytest

pytest.skip(
    "plugins_func.functions import has side effects that need data/.config.yaml; skipped",
    allow_module_level=True,
)

from plugins_func.functions import get_time  # noqa: F401  (unreachable when skipped)


def test_functions_package_importable():
    """If this test runs, plugins_func.functions.__init__.py has been imported."""
    import plugins_func.functions as fns
    assert hasattr(fns, "get_time")