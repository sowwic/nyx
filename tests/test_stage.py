from nyx.core import Stage


def test_create_empty_stage():
    stage = Stage()
    assert stage.file_path is None
    assert stage.data == {}
