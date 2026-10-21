"""The workshop notebook runs end to end, with and without `datos/`.

The versioned notebook is never overwritten: it is read, executed in memory and
the result is written to a temporary folder. Needs the optional ``notebook``
extra (``pip install -e ".[dev,notebook]"``); skipped if it is not installed.
Runs in a few seconds, so it is part of the default suite.
"""

from pathlib import Path

import pytest

nbformat = pytest.importorskip("nbformat")
nbclient = pytest.importorskip("nbclient")
pytest.importorskip("ipykernel")
pytest.importorskip("matplotlib")

REPO = Path(__file__).resolve().parent.parent
NOTEBOOK = REPO / "notebooks" / "skillpath.ipynb"


def execute(tmp_path, monkeypatch, datos_dir=None):
    if datos_dir is not None:
        monkeypatch.setenv("SKILLPATH_DATOS_DIR", str(datos_dir))
    else:
        monkeypatch.delenv("SKILLPATH_DATOS_DIR", raising=False)
    nb = nbformat.read(NOTEBOOK, as_version=4)
    client = nbclient.NotebookClient(
        nb, timeout=300, kernel_name="python3", resources={"metadata": {"path": str(NOTEBOOK.parent)}}
    )
    client.execute()  # raises CellExecutionError if any cell fails (including its asserts)
    nbformat.write(nb, tmp_path / "executed.ipynb")
    return nb


def stream_text(nb):
    return "\n".join(
        o.get("text", "") for c in nb.cells if c.cell_type == "code" for o in c.outputs
        if o.output_type == "stream"
    )


def count_images(nb):
    return sum(
        "image/png" in o.get("data", {})
        for c in nb.cells if c.cell_type == "code" for o in c.outputs
    )


def test_notebook_runs_end_to_end(tmp_path, monkeypatch):
    nb = execute(tmp_path, monkeypatch)
    assert count_images(nb) >= 5


def test_notebook_runs_without_datos_dir(tmp_path, monkeypatch):
    empty = tmp_path / "sin_datos"
    empty.mkdir()
    nb = execute(tmp_path, monkeypatch, datos_dir=empty)
    text = stream_text(nb)
    assert "OMITIDO" in text  # the raw-data preview is skipped, with a notice
    assert count_images(nb) >= 5  # everything essential still comes from catalog/ and reports/


def test_versioned_notebook_has_saved_outputs():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    code_cells = [c for c in nb.cells if c.cell_type == "code"]
    assert sum(bool(c.outputs) for c in code_cells) >= 20
    assert count_images(nb) >= 5
    assert not any(o.output_type == "error" for c in code_cells for o in c.outputs)
