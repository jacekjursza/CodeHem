from typing import Optional

from pydantic import BaseModel


class CodeElementXPathNode(BaseModel):
    """Represents a node in an XPath expression for code elements"""
    name: Optional[str] = None
    type: Optional[str] = None
    part: Optional[str] = None  # new field: "body", "def", etc.

    def __str__(self) -> str:
        """Convert to string representation"""
        result = ''
        if self.name:
            result = self.name
        if self.type:
            result += f'[{self.type}]'
        if self.part:
            result += f'[{self.part}]'
        return result

    @property
    def is_valid(self) -> bool:
        """Check if this node is valid (has a name or type or part)"""
        return bool(self.name or self.type or self.part)
