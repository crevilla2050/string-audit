from dataclasses import dataclass

@dataclass
class Finding:
    file: str
    line: int
    text: str
    detector: str
    object_type: str = "STRING"
    severity: str = "warn"

    def to_dict(self) -> dict:
        return {
            "type": self.object_type,
            "file": self.file,
            "line": self.line,
            "text": self.text,
            "detector": self.detector,
            "severity": self.severity,
        }