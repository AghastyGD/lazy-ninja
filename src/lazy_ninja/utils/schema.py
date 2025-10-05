"""
Schema generation utilities for lazy-ninja.
"""
from typing import Type, List, Optional, Any, Dict, Union
from pydantic import ConfigDict, create_model, model_validator

from django.db import models
from ninja import Schema

from .base import get_pydantic_type, serialize_model_instance


def generate_schema(
    model: Type[models.Model], 
    exclude: List[str] = None, 
    optional_fields: List[str] = None, 
    update: bool = False,
    allow_nested_relations: bool = False,
) -> Type[Schema]:
    """
    Generate a Pydantic schema based on a Django model.
    
    Args:
        model: The Django model class
        exclude: A list of field names to exclude from the schema
        optional_fields: A list of field names that should be marked as optional
        update: Whether this is an update schema (all fields optional)
        allow_nested_relations: When True, foreign key fields accept nested dictionaries
                               that will be processed into related instances.
        
    Returns:
        A dynamically created Pydantic schema class
        
    Notes:
        - Fields listed in `optional_fields` or with null=True in the Django model are set as Optional
        - A root validator is added to preprocess the input using `serialize_model_instance`
    """
    exclude = exclude or []
    optional_fields = optional_fields or []
    
    fields = {}
    for field in model._meta.fields:
        if field.name in exclude:
            continue
            
        pydantic_type = get_pydantic_type(field)

        if allow_nested_relations and isinstance(field, models.ForeignKey):
            pydantic_type = Union[Dict[str, Any], pydantic_type]
        
        is_optional_field = (
            field.name in optional_fields
            or field.null
            or getattr(field, "blank", False)
        )

        if update:
            # For update schemas, all fields are optional
            fields[field.name] = (Optional[pydantic_type], None)
        elif is_optional_field:
            # Mark field as optional if explicitly specified or Django field allows null
            fields[field.name] = (Optional[pydantic_type], None)
        else:
            # Required field
            fields[field.name] = (pydantic_type, ...)
    
    class DynamicSchema(Schema):
        @model_validator(mode="before")
        def pre_serialize(cls, values):
            """
            Pre-root validator that converts a Django model instance into a dict
            using our serialize_model_instance function.
            """
            if hasattr(values, "_meta"):
                return serialize_model_instance(values)
            return values
        
        model_config = ConfigDict(form_attributes=True)

    schema = create_model(
        model.__name__ + "Schema",
        __base__=DynamicSchema,
        **fields
    )
    
    return schema
