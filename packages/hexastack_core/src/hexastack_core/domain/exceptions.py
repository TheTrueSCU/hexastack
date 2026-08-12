class HexastackError(Exception):
    """Base exception class for all Hexastack domain and infrastructure exceptions.

    Notes/Architectural Intent:
        Provides a common root exception type allowing applications to catch all framework-originated errors.
    """


class HexastackRegistryError(HexastackError):
    """Exception raised when registry lookup or registration failures occur.

    Notes/Architectural Intent:
        Base exception for all registry-related errors across Hexastack packages.
    """


class UnitOfWorkError(HexastackError):
    """Exception raised when a Unit of Work transaction fails during execution.

    Notes/Architectural Intent:
        Raised by UnitOfWorkPort when reraise=True is set and an exception occurs
        within the context manager boundary, wrapping the original cause.
    """
