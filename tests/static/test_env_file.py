import os

from nyx.static import env_file


def test_parse_handles_comments_export_and_quotes(monkeypatch):
    monkeypatch.setenv("NYX_TEST_BASE", "base")
    text = (
        "# comment\n"
        "\n"
        "A=1\n"
        "export B = two \n"
        'C="$NYX_TEST_BASE/c"\n'
        "D='$NYX_TEST_BASE'\n"
        "E=x=y\n"
        "broken\n"
        "=novalue\n"
    )
    assert env_file.parse_env_file(text) == {
        "A": "1",
        "B": "two",
        "C": "base/c",
        "D": "$NYX_TEST_BASE",
        "E": "x=y",
    }


def test_load_sets_variables_and_later_lines_see_earlier_ones(tmp_path, monkeypatch):
    monkeypatch.delenv("NYX_TEST_A", raising=False)
    monkeypatch.delenv("NYX_TEST_B", raising=False)
    path = tmp_path / ".env"
    path.write_text("NYX_TEST_A=one\nNYX_TEST_B=$NYX_TEST_A/two\n")
    assert env_file.load_env_file(path) == {
        "NYX_TEST_A": "one",
        "NYX_TEST_B": "one/two",
    }
    assert os.environ["NYX_TEST_B"] == "one/two"
