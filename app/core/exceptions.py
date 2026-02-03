class PediloException(Exception):
    """Base exception for all domain exceptions"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class EntityNotFoundError(PediloException):
    """Raised when an entity is not found in the database"""
    pass

class BusinessLogicError(PediloException):
    """Raised when a business rule is violated"""
    pass

class PermissionDeniedError(PediloException):
    """Raised when a user doesn't have permission for an action"""
    pass
