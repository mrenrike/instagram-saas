# backend/tests/conftest.py
"""
Pytest configuration: clear the get_config lru_cache before each test so that
env-var changes are picked up correctly between test modules.
"""
import pytest


@pytest.fixture(autouse=True)
def clear_config_cache():
    """Clear the lru_cache on get_config before and after each test."""
    try:
        from backend.config import get_config
        get_config.cache_clear()
    except Exception:
        pass
    yield
    try:
        from backend.config import get_config
        get_config.cache_clear()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def reset_google_sheets_id(monkeypatch, request):
    """
    Restore GOOGLE_SHEETS_ID from the test module's own setdefault declarations.

    test_crm.py sets GOOGLE_SHEETS_ID='sheet123' but other modules set it to 'x'
    first. Because Config class attributes are frozen at first import (class-level
    assignments), we directly patch the class attribute before each test so each
    test module's intended value is honoured.
    """
    module_file = getattr(request.module, "__file__", "") or ""
    if "test_crm" in module_file:
        try:
            import backend.config as cfg_mod
            monkeypatch.setattr(cfg_mod.Config, "GOOGLE_SHEETS_ID", "sheet123")
            cfg_mod.get_config.cache_clear()
        except Exception:
            pass
