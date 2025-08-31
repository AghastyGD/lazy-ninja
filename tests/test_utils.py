import pytest
from django.db import models
from django.contrib.auth import get_user_model
from ninja import Schema
from lazy_ninja.utils import (
    generate_schema,    
    serialize_model_instance,
    convert_foreign_keys,
    get_pydantic_type
)

from .models import Category

class MockModel(models.Model):
    title = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    image = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True)
    
    def __str__(self):
        return self.title
    
    
@pytest.mark.django_db
def test_generate_schema():
    """Tests Pydantic schema generation"""
    schema = generate_schema(MockModel)
    assert issubclass(schema, Schema)
    assert "title" in schema.model_fields
    assert "category" in schema.model_fields
    assert "image" in schema.model_fields
    assert "created_at" in schema.model_fields
    assert "user" in schema.model_fields
    
    schema_excluded = generate_schema(MockModel, exclude=["title", "created_at"])
    assert "title" not in schema_excluded.model_fields
    assert "created_at" not in schema_excluded.model_fields
    assert "category" in schema_excluded.model_fields
    
    schema_optional = generate_schema(MockModel, optional_fields=["image"])
    assert "image" in schema_optional.model_fields
    assert schema_optional.model_fields["image"].is_required() is False
    
    
@pytest.mark.django_db
def test_serialize_model_instance(create_test_category):
    """"Tests model instance serialization"""
    User = get_user_model()
    user = User.objects.create_user(username="testuser3", password="testpassowrd")
    category = create_test_category(name="Test Category")
    instance = MockModel.objects.create(title="Test Title", category=category, image="http://sample.com/test.jpg", user=user)
    serialized_data = serialize_model_instance(instance)
    
    assert serialized_data["title"] == "Test Title"
    assert serialized_data["image"] == "http://sample.com/test.jpg"
    assert serialized_data["category"] == category.pk
    assert isinstance(serialized_data["created_at"], str)
    assert serialized_data["is_active"] == True
    assert serialized_data["user"] == user.pk


@pytest.mark.django_db
def test_convert_foreign_keys(create_test_category):
    """Tests foreign keys conversion"""
    category = create_test_category(name="Test Category")
    User = get_user_model()
    user = User.objects.create_user(username="testuser4", password="testpassword")
    
    data = {"title": "Test Title", "category": category.pk, "user": user.pk}
    converted_data = convert_foreign_keys(MockModel, data)
    assert converted_data["category"] == category
    assert converted_data["user"] == user
    
    # Test with None value
    data = {"title": "Test Title", "category": None, "user": None}
    converted_data = convert_foreign_keys(MockModel, data)
    assert converted_data["category"] is None
    assert converted_data["user"] is None
    
    
def test_get_pydantic_type():
    """Tests Django model fields mapping for Pydantic types"""
    assert get_pydantic_type(models.AutoField(primary_key=True)) == int
    assert get_pydantic_type(models.CharField()) == str
    assert get_pydantic_type(models.TextField()) == str
    assert get_pydantic_type(models.IntegerField()) == int
    assert get_pydantic_type(models.BooleanField()) == bool
    assert get_pydantic_type(models.DateField()) == str
    assert get_pydantic_type(models.DateTimeField()) == str
    assert get_pydantic_type(models.ImageField()) == str
    assert get_pydantic_type(models.FileField()) == str
    assert get_pydantic_type(models.ForeignKey(Category, on_delete=models.CASCADE)) == int
    assert get_pydantic_type(models.FloatField()) == float 
    assert get_pydantic_type(models.EmailField()) == str  # Test case not exists in get_pydantic_type, should return str