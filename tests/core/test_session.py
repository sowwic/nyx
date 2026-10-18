import pytest

from nyx.api.v1 import Stage
from nyx.core.session import NyxSession


@pytest.fixture
def session(qapp):
    return NyxSession(config=qapp.config)


def test_find_stage_for_file(session, tmp_path):
    target = tmp_path / "a.nyx"
    stage = Stage()
    stage.export_json(target)
    session.register_stage(stage)
    assert session.find_stage_for_file(target) is stage
    assert session.find_stage_for_file(tmp_path / "other.nyx") is None
    session.unregister_stage(stage)
    assert session.find_stage_for_file(target) is None


def test_recent_files_cap_and_dedupe(session, monkeypatch):
    from nyx.core.layered_config import MAX_RECENT_FILES

    monkeypatch.setattr(session.config, "save", lambda *a, **k: None)
    for i in range(MAX_RECENT_FILES + 3):
        session.add_recent_file(f"/x/{i}.nyx")
    session.add_recent_file(f"/x/{MAX_RECENT_FILES + 2}.nyx")
    assert len(session.recent_files) == MAX_RECENT_FILES
    session.remove_recent_file(session.recent_files[0])
    assert len(session.recent_files) == MAX_RECENT_FILES - 1


def test_session_roundtrip_skips_unsaved_stages(session, tmp_path):
    saved = Stage()
    saved.export_json(tmp_path / "a.nyx")
    session.register_stage(saved)
    session.register_stage(Stage())
    session_file = tmp_path / "s.nyxsession"
    session.save_to_file(session_file)
    data = session.read_file(session_file)
    assert data["stages"] == [{"path": str(tmp_path / "a.nyx")}]
    assert data["active"] is None


def test_session_stores_state_and_active_stage(session, tmp_path):
    stage = Stage()
    stage.export_json(tmp_path / "a.nyx")
    session.register_stage(stage)
    session_file = tmp_path / "s.nyxsession"
    session.save_to_file(
        session_file, stage_state=lambda s: {"scope": "/stage"}, active_stage=stage
    )
    data = session.read_file(session_file)
    assert data["active"] == str(tmp_path / "a.nyx")
    assert data["stages"][0]["scope"] == "/stage"


def test_read_file_accepts_version_1(session, tmp_path):
    session_file = tmp_path / "old.nyxsession"
    session_file.write_text('{"version": 1, "stages": ["/x/a.nyx"]}')
    assert session.read_file(session_file)["stages"] == [{"path": "/x/a.nyx"}]
