from typing import Any, Dict, Optional, Tuple, Type, TypeVar, TypedDict, Union, cast, get_args

from pydantic import BaseModel
from pydantic.version import VERSION as PYDANTIC_VERSION
from typing_extensions import get_origin

__all__ = ("JsonSchemaValue", "model_dump", "model_dump_json", "type2schema", "evaluate_forwardref")

PYDANTIC_V1 = PYDANTIC_VERSION.startswith("1.")

T = TypeVar("T")

if not PYDANTIC_V1:
    from pydantic import TypeAdapter
    from pydantic._internal._typing_extra import eval_type_lenient as evaluate_forwardref
    from pydantic.json_schema import JsonSchemaValue


    def type2schema(t: Optional[type]) -> JsonSchemaValue:
        """Convert a type to a JSON schema

        Args:
            t (Type): The type to convert

        Returns:
            JsonSchemaValue: The JSON schema
        """
        return TypeAdapter(t).json_schema()

    def model_dump(model: BaseModel) -> Dict[str, Any]:
        """Convert a pydantic model to a dict

        Args:
            model (BaseModel): The model to convert

        Returns:
            Dict[str, Any]: The dict representation of the model

        """
        return model.model_dump()

    def model_dump_json(model: BaseModel) -> str:
        """Convert a pydantic model to a JSON string

        Args:
            model (BaseModel): The model to convert

        Returns:
            str: The JSON string representation of the model
        """
        return model.model_dump_json()

    def to_typed_dict(obj: Dict[str, Any], t: Type[T]) -> T:
        """Validate a dictionary against a TypedDict

        Args:
            obj (Dict[str, Any]): The dictionary to validate
            t (Type[T]): The TypedDict type to validate against
        """
        validator = TypeAdapter(t)
        return validator.validate_python(obj)



# Remove this once we drop support for pydantic 1.x
else:  # pragma: no cover
    from pydantic import schema_of, create_model_from_typeddict
    from pydantic.typing import evaluate_forwardref as evaluate_forwardref # type: ignore[no-redef]

    JsonSchemaValue = Dict[str, Any] # type: ignore[misc]

    def type2schema(t: Optional[type]) -> JsonSchemaValue:
        """Convert a type to a JSON schema

        Args:
            t (Type): The type to convert

        Returns:
            JsonSchemaValue: The JSON schema
        """
        if PYDANTIC_V1:
            if t is None:
                return {"type": "null"}
            elif get_origin(t) is Union:
                return {"anyOf": [type2schema(tt) for tt in get_args(t)]}
            elif get_origin(t) in [Tuple, tuple]:
                prefixItems = [type2schema(tt) for tt in get_args(t)]
                return {
                    "maxItems": len(prefixItems),
                    "minItems": len(prefixItems),
                    "prefixItems": prefixItems,
                    "type": "array",
                }

        d = schema_of(t)
        if "title" in d:
            d.pop("title")
        if "description" in d:
            d.pop("description")

        return d

    def model_dump(model: BaseModel) -> Dict[str, Any]:
        """Convert a pydantic model to a dict

        Args:
            model (BaseModel): The model to convert

        Returns:
            Dict[str, Any]: The dict representation of the model

        """
        return model.dict()

    def model_dump_json(model: BaseModel) -> str:
        """Convert a pydantic model to a JSON string

        Args:
            model (BaseModel): The model to convert

        Returns:
            str: The JSON string representation of the model
        """
        return model.json()

    def to_typed_dict(obj: Dict[str, Any], t: Type[T]) -> T:
        """Validate a dictionary against a TypedDict

        Args:
            obj (Dict[str, Any]): The dictionary to validate
            t (Type[T]): The TypedDict type to validate against
        """
        return cast(T, create_model_from_typeddict(t)(**obj).dict()) # type: ignore[operator]
