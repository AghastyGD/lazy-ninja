import pytest
from django.contrib.auth import get_user_model

from tests.models import TestModel, Category

@pytest.mark.django_db
def test_list_items(client, create_test_model):
    """Tests items listing"""
    model1 = create_test_model(title="Model 1", image="http://sample.com/1.jpg")
    model2 = create_test_model(title="Model 2", image="http://sample.com/2.jpg")
    
    url = "/api/testmodel/"
    response = client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(item["title"] == "Model 1" for item in data)
    assert any(item["title"] == "Model 2" for item in data)
    
@pytest.mark.django_db
def test_get_item(client, create_test_model):
    """Tests item retrieval"""
    model = create_test_model()
    url = f"/api/testmodel/{model.id}" 
    response = client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert data['title'] == "Test Model"
    assert data['image'] == "http://sample.com/image.jpg"
    

@pytest.mark.django_db
def test_create_item(client, create_test_category):
    """Tests item creation"""
    category = create_test_category()
    url = "/api/testmodel/"
    data = {
        "title": "New Model",
        "image": "http://sample.com/new.jpg",
        "category": category.id,

    }
    response = client.post(url, data, content_type="application/json")
    assert response.status_code == 200
    assert TestModel.objects.count() == 1
    new_model = TestModel.objects.first()
    assert new_model.title == "New Model"
    assert new_model.image == "http://sample.com/new.jpg"
    assert new_model.category == category
    
@pytest.mark.django_db
def test_update_item(client, create_test_model, create_test_category):
    """Tests item update"""
    model = create_test_model()
    User = get_user_model()
    user, _ = User.objects.get_or_create(username="testuser3", defaults={"password": "testpassword"})
    new_category = create_test_category(name="New Category")
    url = f"/api/testmodel/{model.id}"
    data = {
        "title": "Updated Model",
        "image": "http://sample.com/updated.jpg",
        "category": new_category.id,
        "user": user.id
    }
    response = client.patch(url, data, content_type="application/json")
    assert response.status_code == 200
    model.refresh_from_db() 
    assert model.title == "Updated Model"
    assert model.image == "http://sample.com/updated.jpg"
    assert model.category == new_category

@pytest.mark.django_db
def test_delete_item(client, create_test_model):
    """Tests item deletion"""
    model = create_test_model()
    url = f"/api/testmodel/{model.id}"
    response = client.delete(url)
    assert response.status_code == 200
    assert TestModel.objects.count() == 0