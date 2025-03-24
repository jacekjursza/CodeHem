from typing import Optional, Any

from pydantic import BaseModel


class CodeRange(BaseModel):
    """Represents a range in source code (line numbers)"""
    start_line: int
    end_line: int
    start_column: Optional[int] = None
    end_column: Optional[int] = None
    node: Any = None
    model_config = {'arbitrary_types_allowed': True}
