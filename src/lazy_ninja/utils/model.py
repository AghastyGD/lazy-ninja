from typing import Type, Any, Dict
from asgiref.sync import sync_to_async

from django.db import models
from django.db import transaction
from django.core.exceptions import ValidationError
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
        for field in model._meta.fields:
            if isinstance(field, models.ForeignKey) and field.name in data:
                fk_value = data[field.name]
                if isinstance(fk_value, (int, str)):
                    data[field.name] = field.related_model.objects.get(**{field.target_field.name: fk_value})
        return data

    def split_many_to_many(self, model: Type[models.Model], data: Dict[str, Any]):
        values = dict(data)
        relations = {}
        for field in model._meta.many_to_many:
            if field.name not in values:
                continue
            ids = values.pop(field.name)
            if not field.remote_field.through._meta.auto_created:
                raise ValidationError(f"{field.name} has a custom through model and is read-only.")
            if not isinstance(ids, list):
                raise ValidationError(f"{field.name} must be a list of IDs.")
            unique_ids = list(dict.fromkeys(ids))
            objects = list(field.remote_field.model.objects.filter(pk__in=unique_ids))
            if len(objects) != len(unique_ids):
                raise ValidationError(f"{field.name} contains an unknown ID.")
            relations[field.name] = objects
        return values, relations


class SyncModelUtils(BaseModelUtils):
    """Handles model operations for sync routes."""
    
    def get_object_or_404(self, model: Type[models.Model], **kwargs) -> Any:
        """Get object or raise 404."""
        return get_object_or_404(model, **kwargs)
    
    def create_instance(self, model: Type[models.Model], **data) -> Any:
        """Create a new model instance."""
        fields, relations = self.split_many_to_many(model, data)
        with transaction.atomic():
            instance = model.objects.create(**fields)
            for name, objects in relations.items():
                getattr(instance, name).set(objects)
        return instance
    
    def update_instance(self, instance: Any, data: Dict[str, Any]) -> None:
        """Update an existing model instance."""
        fields, relations = self.split_many_to_many(type(instance), data)
        with transaction.atomic():
            for key, value in fields.items():
                setattr(instance, key, value)
            instance.save()
            for name, objects in relations.items():
                getattr(instance, name).set(objects)
    
    def delete_instance(self, instance: Any) -> None:
        """Delete a model instance."""
        instance.delete()
    
    def serialize_model_instance(self, instance: Any) -> Dict[str, Any]:
        """Serialize a model instance."""
        return serialize_model_instance(instance)
    

class AsyncModelUtils(BaseModelUtils):
    """Handles model operations for async routes."""

    async def get_all_objects(self, model: Type[models.Model]):
        """Get all objects for a model asynchronously."""
        return await sync_to_async(lambda m: m.objects.all())(model)
    
    async def get_object_or_404(self, model: Type[models.Model], **kwargs) -> Any:
        """Get object or raise 404 asynchronously."""
        return await sync_to_async(get_object_or_404)(model, **kwargs)
    
    async def create_instance(self, model: Type[models.Model], **data) -> Any:
        """Create a new model instance asynchronously."""
        return await sync_to_async(SyncModelUtils().create_instance)(model, **data)
    
    async def update_instance(self, instance: Any, data: Dict[str, Any]) -> None:
        """Update an existing model instance asynchronously."""
        await sync_to_async(SyncModelUtils().update_instance)(instance, data)

    async def delete_instance(self, instance: Any) -> None:
        """Delete a model instance asynchronously."""
        delete_func = sync_to_async(lambda obj: obj.delete())
        await delete_func(instance)

    async def convert_foreign_keys(self, model: Type[models.Model], data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert foreign keys asynchronously."""
        return await sync_to_async(super().convert_foreign_keys)(model, data)

    async def serialize_model_instance(self, instance: Any) -> Dict[str, Any]:
        """Serialize a model instance asynchronously."""
        return await serialize_model_instance_async(instance)
    
# Legacy function wrappers for backward compatibility
def convert_foreign_keys(model: Type[models.Model], data: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy wrapper for foreign key conversion."""
    utils = SyncModelUtils()
    return utils.convert_foreign_keys(model, data)


async def convert_foreign_keys_async(model: Type[models.Model], data: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy wrapper for async foreign key conversion."""
    utils = AsyncModelUtils()
    return await utils.convert_foreign_keys(model, data)
