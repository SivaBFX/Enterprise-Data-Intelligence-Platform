"""Shared lightweight stubs for offline unit testing of Streamlit/Databricks modules."""

import importlib.util
from pathlib import Path
import sys
import types

APP_DIR = Path(__file__).resolve().parent.parent / "src" / "app"


class _DummyContext:
    """No-op context manager for st.columns, st.container, st.expander, st.spinner."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def install_test_stubs() -> types.ModuleType:
    """Install minimal streamlit and databricks stubs if not already present."""
    if str(APP_DIR) not in sys.path:
        sys.path.insert(0, str(APP_DIR))

    existing_st = sys.modules.get("streamlit")
    if existing_st is not None and hasattr(existing_st, "captured_links"):
        return existing_st

    st_stub = types.ModuleType("streamlit")
    st_stub.session_state = {}
    st_stub.captured_links = []
    st_stub.captured_markdown = []
    st_stub.set_page_config = lambda **kw: None
    st_stub.cache_data = lambda **kw: (lambda fn: fn)
    st_stub.markdown = lambda body, **kw: st_stub.captured_markdown.append(body)
    st_stub.caption = lambda *a, **kw: None
    st_stub.divider = lambda: None
    st_stub.header = lambda *a, **kw: None
    st_stub.subheader = lambda *a, **kw: None
    st_stub.text_input = lambda *a, **kw: ""
    st_stub.selectbox = lambda label, options, **kw: options[0]
    st_stub.checkbox = lambda *a, **kw: False
    st_stub.button = lambda *a, **kw: False
    st_stub.download_button = lambda *a, **kw: None
    st_stub.form = lambda *a, **kw: _DummyContext()
    st_stub.form_submit_button = lambda *a, **kw: False
    st_stub.line_chart = lambda *a, **kw: None
    st_stub.bar_chart = lambda *a, **kw: None
    st_stub.dataframe = lambda *a, **kw: None
    st_stub.code = lambda *a, **kw: None
    st_stub.warning = lambda *a, **kw: None
    st_stub.error = lambda *a, **kw: None
    st_stub.exception = lambda *a, **kw: None
    st_stub.stop = lambda: (_ for _ in ()).throw(RuntimeError("st.stop"))
    st_stub.rerun = lambda: None
    st_stub.page_link = lambda page, label=None, icon=None: st_stub.captured_links.append(page)
    st_stub.spinner = lambda *a, **kw: _DummyContext()
    st_stub.expander = lambda *a, **kw: _DummyContext()
    st_stub.container = lambda **kw: _DummyContext()
    st_stub.columns = lambda spec: [
        _DummyContext() for _ in range(spec if isinstance(spec, int) else len(spec))
    ]
    st_stub.tabs = lambda labels: [_DummyContext() for _ in labels]
    sys.modules["streamlit"] = st_stub

    db_mod = types.ModuleType("databricks")
    db_sql = types.ModuleType("databricks.sql")
    db_sql.connect = lambda **kw: None
    db_sdk = types.ModuleType("databricks.sdk")
    db_sdk_core = types.ModuleType("databricks.sdk.core")
    db_sdk_core.Config = lambda: types.SimpleNamespace(
        host="https://example.cloud.databricks.com",
        authenticate=lambda: {},
    )
    db_sdk.WorkspaceClient = object
    db_mod.sql = db_sql
    db_mod.sdk = db_sdk
    sys.modules["databricks"] = db_mod
    sys.modules["databricks.sql"] = db_sql
    sys.modules["databricks.sdk"] = db_sdk
    sys.modules["databricks.sdk.core"] = db_sdk_core

    return st_stub


def load_app_module(relative_path: str, module_name: str):
    """Load an app or page Python file dynamically for unit testing."""
    target = APP_DIR / relative_path
    spec = importlib.util.spec_from_file_location(module_name, target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
