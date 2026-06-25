import json

import pytest

from embytools.envelope import read_export, read_export_meta, write_export

TYPE = "livetv-favorite-channels"


def test_round_trip(tmp_path):
    path = tmp_path / "x.json"
    data = [{"Id": "1", "Name": "CNN"}]
    write_export(path, TYPE, "http://host", data)
    assert read_export(path, TYPE) == data


def test_meta_round_trips_and_is_omitted_when_absent(tmp_path):
    path = tmp_path / "m.json"
    write_export(path, TYPE, "http://host", [], meta={"scope": "tag", "tag": "Fav"})
    data, meta = read_export_meta(path, TYPE)
    assert data == [] and meta == {"scope": "tag", "tag": "Fav"}

    plain = tmp_path / "p.json"
    write_export(plain, TYPE, "http://host", [])
    assert "meta" not in json.loads(plain.read_text())  # byte-identical to before
    assert read_export_meta(plain, TYPE) == ([], None)


def test_envelope_shape(tmp_path):
    path = tmp_path / "x.json"
    write_export(path, TYPE, "http://host", [])
    payload = json.loads(path.read_text())
    assert payload["type"] == TYPE
    assert payload["version"] == 1
    assert payload["server"] == "http://host"
    assert "exported_at" in payload


def test_creates_parent_dirs(tmp_path):
    path = tmp_path / "a" / "b" / "c.json"
    write_export(path, TYPE, "http://host", [])
    assert path.exists()


def test_type_mismatch(tmp_path):
    path = tmp_path / "x.json"
    write_export(path, "other-type", "http://host", [])
    with pytest.raises(ValueError):
        read_export(path, TYPE)


def test_non_object_json(tmp_path):
    path = tmp_path / "arr.json"
    path.write_text("[1, 2, 3]")
    with pytest.raises(ValueError):
        read_export(path, TYPE)


def test_missing_data_field(tmp_path):
    path = tmp_path / "nodata.json"
    path.write_text(json.dumps({"type": TYPE, "version": 1}))
    with pytest.raises(ValueError):
        read_export(path, TYPE)
