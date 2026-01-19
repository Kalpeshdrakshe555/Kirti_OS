
import ast
from dataclasses import dataclass
from typing import Optional

@dataclass
class SyntaxCheckResult:
    ok: bool
    error: Optional[str] = None

class SyntaxGuard:
    @staticmethod
    def validate(code: str, filename: str = "<string>") -> SyntaxCheckResult:
        try:
            ast.parse(code, filename=filename, mode="exec")
            return SyntaxCheckResult(ok=True)
        except SyntaxError as e:
            return SyntaxCheckResult(ok=False, error=f"Line {e.lineno}: {e.msg}")
        except Exception as e:
            return SyntaxCheckResult(ok=False, error=str(e))
