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


@pytest.mark.parametrize("role", ROLES)
def test_app_runs_with_interests(role):
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.selectbox[0].select(role).run()
    at.multiselect[0].select("python").run()
    at.multiselect[1].select("tableau").select("machine learning").run()
    assert not at.exception
    table = at.table[0].value
    assert "Similitud" in table.columns and (table["Similitud"] > 0).any()
    assert not at.warning


def test_app_warns_about_unrecognized_interest():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.text_input[0].set_value("zzz qqq, tableau").run()
    assert not at.exception
    assert any("zzz qqq" in w.value for w in at.warning)
    assert not any("tableau" in w.value for w in at.warning)
