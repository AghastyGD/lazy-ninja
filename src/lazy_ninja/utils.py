from django.db import models
from typing import Type, List, Optional
from ninja import Schema
from pydantic import ConfigDict, create_model, model_validator
        
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
        elif isinstance(value, (models.ImageField, models.FileField)):
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
    if isinstance(field, models.AutoField):
        return int
    elif isinstance(field, (models.CharField, models.TextField)):
        return str
    elif isinstance(field, models.IntegerField):
        return int
    elif isinstance(field, models.BooleanField):
        return bool
    elif isinstance(field, (models.DateField, models.DateTimeField)):
        return str
    elif isinstance(field, (models.ImageField, models.FileField)):
        return str
    elif isinstance(field, models.ForeignKey):
        return int
    else:
        return str

def generate_schema(model, exclude: List[str] = [], optional_fields: List[str] = [], update: bool = False) -> Type[Schema]:
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
        
        if update:
            fields[field.name] = (Optional[pydantic_type], None)
    
        # Mark field as optional if it's in optional_fields or if the Django field allows null values.
        elif field.name in optional_fields or field.null:
            fields[field.name] = (Optional[pydantic_type], None)
        else:
            fields[field.name] = (pydantic_type, ...)
            
    class DynamicSchema(Schema):
        @model_validator(mode="before")
        def pre_serialize(cls, values):
            """Define a pre-root validator that converts a Django model instance into a dict
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
