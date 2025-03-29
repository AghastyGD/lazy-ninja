# Lazy Ninja: Generate CRUD API Endpoints for Django

[![PyPI version](https://badge.fury.io/py/lazy-ninja.svg)](https://badge.fury.io/py/lazy-ninja)
[![Downloads](https://static.pepy.tech/personalized-badge/lazy-ninja?period=total&units=international_system&left_color=grey&right_color=blue&left_text=Downloads)](https://pepy.tech/project/lazy-ninja)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

>**Note:** This version supports only JSON data. `multipart/form-data` (file uploads) is not yet available. For `ImageField` or `FileField`, use the full URL as a string


**Lazy Ninja** is a Django library that automates the generation of CRUD API endpoints with Django Ninja. It dynamically scans your Django models and creates Pydantic schemas for listing, detailing, creating, and updating records—all while allowing you to customize behavior via hook functions (controllers) and schema configurations.

By leveraging Django Ninja, Lazy Ninja benefits from automatic, interactive API documentation generated through OpenAPI (Swagger UI and ReDoc), giving developers an intuitive interface to quickly visualize and interact with API endpoints.

>**Async by Default**: Lazy Ninja is designed to be asynchronous by default, leveraging Django's async capabilities for better performance. However, if needed, you can configure it to use synchronous operations by setting the `is_async` parameter to `False`.

**Key Features:**

-   **Instant CRUD Endpoints:** Automatically generate API endpoints from Django models.
-   **Dynamic Schema Generation:** Automatically create Pydantic models.
-   **Customizable Hooks:** Add pre-processing, post-processing, or custom logic to routes by creating controllers for specific models.
-   **Smart Filtering/Sorting:** Built-in support for filters like `field=value` or `field>value`.
-   **Auto Documentation:** Interactive Swagger UI and ReDoc support.
-   **Performance Optimized:** Lightweight with minimal overhead.
    

----------

## Installation

### Requirements

-   **Python**: 3.7 or higher
-   **Django**: 3.1 or higher
-   **Django Ninja**: 0.22 or higher

> **Note:**  While the library may work with older versions of Python or Django, these are the versions officially tested and recommended.

### Install the package

Run the following command to install the package:
```bash
pip install lazy-ninja
```

----------

## Quick Start

### 1. Create a Model

```python
# models.py  
from django.db import models 

class Product(models.Model):
    name = models.CharField(max_length=100)
	price = models.DecimalField(max_digits=10, decimal_places=2)
	in_stock = models.BooleanField(default=True)
```
### 2. Configure the API

```python
# api.py  
from ninja import NinjaAPI 
from lazy_ninja.builder import DynamicAPI

api = NinjaAPI(title="Store API") 
auto_api = DynamicAPI(api, pagination_type="limit-offset")
auto_api.init()
```
### 3. Add URLs

```python
# urls.py  
from django.urls import path 
from .api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
] 
```
### 4. Migrate Your Database

```bash
python manage.py makemigrations
python manage.py migrate 
```
### 5. Run the Server

```bash
python manage.py runserver
```

---------------

## Instant API Endpoints

Your CRUD API is now live at  `http://localhost:8000/api`  with these endpoints:

| Method |  URL               | Action         |
| ------ | -------------------| ---------------| 
| GET    | /api/products/     | List products  |
| POST   | /api/products/     | Create product |
| GET    | /api/products/{id} | Get product    |
| PATCH  | /api/products/{id} | Update product |
| DELETE | /api/products/{id} | Delete product |

----------

## Interactive Documentation

Access auto-generated documentation through:

### Swagger UI

`http://localhost:8000/api/docs`

![Swagger UI](../images/sample/swagger.png)
----------

## Advanced Example

### Custom Schema with Validation

```python
# schemas.py
from pydantic import BaseModel, Field

class ProductCreateSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    price: float = Field(..., gt=0)
    in_stock: bool = True

class ProductUpdateSchema(ProductCreate):
    __annotations__ = {k: Optional[v] for k, v in ProductCreate.__annotations__.items()}
```

### Configure Endpoints

```python
# api.py
from .schemas import ProductCreateSchema, ProductUpdateSchema

custom_schemas = {
    "Product": {
        "create": ProductCreateSchema,
        "update": ProductUpdateSchema
    }

}
auto_api = DynamicAPI(api, custom_schemas=custom_schemas)
```

### Using a Custom Controller

To further customize the behavior of your API, you can create a controller for specific models. Controllers allow you to add hooks such as  `before_create`,  `before_update`, or  `after_delete`  to modify the behavior of routes.

For example, here’s how to use a controller with the  `Product`  model:

```python
# controllers/product.py
from django.utils.text import slugify
from lazy_ninja import BaseModelController, controller_for

@controller_for("Product")
class ProductController(BaseModelController):
    @classmethod
    def before_create(cls, request, payload, create_schema):
        """
        Hook executed before creating a new Product.
        It validates the 'name' field against forbidden words,
        converts it to lowercase, and automatically generates a slug.
        """
        forbidden_words = ["forbidden", "banned", "test"]
        payload_data = payload.model_dump()

        for word in forbidden_words:
            if word in payload_data['name'].lower():
                raise ValueError(f"Invalid name: contains forbidden word '{word}'")
        
        # Generate a slug for the product name
        payload_data['slug'] = slugify(payload_data['name'])

        return create_schema(**payload_data)
```
**Steps to Use a Controller:**

1.  Create a folder named  `controllers`  in your project/app directory (if it doesn't already exist).
2.  Add your controller files inside this folder (e.g.,  `product.py`).
3.  Use the  `@controller_for`  decorator to link the controller to the  `Product`  model.

This setup ensures that the  `before_create`  hook is called whenever a new  `Product`  is created, allowing you to validate or modify the payload before saving it to the database.

----------

## Advanced Configuration

### Excluding apps or models

Lazy Ninja supports exclusion configuration. You can exclude entire apps or specific models by providing an `exclude` configuration.

For example:

```python
from lazy_ninja.builder import DynamicAPI 
# Exclude an entire app (e.g., Django's internal apps are excluded by default) 
# and/or specific models. 
exclude_config = { 
	"blog": True, # Exclude all models from this app
	"store": { "Product", "Comment"} # Exclude specific models from this app
}

auto_api = DynamicAPI(api,exclude=exclude_config)
auto_api.init()
```
In the configuration above, setting a value to **True** means the entire app is excluded, while providing a set will exclude only the specified models. If no configuration is provided for an app (or set to None), the app is included.

----------

## Query Features

### Filtering

Simple filtering is supported, and the query string can be formatted in several ways:

-   `"published=true"` translates to filtering by the `published` field.
    
-   `"views>10"` translates to filtering where `views` is greater than 10.
    
-   `"title=test"` uses a case-insensitive `icontains` filter on the `title` field.
    

Example filter parsing:
```http
GET /api/products/?q=in_stock=true&price>12
```
This filters products to show only those where in_stock is true and price is greater than 12.
### Sorting

Sorting is supported via query parameters. For example:

```http
GET /api/products/?sort=price&order=desc&sort=name&order=asc&page=1
```
This sorts products first by `price` in **descending order** (`desc`), then by `name` in **ascending order** (`asc`) for items with the same price.

### Pagination
Built-in support for pagination, allowing you to efficiently navigate through large datasets by splitting results into manageable chunks. You can control pagination using query parameters in your API requests. Two strategies are supported: **Limit-Offset** (default) and **Page Number**.

#### Limit-Offset Pagination (Default)
This strategy lets you specify how many items to return (`limit`) and how many to skip (`offset`).
**Example:**
```http
GET /api/products/?limit=3&offset=2
```
Returns 3 products, starting after the 2nd item (items 3, 4, and 5).

#### Page Number Pagination
This strategy uses page numbers to navigate results. You specify the `page` number, and the page size is configurable.

**Example:**
```http
GET /api/products/?page=2
```
Returns the second page of products.

**Note:** To set the page size (e.g., 10 items per page), define `NINJA_PAGINATION_PER_PAGE` in your Django `settings.py`. For example:
```python
NINJA_PAGINATION_PER_PAGE = 10
```
See [Django Ninja Pagination Docs](https://django-ninja.dev/guides/response/pagination/) for more details.

#### Configuring Pagination

By default, Lazy Ninja uses Limit-Offset pagination. To switch to Page Number pagination or customize the strategy, pass the pagination_type parameter when initializing DynamicAPI:

```python
api = DynamicAPI(api, pagination_type="page-number")
```

Alternatively, set NINJA_PAGINATION_CLASS in settings.py to override the default globally.

### License
This project is licensed under the terms of the MIT license.