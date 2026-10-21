import pytest

from nyx.plugins.functions.dict_operations import operations as dicts
from nyx.plugins.functions.file_operations import operations as files
from nyx.plugins.functions.json_operations import operations as js
from nyx.plugins.functions.list_operations import operations as lists
from nyx.plugins.functions.string_operations import operations as strings
from nyx.plugins.functions.system_operations import operations as system


@pytest.mark.parametrize(
    "func, args, expected",
    [
        (strings.join, (["a", 1], "-"), "a-1"),
        (strings.split, ("a b c",), ["a", "b", "c"]),
        (strings.replace, ("aXb", "X", "-"), "a-b"),
        (strings.regex_replace, ("a1b22", r"\d+", "#"), "a#b#"),
        (strings.regex_match, ("abc", "b"), True),
        (strings.regex_find_all, ("a1b22", r"\d+"), ["1", "22"]),
        (strings.format_text, ("{a}-{b}", {"a": 1, "b": 2}), "1-2"),
        (strings.strip, ("  x ",), "x"),
        (strings.strip, ("--x--", "-"), "x"),
        (strings.substring, ("hello", 1), "ello"),
        (strings.substring, ("hello", 1, 3), "el"),
        (strings.pad_left, ("7", 3, "0"), "007"),
        (strings.find, ("abc", "z"), -1),
        (lists.append, ([1], 2), [1, 2]),
        (lists.insert, ([1, 3], 1, 2), [1, 2, 3]),
        (lists.remove_at, ([1, 2, 3], 0), [2, 3]),
        (lists.remove_item, ([1, 2, 1], 1), [2, 1]),
        (lists.set_item, ([1, 2], 0, 9), [9, 2]),
        (lists.slice_list, ([1, 2, 3], 1), [2, 3]),
        (lists.slice_list, ([1, 2, 3], 0, 2), [1, 2]),
        (lists.index_of, ([1, 2], 5), -1),
        (lists.sort, ([3, 1, 2], True), [3, 2, 1]),
        (lists.unique, ([1, 2, 1, 3, 2],), [1, 2, 3]),
        (lists.flatten, ([[1], [2, 3]],), [1, 2, 3]),
        (lists.number_range, (0, 6, 2), [0, 2, 4]),
        (lists.zip_lists, ([1, 2], ["a", "b"]), [[1, "a"], [2, "b"]]),
        (dicts.get_value, ({"a": 1}, "b", 0), 0),
        (dicts.set_value, ({"a": 1}, "b", 2), {"a": 1, "b": 2}),
        (dicts.remove_key, ({"a": 1, "b": 2}, "a"), {"b": 2}),
        (dicts.items, ({"a": 1},), [["a", 1]]),
        (dicts.from_items, ([["a", 1]],), {"a": 1}),
        (dicts.merge, ({"a": 1}, {"a": 2}), {"a": 2}),
        (dicts.invert, ({"a": 1},), {1: "a"}),
        (dicts.pick, ({"a": 1, "b": 2}, ["a", "z"]), {"a": 1}),
        (js.parse_json, ('{"a": [1]}',), {"a": [1]}),
        (js.to_json, ({"a": 1},), '{"a": 1}'),
        (js.is_valid_json, ("{",), False),
        (js.get_json_value, ({"a": [{"b": 5}]}, "a.0.b"), 5),
        (js.get_json_value, ({"a": 1}, "x.y", "none"), "none"),
        (files.join_path, ("a", "b"), "a/b"),
        (files.file_name, ("/x/y.txt",), "y.txt"),
        (files.file_stem, ("/x/y.txt",), "y"),
        (files.file_extension, ("/x/y.txt",), ".txt"),
        (files.parent_folder, ("/x/y.txt",), "/x"),
        (system.get_env, ("NYX_SURELY_NOT_SET", "d"), "d"),
    ],
)
def test_operations(func, args, expected):
    assert func(*args) == expected


def test_list_operations_do_not_change_the_input():
    items = [3, 1, 2]
    lists.sort(items)
    lists.append(items, 4)
    lists.reverse(items)
    assert items == [3, 1, 2]


def test_file_round_trip(tmp_path):
    folder = files.make_folder(str(tmp_path / "a" / "b"))
    path = files.write_text(files.join_path(folder, "f.txt"), "one\ntwo")
    files.append_text(path, "\nthree")

    assert files.file_exists(path)
    assert files.folder_exists(folder)
    assert files.read_lines(path) == ["one", "two", "three"]
    assert files.list_folder(folder) == ["f.txt"]
    copy = files.copy_file(path, str(tmp_path / "copy.txt"))
    assert files.read_text(copy) == files.read_text(path)
    assert files.delete_file(copy) is True
    assert files.delete_file(copy) is False
    assert files.delete_folder(str(tmp_path / "a")) is True


def test_json_file_round_trip(tmp_path):
    path = js.write_json_file(str(tmp_path / "d.json"), {"a": [1, 2]})
    assert js.read_json_file(path) == {"a": [1, 2]}


def test_system_operations(monkeypatch):
    system.set_env("NYX_TEST_VAR", "1")
    assert system.has_env("NYX_TEST_VAR")
    assert system.get_env("NYX_TEST_VAR") == "1"
    assert system.cpu_count() >= 1
    assert system.run_command([system.python_executable(), "-c", "print(5)"]).strip() == "5"
    with pytest.raises(Exception):
        system.run_command([system.python_executable(), "-c", "raise SystemExit(1)"])
