def update(obj: object, attrs: dict) -> None:
    """Updates an object's attributes from a dictionary.
    Uses direct __dict__ modification if possible for performance,
    otherwise falls back to setattr for objects without __dict__ (e.g., __slots__).

    Args:
        obj: The object whose attributes will be updated.
        attrs: Dictionary of attribute names and values.

    Raises:
        AttributeError: If an attribute cannot be set (optional, see notes).
    """
    if hasattr(obj, '__dict__'):
        obj.__dict__.update(attrs)
    else:
        for key, value in attrs.items():
            try:
                setattr(obj, key, value)
            except AttributeError as e:
                raise AttributeError(
                    f"Cannot set attribute '{key}' on object '{obj}': {e}"
                )
