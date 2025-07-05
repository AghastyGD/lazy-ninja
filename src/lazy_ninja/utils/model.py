from typing import Type, Any, Dict
from asgiref.sync import sync_to_async

from django.db import models
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
                if isinstance(fk_value, int):
                    # Retrieve the related model instance using the primary key.
                    data[field.name] = field.related_model.objects.get(pk=fk_value)
        return data


class SyncModelUtils(BaseModelUtils):
    """Handles model operations for sync routes."""
    
    def get_object_or_404(self, model: Type[models.Model], **kwargs) -> Any:
        """Get object or raise 404."""
        return get_object_or_404(model, **kwargs)
    
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
    
    def serialize_instance(self, instance: Any) -> Dict[str, Any]:
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
    
# Legacy function wrappers for backward compatibility
def convert_foreign_keys(model: Type[models.Model], data: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy wrapper for foreign key conversion."""
    utils = SyncModelUtils()
    return utils.convert_foreign_keys(model, data)


async def convert_foreign_keys_async(model: Type[models.Model], data: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy wrapper for async foreign key conversion."""
    utils = AsyncModelUtils()
    return await utils.convert_foreign_keys(model, data)