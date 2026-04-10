# src/dennis/plugins/python.py

def transform_line(line: str, reverse_mapping: dict):
    for text, key in reverse_mapping.items():

        if text not in line:
            continue

        if f'"{text}"' in line:
            return (
                line.replace(f'"{text}"', f'messages["{key}"]'),
                key
            )

        elif f"'{text}'" in line:
            return (
                line.replace(f"'{text}'", f'messages["{key}"]'),
                key
            )

    return None, None