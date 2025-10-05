import json
from typing import Type, Any, Dict, Optional, Iterable, Union
from asgiref.sync import sync_to_async

from django.db import models
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from .base import serialize_model_instance, serialize_model_instance_async

class BaseModelUtils:
    """Base class for model utilities."""

    def convert_foreign_keys(self, model: Type[models.Model], data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Converts integer values for ForeignKey fields in `data` to the corresponding model instances.
        
        Args:
            model: The Django model class
            data: Dictionary containing field data
            
        Returns:
            Dictionary with converted foreign key values
        """
        data = dict(data)

        for field in model._meta.fields:
            if field.name not in data or not isinstance(field, models.ForeignKey):
                continue

            fk_value = data[field.name]

            if fk_value in (None, ""):
                data[field.name] = None
                continue

            if isinstance(fk_value, models.Model):
                continue

            if isinstance(fk_value, str):
                parsed = self._try_parse_json_dict(fk_value)
                if isinstance(parsed, dict):
                    fk_value = parsed
                else:
                    data[field.name] = field.related_model.objects.get(pk=fk_value)
                    continue

            if isinstance(fk_value, dict):
                data[field.name] = self._handle_nested_relation(field, fk_value)
                continue

            if isinstance(fk_value, (int, str)):
                data[field.name] = field.related_model.objects.get(pk=fk_value)

        return data

    def _handle_nested_relation(self, field: models.ForeignKey, value: Dict[str, Any]) -> models.Model:
        """Create or update a related object from nested payload data."""
        related_model = field.related_model
        nested_payload = dict(value)

        pk_name = related_model._meta.pk.name
        pk_value = nested_payload.pop(pk_name, None)

        nested_payload = self.convert_foreign_keys(related_model, nested_payload)

        if pk_value is not None:
            instance = related_model.objects.get(pk=pk_value)
            for attr, attr_value in nested_payload.items():
                setattr(instance, attr, attr_value)
            instance.save()
            return instance

        return related_model.objects.create(**nested_payload)

    def _try_parse_json_dict(self, value: str) -> Any:
        """Attempt to decode a JSON string and return dict payloads only."""
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            return value

        return parsed if isinstance(parsed, dict) else parsed


class SyncModelUtils(BaseModelUtils):
    """Handles model operations for sync routes."""
    
    def get_object_or_404(self, source: Union[Type[models.Model], QuerySet], **kwargs) -> Any:
        """Get object or raise 404."""
        return get_object_or_404(source, **kwargs)
    
    def create_instance(self, model: Type[models.Model], **data) -> Any:
        """Create a new model instance."""
        return model.objects.create(**data)
    
    def update_instance(self, instance: Any, data: Dict[str, Any]) -> None:
        """Update an existing model instance."""
        for key, value in data.items():
            setattr(instance, key, value)
        instance.save()
    
    def delete_instance(self, instance: Any) -> None:
        """Delete a model instance."""
        instance.delete()
    
    def serialize_model_instance(self, instance: Any, *, expand: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        """Serialize a model instance."""
        return serialize_model_instance(instance, expand=expand)
    

class AsyncModelUtils(BaseModelUtils):
    """Handles model operations for async routes."""

    async def get_all_objects(self, model: Type[models.Model]):
        """Get all objects for a model asynchronously."""
        return await sync_to_async(lambda m: m.objects.all())(model)
    
    async def get_object_or_404(self, source: Union[Type[models.Model], QuerySet], **kwargs) -> Any:
        """Get object or raise 404 asynchronously."""
        return await sync_to_async(get_object_or_404)(source, **kwargs)
    
    async def create_instance(self, model: Type[models.Model], **data) -> Any:
        """Create a new model instance asynchronously."""
        create_func = sync_to_async(lambda m, **kwargs: m.objects.create(**kwargs))
        return await create_func(model, **data)
    
    async def update_instance(self, instance: Any, data: Dict[str, Any]) -> None:
        """Update an existing model instance asynchronously."""
        for key, value in data.items():
            setattr(instance, key, value)

        save_instance = sync_to_async(lambda obj: obj.save())
        await save_instance(instance)

    async def delete_instance(self, instance: Any) -> None:
        """Delete a model instance asynchronously."""
        delete_func = sync_to_async(lambda obj: obj.delete())
        await delete_func(instance)

    async def convert_foreign_keys(self, model: Type[models.Model], data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert foreign keys asynchronously."""
        return await sync_to_async(super().convert_foreign_keys)(model, data)

    async def serialize_model_instance(self, instance: Any, *, expand: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        """Serialize a model instance asynchronously."""
        return await serialize_model_instance_async(instance, expand=expand)
    
# Legacy function wrappers for backward compatibility
def convert_foreign_keys(model: Type[models.Model], data: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy wrapper for foreign key conversion."""
    utils = SyncModelUtils()
    return utils.convert_foreign_keys(model, data)


async def convert_foreign_keys_async(model: Type[models.Model], data: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy wrapper for async foreign key conversion."""
    utils = AsyncModelUtils()
    return await utils.convert_foreign_keys(model, data)
