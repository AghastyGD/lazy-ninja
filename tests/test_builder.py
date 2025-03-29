import pytest
from django.test import Client

@pytest.mark.django_db
def test_dynamic_api_registration(client):
    """Tests if all routes are registered correctly"""
    client = Client()
    url = "/api/test-models/"
    response = client.get(url)
    assert response.status_code == 200
    assert response.json() ==  {
        'count': 0,
        'items': []
    }