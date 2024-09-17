# Copyright (c) 2023 nggit

__all__ = ('validate_name',)

ALLOWED_CHARS = set('abcdefghijklmnopqrstuvwxyz0123456789-.')


def validate_name(name):
    if not 4 < len(name) < 256:
        return False

    if not set(name).issubset(ALLOWED_CHARS):
        return False

    if name.strip('-.') != name:
        return False

    for sub in name.split('.'):
        if len(sub) > 63:
            return False

    return True
