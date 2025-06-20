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


class FileFieldDetector:
    """
    Utility class for detecting file fields in Django models.
    
    Separated from the main detect_file_fields function for better organization.
    """
    
    def detect_file_fields(self, model) -> Tuple[List[str], List[str]]:
        """
        Automatically detect file fields in a Django model.
        
        Args:
            model: Django model class to analyze
            
        Returns:
            Tuple of (single_file_fields, multiple_file_fields)
        """
        single_file_fields = []
        multiple_file_fields = []
        
        for field in model._meta.get_fields():
            if isinstance(field, (models.FileField, models.ImageField)):
                single_file_fields.append(field.name)
                
            elif isinstance(field, models.ManyToManyField):
                related_model = field.related_model
                if related_model and self._has_file_fields(related_model):
                    multiple_file_fields.append(field.name)
                    
            # elif isinstance(field, models.ManyToOneRel):
            #     related_model = field.related_model
            #     if related_model and self._has_file_fields(related_model):
            #         multiple_file_fields.append(field.get_accessor_name())
                    
            # elif isinstance(field, models.OneToOneField):
            #     related_model = field.related_model
            #     if related_model and self._has_file_fields(related_model):
            #         single_file_fields.append(field.name)
                    
            # elif isinstance(field, models.OneToOneRel):
            #     related_model = field.related_model
            #     if related_model and self._has_file_fields(related_model):
            #         single_file_fields.append(field.get_accessor_name())
                
        return single_file_fields, multiple_file_fields
    
    def _has_file_fields(self, model) -> bool:
        """Check if a model has any file fields."""
        for field in model._meta.get_fields():
            if isinstance(field, (models.FileField, models.ImageField)):
                return True
        return False


# Legacy function for backward compatibility
def detect_file_fields(model) -> Tuple[List[str], List[str]]:
    """
    Legacy function for detecting file fields.
    
    This function is kept for backward compatibility.
    Use FileFieldDetector.detect_file_fields() for new code.
    """
    detector = FileFieldDetector()
    return detector.detect_file_fields(model)