from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from skillpath.catalog import CATALOG, ROLES

APP = str(Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py")


@pytest.mark.parametrize("role", ROLES)
def test_app_runs_for_each_role(role):
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    at.selectbox[0].select(role).run()
    assert not at.exception
    assert len(at.table[0].value) == len(CATALOG)
