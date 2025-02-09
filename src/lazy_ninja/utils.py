from django.db.models import AutoField, CharField, IntegerField, TextField, DateField, DateTimeField, BooleanField, ForeignKey
from typing import Type, List
from ninja import Schema
from pydantic import create_model
from typing import Optional

def get_pydantic_type(field):
    """
    Map a Django model field to an equivalent Python type for Pydantic validation.
    
    Parameters:
      - field: A Django model field instance.
    
    Returns:
      - A Python type that represents the field.
    """
    if isinstance(field, AutoField):
        return int
    elif isinstance(field, (CharField, TextField)):
        return str
    elif isinstance(field, IntegerField):
        return int
    elif isinstance(field, BooleanField):
        return bool
    elif isinstance(field, (DateField, DateTimeField)):
        return str
    elif isinstance(field, ForeignKey):
        return int
    else:
        return str
    
def generate_schema(model, exclude: List[str] = [], optional_fields: List[str] = []) -> Type[Schema]:
    """
    Generate a Pydantic schema based on a Django model.
    
    Parameters:
      - model: The Django model class.
      - exclude: A list of field names to exclude from the schema.
      - optional_fields: A list of field names that should be marked as optional.
    
    Returns:
      - A dynamically created Pydantic schema class.
      
    Notes:
      - Fields defined in `optional_fields` or those with null=True in the Django model
        are set as Optional in the Pydantic schema.
    """
    fields = {}
    for field in model._meta.fields:
        if field.name in exclude:
            continue
        pydantic_type = get_pydantic_type(field)
        # Mark field as optional if it's in optional_fields or if the Django field allows null values.
        if field.name in optional_fields:
            fields[field.name] = (Optional[pydantic_type], None)
        elif field.null:
            fields[field.name] = (Optional[pydantic_type], None)
        else:
            fields[field.name] = (pydantic_type, ...)
            
    class Config:
        # Allow creating schema instances from Django model attributes.
        from_attributes = True
        
    # Create the Pydantic model with a name based on the Django model name.
    schema = create_model(
        model.__name__ + "Schema",
        __config__=Config,
        **fields
    )
    schema.model_rebuild()
    return schema
