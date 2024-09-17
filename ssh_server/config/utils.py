# Copyright (c) 2023 nggit

__all__ = ('load_dotenv',)

import os  # noqa: E402


def load_dotenv():
    dirname = os.path.dirname(os.path.abspath(__file__))

    for filename in os.listdir(dirname):
        if not filename.lower().endswith('.env'):
            continue

        with open(os.path.join(dirname, filename)) as f:
            for line in f:
                _line = line.strip()

                if _line == '' or _line.startswith('#') or '=' not in _line:
                    continue

                key, value = _line.split('=', 1)
                _key = key.strip()
                _value = value.strip('"\'')
                var_pos = _value.find('${')

                while var_pos != -1:
                    var_len = _value.find('}', var_pos + 3)

                    if var_len == -1:
                        break

                    env_key = _value[var_pos + 2:var_len]

                    if env_key in os.environ:
                        _value = (_value[:var_pos] + os.environ[env_key] +
                                  _value[var_len + 1:])

                    var_pos = _value.find('${', var_len + 1)

                os.environ[_key] = _value
                print(f'load_dotenv: {_key}="{_value}"')
