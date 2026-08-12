from hexastack_core.domain.exceptions import HexastackError


class GrpcError(HexastackError):
    """Base exception for all gRPC presentation layer errors.

    Notes/Architectural Intent:
        Inherits from HexastackError to maintain unified error hierarchy across the framework.
    """


class ServiceRegistrationError(GrpcError):
    """Exception raised when a gRPC servicer fails registration or lacks a valid add_to_server callback."""


class RpcExecutionError(GrpcError):
    """Exception raised when an RPC handler execution fails during dispatch."""


__all__ = [
    "GrpcError",
    "RpcExecutionError",
    "ServiceRegistrationError",
]
