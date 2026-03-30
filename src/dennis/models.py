from dataclasses import dataclass

@dataclass
class Finding:
    file: str
    line: int
    text: str
    detector: str
    severity: str = "warn"

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "line": self.line,
            "text": self.text,
            "detector": self.detector,
            "severity": self.severity,
        }