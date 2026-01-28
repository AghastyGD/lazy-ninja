"""
Type guards and type-safe utilities for Lazy Ninja.

This module provides type guards and helper functions to safely work with
Django's dynamic nature while keeping type checkers happy.

Type guards help avoid `type: ignore` by encapsulating complex runtime checks.
"""

import logging
from typing import Any, Dict, List, Optional, Type, TypeVar

from django.db.models import Field, Model

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Model)


# ============================================================================
# Model and Field Type Guards
# ============================================================================


def has_field(model: Type[Model], field_name: str) -> bool:
    """Check if a Django model has a specific field.
    
    Args:
        model: Django model class
        field_name: Name of the field to check
    
    Returns:
        True if field exists, False otherwise
    
    Example:
        if has_field(User, "email"):
            # Safe to access User.email
    """
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def has_unique_field(model: Type[Model], field_name: str) -> bool:
    """Check if a Django model has a unique field.
    
    Args:
        model: Django model class
        field_name: Name of the field to check
    
    Returns:
        True if field exists and is unique, False otherwise
    
    Example:
        if has_unique_field(User, "username"):
            # Check for duplicates before creating
    """
    try:
        field = model._meta.get_field(field_name)
        return getattr(field, "unique", False)
    except Exception:
        return False


def get_model_field(model: Type[Model], field_name: str) -> Optional[Field]:
    """Safely get a field from a Django model.
    
    Args:
        model: Django model class
        field_name: Name of the field to retrieve
    
    Returns:
        Field instance if exists, None otherwise
    
    Example:
        field = get_model_field(User, "email")
        if field:
            max_length = getattr(field, "max_length", None)
    """
    try:
        return model._meta.get_field(field_name) # type: ignore
    except Exception:
        return None


def has_attribute(obj: Any, attr_name: str) -> bool:
    """Type-safe attribute check.
    
    Args:
        obj: Object to check
        attr_name: Attribute name
    
    Returns:
        True if attribute exists and is not None
    
    Example:
        if has_attribute(user, "profile"):
            user.profile.update()
    """
    return hasattr(obj, attr_name) and getattr(obj, attr_name) is not None


def get_field_choices(field: Any) -> Optional[List[Any]]:
    """Safely get choices from a Django field.
    
    Args:
        field: Django field instance
    
    Returns:
        List of choices if field has them, None otherwise
    
    Example:
        choices = get_field_choices(status_field)
        if choices:
            # Generate select options
    """
    choices = getattr(field, "choices", None)
    if choices:
        return list(choices)
    return None


def is_related_field(field: Any) -> bool:
    """Check if field is a relation (ForeignKey, ManyToMany, etc).
    
    Args:
        field: Django field instance
    
    Returns:
        True if field is a relation, False otherwise
    
    Example:
        if is_related_field(field):
            # Handle relation differently
    """
    from django.db.models.fields.related import RelatedField
    return isinstance(field, RelatedField)


def is_many_to_many(field: Any) -> bool:
    """Check if field is a ManyToMany relation.
    
    Args:
        field: Django field instance
    
    Returns:
        True if field is ManyToMany, False otherwise
    """
    from django.db.models import ManyToManyField
    return isinstance(field, ManyToManyField)


# ============================================================================
# Model Instance Type Guards
# ============================================================================


def is_model_instance(obj: Any, model: Type[T]) -> bool:
    """Check if object is an instance of a Django model.
    
    Args:
        obj: Object to check
        model: Model class to check against
    
    Returns:
        True if obj is instance of model, False otherwise
    
    Example:
        if is_model_instance(obj, User):
            # obj is a User instance
    """
    try:
        return isinstance(obj, model)
    except Exception:
        return False


def has_primary_key(obj: Any) -> bool:
    """Check if model instance has a primary key (is saved).
    
    Args:
        obj: Django model instance
    
    Returns:
        True if instance has pk (is saved), False otherwise
    
    Example:
        if has_primary_key(user):
            # User was saved to database
    """
    return hasattr(obj, "pk") and obj.pk is not None


# ============================================================================
# User Model Type Guards
# ============================================================================


def has_user_field(user_model: Type[Model], field_name: str) -> bool:
    """Check if User model has a specific field.
    
    Specialized version for User model checks.
    
    Args:
        user_model: User model class from get_user_model()
        field_name: Field name to check
    
    Returns:
        True if field exists, False otherwise
    
    Example:
        User = get_user_model()
        if has_user_field(User, "email"):
            # Can use email field
    """
    return has_field(user_model, field_name)


def has_user_manager_method(user_model: Type[Model], method_name: str) -> bool:
    """Check if User manager has a specific method.
    
    Args:
        user_model: User model class
        method_name: Manager method name to check
    
    Returns:
        True if method exists, False otherwise
    
    Example:
        if has_user_manager_method(User, "create_user"):
            User.objects.create_user(...)
    """
    return hasattr(user_model.objects, method_name)


def get_user_identifier(user: Any) -> str:
    """Get best identifier for a user (email > username > id).
    
    Args:
        user: Django user instance
    
    Returns:
        User identifier string for logging/display
    
    Example:
        logger.info("User logged in: %s", get_user_identifier(user))
    """
    email = getattr(user, "email", None)
    if email:
        return str(email)
    
    username = getattr(user, "username", None)
    if username:
        return str(username)
    
    user_id = getattr(user, "id", None) or getattr(user, "pk", None)
    if user_id:
        return f"ID:{user_id}"
    
    return "unknown"


# ============================================================================
# File Upload Type Guards
# ============================================================================


def is_uploaded_file(file: Any) -> bool:
    """Check if object is an uploaded file.
    
    Args:
        file: Object to check
    
    Returns:
        True if object has file-like attributes
    
    Example:
        if is_uploaded_file(request.FILES.get("image")):
            # Process upload
    """
    return all([
        hasattr(file, "read"),
        hasattr(file, "name"),
        has_attribute(file, "size"),
    ])


def get_file_content_type(file: Any) -> Optional[str]:
    """Safely get content type from uploaded file.
    
    Args:
        file: Uploaded file object
    
    Returns:
        Content type string or None
    
    Example:
        content_type = get_file_content_type(file)
        if content_type and content_type.startswith("image/"):
            # Process image
    """
    return getattr(file, "content_type", None)


def get_file_size(file: Any) -> int:
    """Safely get size from uploaded file.
    
    Args:
        file: Uploaded file object
    
    Returns:
        File size in bytes, 0 if not available
    
    Example:
        size = get_file_size(file)
        if size > MAX_SIZE:
            raise ValidationError("File too large")
    """
    return getattr(file, "size", 0)


def is_image_file(file: Any) -> bool:
    """Check if uploaded file is an image.
    
    Args:
        file: Uploaded file object
    
    Returns:
        True if file is an image based on content type
    
    Example:
        if is_image_file(file):
            # Process as image
    """
    content_type = get_file_content_type(file)
    return bool(content_type and content_type.startswith("image/"))


def is_video_file(file: Any) -> bool:
    """Check if uploaded file is a video.
    
    Args:
        file: Uploaded file object
    
    Returns:
        True if file is a video based on content type
    
    Example:
        if is_video_file(file):
            # Process as video
    """
    content_type = get_file_content_type(file)
    return bool(content_type and content_type.startswith("video/"))


# ============================================================================
# Query and Filter Type Guards
# ============================================================================


def is_valid_filter_field(model: Type[Model], field_name: str) -> bool:
    """Check if field name is valid for filtering.
    
    Handles Django lookups like "field__icontains".
    
    Args:
        model: Django model class
        field_name: Field name with optional lookup
    
    Returns:
        True if field exists and is filterable
    
    Example:
        if is_valid_filter_field(User, "email__iexact"):
            # Safe to use in filter
    """
    # Handle Django lookups (field__lookup)
    base_field = field_name.split("__")[0]
    return has_field(model, base_field)


def sanitize_filters(
    model: Type[Model], 
    filters: Dict[str, Any]
) -> Dict[str, Any]:
    """Sanitize filter dict to only include valid model fields.
    
    Args:
        model: Django model class
        filters: Raw filter dictionary
    
    Returns:
        Sanitized filter dict with only valid fields
    
    Example:
        safe_filters = sanitize_filters(User, request.GET.dict())
        queryset = User.objects.filter(**safe_filters)
    """
    sanitized = {}
    for field_name, value in filters.items():
        if is_valid_filter_field(model, field_name):
            sanitized[field_name] = value
        else:
            logger.warning(
                "Ignoring invalid filter field: %s for model %s",
                field_name,
                model.__name__
            )
    return sanitized


def get_model_field_names(
    model: Type[Model],
    exclude_relations: bool = False,
) -> List[str]:
    """Get list of all field names for a model.
    
    Args:
        model: Django model class
        exclude_relations: If True, exclude ForeignKey/ManyToMany fields
    
    Returns:
        List of field names
    
    Example:
        fields = get_model_field_names(User)
        # ["id", "username", "email", ...]
    """
    try:
        fields = model._meta.get_fields()
        field_names = []
        
        for field in fields:
            if exclude_relations and is_related_field(field):
                continue
            field_name = getattr(field, "name", None)
            if field_name:
                field_names.append(field_name)
        
        return field_names
    except Exception as e:
        logger.error("Error getting field names for %s: %s", model.__name__, e)
        return []


# ============================================================================
# Validation Type Guards
# ============================================================================


def is_valid_pagination_params(page: Any, page_size: Any) -> bool:
    """Check if pagination parameters are valid.
    
    Args:
        page: Page number
        page_size: Items per page
    
    Returns:
        True if both are valid integers
    
    Example:
        if is_valid_pagination_params(request.GET.get("page"), ...):
            # Safe to paginate
    """
    try:
        p = int(page)
        ps = int(page_size)
        return p >= 1 and 1 <= ps <= 100
    except (ValueError, TypeError):
        return False


def is_uuid(value: Any) -> bool:
    """Check if value is a valid UUID.
    
    Args:
        value: Value to check
    
    Returns:
        True if value is a valid UUID
    
    Example:
        if is_uuid(user_id):
            # Safe to use as UUID
    """
    import uuid
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False
