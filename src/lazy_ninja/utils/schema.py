"""
Schema generation utilities for lazy-ninja.
"""
from typing import Type, List, Optional, Any, Dict, cast
from pydantic import BaseModel, ConfigDict, create_model, model_validator

from django.db import models
from ninja import Schema

from .base import get_pydantic_type, serialize_model_instance


def generate_schema(
    model: Type[models.Model],
    exclude: Optional[List[str]] = None,
    optional_fields: Optional[List[str]] = None,
    update: bool = False,
) -> Type[BaseModel]:
    """Generate a Pydantic schema based on a Django model.
    
    Args:
        model: Django model class
        exclude: List of field names to exclude from schema
        optional_fields: List of field names that should be optional
        update: Whether this is an update schema (all fields optional)
        
    Returns:
        Dynamically created Pydantic schema class
        
    Note on typing:
        The return type is dynamically created and cannot be fully
        type-checked. Use type: ignore[attr-defined] when accessing
        fields on instances of the returned schema.
        
    Example:
        UserSchema = generate_schema(User, exclude=["password"])
        user_data = UserSchema(username="john")  # ✅ Works
        # user_data.username  # type: ignore[attr-defined] if needed
    """
    exclude = exclude or []
    optional_fields = optional_fields or []
    
    fields: Dict[str, Any] = {}
    for field in model._meta.fields:  # type: ignore[attr-defined]
        field_name = getattr(field, "name", None)
        if not field_name or field_name in exclude:
            continue
        
        # Get Pydantic type for this field
        pydantic_type = get_pydantic_type(field)
        
        # Check if field allows null
        field_null = getattr(field, "null", False)
        
        if update:
            # For update schemas, all fields are optional
            fields[field_name] = (Optional[pydantic_type], None)
        elif field_name in optional_fields or field_null:
            # Mark field as optional if explicitly specified or Django field allows null
            fields[field_name] = (Optional[pydantic_type], None)
        else:
            # Required field
            fields[field_name] = (pydantic_type, ...)
    
    class DynamicSchema(Schema):
        """Base schema with model serialization validator."""
        
        @model_validator(mode="before")
        def pre_serialize(cls, values: Any) -> Any:
            """Convert Django model instance to dict.
            
            Args:
                values: Input values (Django model or dict)
            
            Returns:
                Dictionary representation of the model
            """
            # Check if it's a Django model instance
            if hasattr(values, "_meta"):
                return serialize_model_instance(values)
            return values
        
        model_config = ConfigDict(from_attributes=True)

    # Create dynamic schema class
    schema = create_model(
        model.__name__ + "Schema",
        __base__=DynamicSchema,
        **fields  # type: ignore[arg-type]
    )
    
    return cast(Type[BaseModel], schema)
