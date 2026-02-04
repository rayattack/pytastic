from typing import Any, List, Dict

class PytasticError(Exception):
    """Base exception for all Pytastic errors."""
    pass

class SchemaDefinitionError(PytasticError):
    """Raised when a schema definition is invalid."""
    pass

class ValidationError(PytasticError):
    """Raised when data validation fails."""
    def __init__(self, message: str, errors: List[Dict[str, Any]] = None):
        super().__init__(message)
        self.errors = errors if errors is not None else []

    def __str__(self):
        if not self.errors:
            return super().__str__()
        
        details = "\n".join([f"  - {e['path']}: {e['message']}" for e in self.errors])
        return f"{super().__str__()}\n{details}"
