import pytest

from nyx.plugins.functions.dict_operations import operations as dicts
from nyx.plugins.functions.encoding_operations import operations as encoding
from nyx.plugins.functions.file_operations import operations as files
from nyx.plugins.functions.datetime_operations import operations as dt
from nyx.plugins.functions.path_operations import operations as paths
from nyx.plugins.functions.random_operations import operations as rnd
from nyx.plugins.functions.regex_operations import operations as rx
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
        (paths.join_path, ("a", "b"), "a/b"),
        (paths.file_name, ("/x/y.txt",), "y.txt"),
        (paths.file_stem, ("/x/y.txt",), "y"),
        (paths.file_extension, ("/x/y.txt",), ".txt"),
        (paths.parent_folder, ("/x/y.txt",), "/x"),
        (system.get_env, ("NYX_SURELY_NOT_SET", "d"), "d"),
        (rx.replace, ("a1b22", r"\d+", "#"), "a#b#"),
        (rx.replace, ("Ab", "a", "x", True), "xb"),
        (rx.is_match, ("abc", "b"), True),
        (rx.is_match, ("abc", "B"), False),
        (rx.is_match, ("abc", "B", True), True),
        (rx.is_full_match, ("abc", "b"), False),
        (rx.find_all, ("a1b22", r"\d+"), ["1", "22"]),
        (rx.find_first, ("a1b22", r"\d+"), "1"),
        (rx.find_first, ("k=v", r"(\w)=(\w)", 2), "v"),
        (rx.find_first, ("abc", r"\d"), ""),
        (rx.groups, ("k=v", r"(\w)=(\w)"), ["k", "v"]),
        (rx.groups, ("abc", r"(\d)"), []),
        (rx.count_matches, ("a1b22", r"\d"), 3),
        (rx.split, ("a1b22c", r"\d+"), ["a", "b", "c"]),
        (rx.escape, ("a.b",), r"a\.b"),
        (rx.is_valid_pattern, ("(",), False),
        (rx.is_valid_pattern, ("a+",), True),
        (paths.with_name, ("/x/y.txt", "z.md"), "/x/z.md"),
        (paths.with_extension, ("/x/y.txt", ".md"), "/x/y.md"),
        (paths.relative_to, ("/x/y/z", "/x"), "y/z"),
        (paths.path_parts, ("/x/y",), ["/", "x", "y"]),
        (paths.is_absolute, ("x",), False),
        (paths.matches_pattern, ("/x/y.py", "*.py"), True),
        (dt.format_datetime, ("2026-10-21T18:15:00", "%d.%m.%Y"), "21.10.2026"),
        (dt.parse_datetime, ("21.10.2026", "%d.%m.%Y"), "2026-10-21T00:00:00"),
        (dt.add_time, ("2026-10-21T18:00:00", 1, 2), "2026-10-22T20:00:00"),
        (dt.add_time, ("2026-10-21T18:00:00", 0, 0, -30), "2026-10-21T17:30:00"),
        (dt.seconds_between, ("2026-10-21T18:00:00", "2026-10-21T18:01:30"), 90),
        (dt.days_between, ("2026-10-21T23:59:00", "2026-10-23T00:01:00"), 2),
        (dt.year, ("2026-10-21T18:00:00",), 2026),
        (dt.month, ("2026-10-21T18:00:00",), 10),
        (dt.day, ("2026-10-21T18:00:00",), 21),
        (dt.hour, ("2026-10-21T18:05:09",), 18),
        (dt.minute, ("2026-10-21T18:05:09",), 5),
        (dt.second, ("2026-10-21T18:05:09",), 9),
        (dt.weekday, ("2026-10-21",), 2),
        (dt.weekday_name, ("2026-10-21",), "Wednesday"),
        (dt.day_of_year, ("2026-02-01",), 32),
        (dt.is_leap_year, (2028,), True),
        (dt.is_leap_year, (2026,), False),
        (dt.days_in_month, (2028, 2), 29),
        (dt.to_timestamp, ("1970-01-02T00:00:00",), 86400),
        (dt.from_timestamp, (86400,), "1970-01-02T00:00:00"),
        (encoding.md5, ("abc",), "900150983cd24fb0d6963f7d28e17f72"),
        (
            encoding.sha256,
            ("abc",),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        ),
        (encoding.sha1, ("abc",), "a9993e364706816aba3e25717850c26c9cd0d89d"),
        (encoding.base64_encode, ("héllo",), "aMOpbGxv"),
        (encoding.base64_decode, ("aMOpbGxv",), "héllo"),
        (encoding.hex_encode, ("hi",), "6869"),
        (encoding.hex_decode, ("6869",), "hi"),
        (encoding.url_encode, ("a b/c",), "a%20b%2Fc"),
        (encoding.url_decode, ("a%20b%2Fc",), "a b/c"),
        (encoding.html_escape, ("<a&b>",), "&lt;a&amp;b&gt;"),
        (encoding.html_unescape, ("&lt;a&amp;b&gt;",), "<a&b>"),
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
    path = files.write_text(paths.join_path(folder, "f.txt"), "one\ntwo")
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
    assert (
        system.run_command([system.python_executable(), "-c", "print(5)"]).strip() == "5"
    )
    with pytest.raises(Exception):
        system.run_command([system.python_executable(), "-c", "raise SystemExit(1)"])


def test_create_file(tmp_path):
    path = str(tmp_path / "new" / "dir" / "f.txt")

    assert files.create_file(path) is True
    assert files.file_exists(path)
    with pytest.raises(ValueError):
        files.create_file(path)
    assert files.create_file(path, exists_ok=True) is False


def test_create_file_without_parent_folders_fails(tmp_path):
    with pytest.raises(FileNotFoundError):
        files.create_file(str(tmp_path / "a" / "b" / "f.txt"), parent_dirs=False)


def test_hmac_and_hash_file(tmp_path):
    assert encoding.hmac_sha256("data", "key") == (
        "5031fe3d989c6d1537a013fa6e739da23463fdaec3b70137d828e36ace221bd0"
    )
    path = files.write_text(str(tmp_path / "f.txt"), "abc")
    assert encoding.hash_file(path) == encoding.sha256("abc")
    assert encoding.hash_file(path, "md5") == encoding.md5("abc")


def test_datetime_now_functions_return_parseable_text():
    import datetime

    for moment in (dt.now(), dt.utc_now(), dt.today()):
        datetime.datetime.fromisoformat(moment)


def test_random_functions_stay_in_range():
    rnd.set_seed(1)
    assert all(0 <= rnd.random_float() < 1 for _ in range(50))
    assert all(3 <= rnd.random_int(3, 5) <= 5 for _ in range(50))
    assert all(1.0 <= rnd.random_uniform(1, 2) <= 2.0 for _ in range(50))
    assert rnd.random_bool(1.0) is True
    assert rnd.random_bool(0.0) is False
    assert rnd.random_choice([7]) == 7
    assert sorted(rnd.shuffle([3, 1, 2])) == [1, 2, 3]
    assert len(set(rnd.random_sample([1, 2, 3, 4], 3))) == 3
    assert len(rnd.random_string(12)) == 12
    assert set(rnd.random_string(20, "ab")) <= {"a", "b"}
    assert len(rnd.random_uuid()) == 36
    assert isinstance(rnd.random_gauss(), float)


def test_random_seed_makes_values_repeatable():
    rnd.set_seed(42)
    first = [rnd.random_int(0, 1000) for _ in range(5)]
    rnd.set_seed(42)
    assert [rnd.random_int(0, 1000) for _ in range(5)] == first


def test_absolute_path_expands_and_resolves(tmp_path):
    assert paths.absolute_path(str(tmp_path / "a" / ".." / "b")) == str(
        (tmp_path / "b").resolve()
    )
    assert not paths.expand_user("~").startswith("~")
