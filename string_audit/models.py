from dataclasses import dataclass

@dataclass
class Finding:
    file: str
    line: int
    text: str
    detector: str
    severity: str = "warn"
