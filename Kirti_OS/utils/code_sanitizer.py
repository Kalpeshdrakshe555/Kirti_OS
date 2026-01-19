
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class SanitizedCode:
    code: str
    language: Optional[str]
    all_blocks: List[str]
    source_had_fences: bool

class CodeSanitizer:
    FENCE_PATTERN = re.compile(r"```(?:\s*(?P<lang>[a-zA-Z0-9_+-]+))?\s*(?P<code>[\s\S]*?)```", re.MULTILINE)
    FILLER_PREFIXES = ("here is the code", "here's the code", "the code is as follows", "example:", "sure", "certainly")

    @classmethod
    def extract_code_blocks(cls, text: str) -> List[str]:
        if not text: return []
        blocks = []
        for match in cls.FENCE_PATTERN.finditer(text):
            code = match.group("code") or ""
            code = cls._strip_filler_lines(code)
            if code.strip(): blocks.append(code.strip())
        return blocks

    @classmethod
    def sanitize(cls, raw_text: str) -> SanitizedCode:
        if not raw_text: return SanitizedCode("", "python", [], False)
        blocks = cls.extract_code_blocks(raw_text)
        if blocks:
            # Pick largest block
            primary = max(blocks, key=len)
            return SanitizedCode(primary, "python", blocks, True)
        
        # Fallback: Return raw text stripped
        return SanitizedCode(cls._strip_filler_lines(raw_text), "python", [], False)

    @classmethod
    def _strip_filler_lines(cls, code: str) -> str:
        lines = code.splitlines()
        cleaned = []
        for line in lines:
            if not any(line.strip().lower().startswith(p) for p in cls.FILLER_PREFIXES):
                cleaned.append(line)
        return "\n".join(cleaned)
