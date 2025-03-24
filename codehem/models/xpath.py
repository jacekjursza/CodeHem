from typing import Optional

from pydantic import BaseModel


class CodeElementXPathNode(BaseModel):
    """Represents a node in an XPath expression for code elements"""
    name: Optional[str] = None
    type: Optional[str] = None

    def __str__(self) -> str:
        """Convert to string representation"""
        result = ""

        # Add name if present
        if self.name:
            result = self.name

        # Add type if present
        if self.type:
            result += f"[{self.type}]"

        return result

    @property
    def is_valid(self) -> bool:
        """Check if this node is valid (has a name or type)"""
        return bool(self.name) or bool(self.type)
