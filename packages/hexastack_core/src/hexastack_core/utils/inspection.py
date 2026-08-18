import inspect
from dataclasses import is_dataclass
from typing import Any

from pydantic import BaseModel

__all__ = [
    "extract_dto_fields",
    "inspect_model_parameters",
]


def extract_dto_fields(source: Any, target_cls: type[Any]) -> dict[str, Any]:
    """Extract matching fields from an arbitrary source object, dictionary, or protobuf message.

    Notes/Architectural Intent:
        Enables seamless DTO instantiation across transport layers (Protobuf, HTTP request, CLI).

    Args:
        source: Source data payload (Dict, Protobuf message, or object).
        target_cls: Target DTO or class to extract fields for.

    Returns:
        Dictionary of extracted field key-value pairs matching target_cls.
    """
    data: dict[str, Any] = {}

    if hasattr(source, "DESCRIPTOR"):
        # Protobuf Message object
        for field in source.DESCRIPTOR.fields:
            data[field.name] = getattr(source, field.name)
    elif isinstance(source, dict):
        data = dict(source)
    else:
        # Fallback attribute copy
        if is_dataclass(target_cls):
            for f in target_cls.__dataclass_fields__:  # type: ignore[attr-defined]
                if hasattr(source, f):
                    data[f] = getattr(source, f)
        elif isinstance(target_cls, type) and issubclass(target_cls, BaseModel):
            for f in target_cls.model_fields:
                if hasattr(source, f):
                    data[f] = getattr(source, f)

    return data


def inspect_model_parameters(model_cls: type[Any]) -> list[inspect.Parameter]:
    """Extract inspect.Parameter definitions from dataclasses, Pydantic models, or callables.

    Notes/Architectural Intent:
        Provides a unified parameter reflection utility across presentation adapters
        (CLI, MCP, gRPC) for dynamic schema generation and validation.

    Args:
        model_cls: Class or callable to inspect.

    Returns:
        List of inspect.Parameter objects.
    """
    params: list[inspect.Parameter] = []

    if is_dataclass(model_cls):
        fields = model_cls.__dataclass_fields__  # type: ignore[attr-defined]
        for f_name, f_info in fields.items():
            default = (
                inspect.Parameter.empty
                if f_info.default is f_info.default_factory
                else f_info.default
            )
            params.append(
                inspect.Parameter(
                    name=f_name,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    default=default,
                    annotation=f_info.type,
                )
            )
    elif isinstance(model_cls, type) and issubclass(model_cls, BaseModel):
        for f_name, f_info in model_cls.model_fields.items():
            default = (
                inspect.Parameter.empty if f_info.is_required() else f_info.default
            )
            params.append(
                inspect.Parameter(
                    name=f_name,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    default=default,
                    annotation=f_info.annotation or Any,
                )
            )
    elif callable(model_cls):
        sig = inspect.signature(model_cls)
        params.extend(sig.parameters.values())

    return params
