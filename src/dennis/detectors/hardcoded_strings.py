import re
from pathlib import Path
from typing import List

from ..models import Finding
from dennis.classifiers.sql import is_sql
from dennis.classifiers.url import is_url

class HardcodedStringDetector:
    name = "hardcoded-string"

    SUSPICIOUS_PATTERNS = [
        re.compile(r'print\((["\'])(.+?)\1\)'),
        re.compile(r'raise\s+\w+\((["\'])(.+?)\1\)'),
        re.compile(r'logging\.(info|warning|error|debug)\((["\'])(.+?)\2\)'),
    ]

    GENERIC_STRING = re.compile(r'(["\'])(.*?)(?<!\\)\1')

    def classify_string(self,text: str) -> str:

        if not text:
            return "empty"

        t = text.strip()
        upper = t.upper()

        # ----------------------------------------
        # URL
        # ----------------------------------------
        if t.startswith(("http://", "https://", "ftp://")):
            return "url"

        # ----------------------------------------
        # SQL (AGGRESSIVE)
        # ----------------------------------------
        if any(x in upper for x in [
            "SELECT ", "INSERT INTO", "UPDATE ", "DELETE FROM",
            "CREATE TABLE", "ALTER TABLE", "DROP TABLE"
        ]):
            return "sql"

        if (" FROM " in upper or " WHERE " in upper) and "(" in t:
            return "sql"

        # ----------------------------------------
        # CSS
        # ----------------------------------------
        if re.fullmatch(r"[a-z]+(-[a-z0-9]+)+", t):
            return "css"

        if " " in t:
            parts = t.split()
            if all(re.fullmatch(r"[a-z]+(-[a-z0-9]+)*", p) for p in parts):
                return "css"

        # ----------------------------------------
        # IDENTIFIER (THIS IS HUGE)
        # ----------------------------------------
        if re.fullmatch(r"[a-z]+[A-Za-z0-9]+", t):
            return "identifier"

        if "_" in t and t.lower() == t:
            return "identifier"

        # ----------------------------------------
        # CODE-LIKE
        # ----------------------------------------
        if any(x in t for x in ["{", "}", ";", "$", "->", "::"]):
            return "code"

        # ----------------------------------------
        # HUMAN TEXT
        # ----------------------------------------
        if " " in t and any(c.isalpha() for c in t):
            return "human"

        return "unknown"

    # --------------------------------------------------------
    # VALID STRING (ONLY HUMAN TEXT)
    # --------------------------------------------------------
    def is_valid_string(self, text: str) -> bool:
        
        kind = self.classify_string(text)

        if kind != "human":
            return False

        if len(text) < 3:
            return False

        # must contain letters
        if not any(c.isalpha() for c in text):
            return False

        # must contain space → human language
        if " " not in text:
            return False

        return True
    
    # --------------------------------------------------------
    # CSS DETECTION
    # --------------------------------------------------------


    # --------------------------------------------------------
    # GENERIC SKIP RULES (NON-HUMAN)
    # --------------------------------------------------------
    
    def should_skip(self, text: str) -> bool:

        if not text:
            return True
        
        kind = self.classify_string(text)

        if kind in {"url", "sql", "css", "identifier", "code"}:
            return True

        # --------------------------------------------------------
        # 1. URL (strong)
        # --------------------------------------------------------
        if text.startswith(("http://", "https://", "ftp://")):
            return True

        # --------------------------------------------------------
        # 2. SQL (VERY aggressive)
        # --------------------------------------------------------
        upper = text.upper()

        if any(x in upper for x in [
            "SELECT ", "INSERT INTO", "UPDATE ", "DELETE FROM",
            "CREATE TABLE", "ALTER TABLE", "DROP TABLE"
        ]):
            return True

        # also catch long SQL-like strings
        if (
            (" FROM " in upper or " WHERE " in upper or " VALUES " in upper)
            and ("(" in text and ")" in text)
        ):
            return True

        # --------------------------------------------------------
        # 3. CSS (STRONG)
        # --------------------------------------------------------
        if re.fullmatch(r"[a-z]+(-[a-z0-9]+)+", text):
            return True

        if " " in text:
            parts = text.split()

            # ALL tokens look like css classes
            if all(re.fullmatch(r"[a-z]+(-[a-z0-9]+)*", p) for p in parts):
                return True

        # --------------------------------------------------------
        # 4. PATHS / FILES
        # --------------------------------------------------------
        if "/" in text or "\\" in text:
            return True

        if text.endswith((".php", ".js", ".css", ".html", ".json")):
            return True

        # --------------------------------------------------------
        # 5. FUNCTION CALLS
        # --------------------------------------------------------
        if text.endswith("()"):
            return True

        # --------------------------------------------------------
        # 6. CAMELCASE IDENTIFIERS (BIG FIX)
        # --------------------------------------------------------
        if re.fullmatch(r"[a-z]+[A-Za-z0-9]+", text):
            return True

        # --------------------------------------------------------
        # 7. SNAKE / CONSTANTS
        # --------------------------------------------------------
        if "_" in text and text.lower() == text:
            return True

        if text.upper() == text and len(text) > 8:
            return True

        # --------------------------------------------------------
        # 8. SHORT TOKENS
        # --------------------------------------------------------
        if len(text.split()) <= 1:
            return True

        return False

    # --------------------------------------------------------
    # MAIN SCANNER
    # --------------------------------------------------------
    def scan_file(self, path: Path, lines: List[str]) -> List[Finding]:

        findings: List[Finding] = []

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()

            if stripped.startswith(("#", "//", "/*", "*","'",)):
                continue

            matched_specific = False

            # ----------------------------------------
            # 1. High-confidence patterns
            # ----------------------------------------
            for pattern in self.SUSPICIOUS_PATTERNS:
                match = pattern.search(line)

                if match:
                    text = match.groups()[-1]

                    findings.append(
                        Finding(
                            file=str(path),
                            line=idx,
                            text=text,
                            detector=self.name,
                            object_type=self.classify_string(text).upper(),
                        )
                    )

                    matched_specific = True
                    break

            if matched_specific:
                continue

            # ----------------------------------------
            # 2. Generic detection
            # ----------------------------------------
            
            from dennis.utils import (
                looks_like_binary,
                looks_like_html,
                looks_like_css,
                contains_sql_token_like
            )
            from dennis.filters.code_filter import looks_like_code as looks_like_code_filter

            for match in self.GENERIC_STRING.finditer(line):
                
                text = match.group(2).strip()

                if looks_like_binary(text):
                    continue
                    
                if self.should_skip(text):
                    continue

                if not self.is_valid_string(text):
                    continue

                if looks_like_html(text):
                    continue

                if contains_sql_token_like(text):
                    continue

                if looks_like_code_filter(text):
                    continue

                findings.append(
                    Finding(
                        file=str(path),
                        line=idx,
                        text=text,
                        detector="generic-string",
                        object_type=self.classify_string(text).upper(),
                    )
                )

        return findings
    
