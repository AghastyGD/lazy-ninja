import pytest
from django.core.management import call_command
from django.test import Client

from .models import TestModel, Category

@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command('makemigrations')
        call_command('migrate')
        
        
@pytest.fixture
def client():
    return Client()


@pytest.fixture
def create_test_model(db, create_test_category):
    def _create_test_model(**kwargs, ):
        defaults = {
            'title': 'Test Model',
            'image': 'http://sample.com/image.jpg',
            'category': create_test_category()
        }
        defaults.update(kwargs)
        return TestModel.objects.create(**defaults)
    return _create_test_model


@pytest.fixture
def create_test_category(db):
    def _create_test_category(**kwargs):
        defaults = {'name': 'Test Category'}
        defaults.update(kwargs)
        return Category.objects.create(**defaults)
    return _create_test_category