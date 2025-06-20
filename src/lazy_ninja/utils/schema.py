"""
Schema generation utilities for lazy-ninja.
"""
from typing import Type, List, Optional
from pydantic import ConfigDict, create_model, model_validator

from django.db import models
from ninja import Schema

from .base import get_pydantic_type, serialize_model_instance


def generate_schema(
    model: Type[models.Model], 
    exclude: List[str] = None, 
    optional_fields: List[str] = None, 
    update: bool = False
) -> Type[Schema]:
    """
    Generate a Pydantic schema based on a Django model.
    
    Args:
        model: The Django model class
        exclude: A list of field names to exclude from the schema
        optional_fields: A list of field names that should be marked as optional
        update: Whether this is an update schema (all fields optional)
        
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
        
        if update:
            # For update schemas, all fields are optional
            fields[field.name] = (Optional[pydantic_type], None)
        elif field.name in optional_fields or field.null:
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
