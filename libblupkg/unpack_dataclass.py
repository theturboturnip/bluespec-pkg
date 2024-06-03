from dataclasses import MISSING, fields, is_dataclass
from types import NoneType
from typing import Type, TypeVar, Union, get_args, get_origin


T = TypeVar("T", bound="DataclassInstance") # type: ignore

def unpack_dataclass(ty: Type[T], args_dict) -> T:
    if not isinstance(args_dict, dict):
        raise ValueError(f"Structures of type '{ty}' must be built from a dictionary, got {args_dict} instead")

    for field in fields(ty):
        field_required = (field.default == MISSING) and (field.default_factory == MISSING)
       
        if field.name in args_dict:
            val = args_dict[field.name]

            if get_origin(field.type) is Union:
                assert len(get_args(field.type)) == 2
                args = list(get_args(field.type))
                args.remove(NoneType)
                field_type = args[0]
            else:
                field_type = field.type

            if is_dataclass(field_type):
                val = unpack_dataclass(field_type, val)
                args_dict[field.name] = val
            if not isinstance(val, get_origin(field_type) or field_type): # type:ignore
                raise ValueError(f"Structures of type '{ty}' requires the field '{field.name}' to be of type '{field_type}', but got {val} instead")
        elif field_required:
            raise ValueError(f"Structures of type '{ty}' requires a field '{field.name}' but none was supplied!")

    return ty(**args_dict)
