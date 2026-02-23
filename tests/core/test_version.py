from nyx import version


def test_version_file_exists():
    assert version.VERSION_FILE.exists(), "VERSION file does not exist"
    assert version.__version__ != "0.0.0", "VERSION file could not be read properly"
