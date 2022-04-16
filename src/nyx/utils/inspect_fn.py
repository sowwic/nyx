def class_string(cls, full_path=False) -> str:
    """Get string representation of the class

    Args:
        full_path (bool, optional): Full module path to the class. Defaults to False.

    Returns:
        str: class string.
    """
    module_name = cls.__module__
    cls_name = cls.__name__
    if not full_path:
        return cls_name
    return ".".join([module_name, cls_name])
