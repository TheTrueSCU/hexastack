from hexastack_core.domain.exceptions import HexastackError
from hexastack_grpc.domain.exceptions import (
    GrpcError,
    RpcExecutionError,
    ServiceRegistrationError,
)


def test_grpc_exceptions():
    err = ServiceRegistrationError("Failed to register servicer")
    assert isinstance(err, GrpcError)
    assert isinstance(err, HexastackError)
    assert str(err) == "Failed to register servicer"

    rpc_err = RpcExecutionError("RPC failed")
    assert isinstance(rpc_err, GrpcError)
