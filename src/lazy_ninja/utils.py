from django.db.models import AutoField, CharField, IntegerField, TextField, DateField, DateTimeField, BooleanField, ForeignKey, ImageField
from django.db.models.fields.files import ImageFieldFile
from typing import Type, List, Optional
from ninja import Schema
from pydantic import create_model, model_validator
from django.db import models
        
def convert_foreign_keys(model, data: dict) -> dict:
    """
    Converts integer values for ForeignKey fields in `data` to the corresponding model instances.
    """
    for field in model._meta.fields:
        if isinstance(field, models.ForeignKey) and field.name in data:
            fk_value = data[field.name]
            if isinstance(fk_value, int):
                # Retrieve the related model instance using the primary key.
                data[field.name] = field.related_model.objects.get(pk=fk_value)
    return data


def serialize_model_instance(obj):
    """
    Serializes a Django model instance into a dictionary with simple types.
    """
    data = {}
    for field in obj._meta.fields:
        value = getattr(obj, field.name)
        if value is None:
            data[field.name] = None
        elif isinstance(field, (models.DateField, models.DateTimeField)):
            data[field.name] = value.isoformat()
        elif isinstance(value, ImageFieldFile):
            data[field.name] = value.url if hasattr(value, 'url') else str(value)
        elif hasattr(value, 'pk'):
            data[field.name] = value.pk
        else:
            data[field.name] = value
    return data

def get_pydantic_type(field) -> Type:
    """
    Map a Django model field to an equivalent Python type for Pydantic validation.
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
    elif isinstance(field, ImageField):
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
      - Fields listed in `optional_fields` or with null=True in the Django model are set as Optional.
      - A root validator is added to preprocess the input using `serialize_model_instance`.
    """
    fields = {}
    for field in model._meta.fields:
        if field.name in exclude:
            continue
        pydantic_type = get_pydantic_type(field)
        # Mark field as optional if it's in optional_fields or if the Django field allows null values.
        if field.name in optional_fields or field.null:
            fields[field.name] = (Optional[pydantic_type], None)
        else:
            fields[field.name] = (pydantic_type, ...)
            
    # Define a pre-root validator that converts a Django model instance into a dict
    # using our serialize_model_instance function.
    @model_validator(mode="before")
    def pre_serialize(cls, values):
        # If the input is a Django model instance, serialize it.
        if hasattr(values, "_meta"):
            return serialize_model_instance(values)
        return values

    class Config:
        from_attributes = True
 
    # Create the Pydantic model with our fields, config, and validator.
    schema = create_model(
        model.__name__ + "Schema",
        __config__=Config,
        __validators__={'pre_serialize': pre_serialize},
        **fields
    )
    schema.model_rebuild()
    return schema
