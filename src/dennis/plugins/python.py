# src/dennis/plugins/python.py

def transform_line(line: str, reverse_mapping: dict):
    new_line = line
    token_used = None

    for text, key in reverse_mapping.items():
        if f'"{text}"' in new_line:
            new_line = new_line.replace(f'"{text}"', f'messages["{key}"]')
            token_used = key
        elif f"'{text}'" in new_line:
            new_line = new_line.replace(f"'{text}'", f'messages["{key}"]')
            token_used = key

    if token_used:
        return new_line, token_used

    return None, None