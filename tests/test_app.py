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


def _is_cold_start_info(at):
    return any("Sin datos tuyos" in i.value for i in at.info)


def _top_frequent(role, n):
    from skillpath import LearnerProfile, recommend

    return [i.skill for i in recommend(LearnerProfile(role)).most_frequent(n)]


@pytest.mark.parametrize("role", ROLES)
def test_app_start_without_data_shows_cold_start_result(role):
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.selectbox[0].select(role).run()
    at.checkbox(key="start_empty").check().run()
    assert not at.exception
    assert _is_cold_start_info(at)
    assert len(at.table[0].value) == len(CATALOG)
    frequent = at.table[1].value
    assert len(frequent) == 10
    assert list(frequent["Habilidad"]) == _top_frequent(role, 10)


@pytest.mark.parametrize("role", ROLES)
def test_app_start_without_data_ignores_declared_skills(role):
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.selectbox[0].select(role).run()
    at.multiselect[0].select("python").run()
    at.checkbox(key="start_empty").check().run()
    assert not at.exception
    assert _is_cold_start_info(at)
    assert len(at.table[0].value) == len(CATALOG)


@pytest.mark.parametrize("role", ROLES)
def test_app_minimal_profile_is_not_cold_start(role):
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.selectbox[0].select(role).run()
    assert _is_cold_start_info(at)  # default: nothing declared
    skill = _top_frequent(role, 8)[0]
    at.checkbox(key=f"suggest_{role}_{skill}").check().run()
    assert not at.exception
    assert not _is_cold_start_info(at)
    assert skill not in list(at.table[0].value["Habilidad"])  # intermediate = mastered
    assert skill not in list(at.table[1].value["Habilidad"])
    assert len(at.table[0].value) == len(CATALOG) - 1


def test_app_minimal_profile_with_multiselect_skill():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.multiselect[0].select("tableau").run()
    assert not at.exception
    assert not _is_cold_start_info(at)
    assert "tableau" not in list(at.table[0].value["Habilidad"])
