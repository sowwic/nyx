from importlib import metadata

try:
    _version = metadata.version("requests")
except metadata.PackageNotFoundError:
    _version = "unknown"
