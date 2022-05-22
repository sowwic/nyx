import pkg_resources

try:
    _version = pkg_resources.get_distribution("nyx").version
except Exception:
    _version = "unknown"
