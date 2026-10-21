from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from skillpath import catalog
from skillpath.catalog import ROLES

APP = str(Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py")
ENTRY = "Inicial (estudiante o recién graduado)"


@pytest.mark.parametrize("role", ROLES)
def test_app_entry_level(role):
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.selectbox[0].select(role).run()
    assert not at.warning  # default: no entry-level warning
    experienced = at.table[0].value.copy()
    experienced_frequent = at.table[1].value.copy()

    at.radio(key="experience_level").set_value(ENTRY).run()
    assert not at.exception
    n = catalog.ENTRY_SAMPLE_SIZE[role]
    assert any(f"{n} ofertas de nivel inicial de {role}" in w.value for w in at.warning)
    assert any("muestra pequeña" in w.value for w in at.warning)
    entry = at.table[0].value
    assert len(entry) == len(experienced)
    assert not entry.equals(experienced)
    assert not at.table[1].value.equals(experienced_frequent)
    assert any("nivel inicial" in e for e in entry["Explicación"])
