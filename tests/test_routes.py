import pytest

from django.test.utils import CaptureQueriesContext
from django.db import connection

from tests.models import TestModel

@pytest.mark.django_db
def test_list_items(client, create_test_model):
    """Tests items listing"""
    model1 = create_test_model(title="Model 1", image="http://sample.com/1.jpg")
    model2 = create_test_model(title="Model 2", image="http://sample.com/2.jpg")
    
    url = "/api/test-models/"
    response = client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert data['count'] == 2
    assert any(item["title"] == "Model 1" for item in data['items'])
    assert any(item["title"] == "Model 2" for item in data['items'])
    
    
@pytest.mark.django_db
def test_get_item(client, create_test_model):
    """Tests item retrieval"""
    model = create_test_model()
    url = f"/api/test-models/{model.id}" 
    response = client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert data['title'] == "Test Model"
    assert data['image'] == "http://sample.com/image.jpg"
    
    
@pytest.mark.django_db
def test_create_item(client, create_test_category):
    """Tests item creation"""
    category = create_test_category()
    url = "/api/test-models/"
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
    new_category = create_test_category(name="New Category")
    url = f"/api/test-models/{model.id}"
    data = {
        "title": "Updated Model",
        "image": "http://sample.com/updated.jpg",
        "category": new_category.id
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
    url = f"/api/test-models/{model.id}"
    response = client.delete(url)
    assert response.status_code == 200
    assert TestModel.objects.count() == 0


@pytest.mark.django_db
def test_list_items_no_n_plus_1(client, create_test_model):
    """
    List endpoint must not produce N+1 queries.
    With select_related applied, the number of DB queries must stay constant
    regardless of how many items are in the list.
    """
    # Create 3 items each with their own FK category
    create_test_model(title="A")
    create_test_model(title="B")
    create_test_model(title="C")

    url = "/api/test-models/"

    with CaptureQueriesContext(connection) as ctx_3:
        response = client.get(url)
    assert response.status_code == 200
    queries_for_3 = len(ctx_3.captured_queries)

    # Add 3 more items
    create_test_model(title="D")
    create_test_model(title="E")
    create_test_model(title="F")

    with CaptureQueriesContext(connection) as ctx_6:
        response = client.get(url)
    assert response.status_code == 200
    queries_for_6 = len(ctx_6.captured_queries)

    # Query count must not grow linearly with row count
    assert queries_for_6 == queries_for_3, (
        f"N+1 detected: {queries_for_3} queries for 3 items but "
        f"{queries_for_6} queries for 6 items"
    )