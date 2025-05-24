from typing import Dict, List, Tuple

from django.db import models

class FileUploadConfig:
    """
    Configuration for file upload fields in a model.
    
    This class helps configure which fields are file fields and
    whether to use multipart/form-data for specific models.
    """
    def __init__(
        self,
        file_fields: Dict[str, List[str]] = None,
        multiple_file_fields: Dict[str, List[str]] = None,
    ):
        """
        Initialize file upload configuration.
        
        Args:
            file_fields: Dictionary mapping model names to lists of file field names
                         e.g. {"MyModel": ["image", "attachment"]}
            multiple_file_fields: Dictionary mapping model names to lists of field names 
                                  that can accept multiple files
                                  e.g. {"MyModel": ["gallery_images"]}
        """
        self.file_fields = file_fields or {}
        self.multiple_file_fields = multiple_file_fields or {}
        
    def get_model_file_fields(self, model_name: str) -> List[str]:
        """Get list of file fields for a model."""
        return self.file_fields.get(model_name, [])
    
    def get_model_multiple_file_fields(self, model_name: str) -> List[str]:
        """Get list of multiple file fields for a model."""
        return self.multiple_file_fields.get(model_name, [])
    
    def is_multiple_file_field(self, model_name: str, field_name: str) -> bool:
        """Check if a field is configured for multiple file uploads."""
        return field_name in self.get_model_multiple_file_fields(model_name)


def detect_file_fields(model) -> Tuple[List[str], List[str]]:
    """
    Automatically detect file fields in a Django model.
    
    Returns a tuple of (single_file_fields, multiple_file_fields)
    """
    single_file_fields = []
    multiple_file_fields = []
    
    for field in model._meta.get_fields():
        if isinstance(field, (models.FileField, models.ImageField)):
            single_file_fields.append(field.name)
            
        elif isinstance(field, models.ManyToManyField):
            related_model = field.related_model
            if related_model:
                
                for related_field in related_model._meta.get_fields():
                    if isinstance(related_field, (models.FileField, models.ImageField)):
                        multiple_file_fields.append(field.name)
                        break
                    
        elif isinstance(field, models.ManyToOneRel):
            related_model = field.related_model
            if related_model:
                has_file_field = False
                
                for related_field in related_model._meta.get_fields():
                    if isinstance(related_field, (models.FileField, models.ImageField)):
                        has_file_field = True
                        break
                    
                if has_file_field:
                    multiple_file_fields.append(field.get_accessor_name())
                    
        elif isinstance(field, models.OneToOneField):
            related_model = field.related_model
            if related_model:
                
                for related_model in related_model._meta.get_fields():
                    if isinstance(related_field, (models.FileField, models.ImageField)):
                        single_file_fields.append(field.name)
                        break
                    
        elif isinstance(field, models.OneToOneRel):
            related_model = field.related_model
            if related_model:
                has_file_field = False
                
                for related_field in related_model._meta.get_fields():
                    if isinstance(related_field, (models.FileField, models.ImageField)):
                        has_file_field = True
                        break
                
                if has_file_field:
                    single_file_fields.append(field.get_accessor_name())
            
    return single_file_fields, multiple_file_fields
