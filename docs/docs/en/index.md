# Lazy Ninja: Generate API Endpoints for Django

[![PyPI version](https://badge.fury.io/py/lazy-ninja.svg)](https://badge.fury.io/py/lazy-ninja)
[![Downloads](https://static.pepy.tech/personalized-badge/lazy-ninja?period=total&units=international_system&left_color=grey&right_color=blue&left_text=Downloads)](https://pepy.tech/project/lazy-ninja)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Lazy Ninja** is a Django library that automates the generation of API endpoints with Django Ninja. It dynamically scans your Django models and creates Pydantic schemas for listing, detailing, creating, and updating records—all while allowing you to customize behavior via hook functions (controllers) and schema configurations.

By leveraging Django Ninja, Lazy Ninja benefits from automatic, interactive API documentation generated through OpenAPI (Swagger UI and ReDoc), giving developers an intuitive interface to quickly visualize and interact with API endpoints.

>**Async by Default**: Lazy Ninja is designed to be asynchronous by default, leveraging Django's async capabilities for better performance. However, if needed, you can configure it to use synchronous operations by setting the `is_async` parameter to `False`.

**Key Features:**

-   **Instant API Endpoints:** Automatically generate API endpoints from Django models.
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

### Instant API Endpoints

Your API is now live at  `http://localhost:8000/api`  with these endpoints:

| Method |  URL               | Action         |
| ------ | -------------------| ---------------| 
| GET    | /api/products/     | List products  |
| POST   | /api/products/     | Create product |
| GET    | /api/products/{id} | Get product    |
| PATCH  | /api/products/{id} | Update product |
| DELETE | /api/products/{id} | Delete product |

----------

### Interactive Documentation

Access auto-generated documentation through:

#### Swagger UI

`http://localhost:8000/api/docs`

![Swagger UI](../images/sample/swagger.png)

----------

## CLI Usage

Lazy Ninja ships with a **Command Line Interface (CLI)** to speed up common tasks:

-   Scaffold a new Django project with Lazy Ninja preconfigured.
    
-   Generate OpenAPI clients/SDKs for multiple languages.
    

It removes boilerplate and keeps backend ↔ frontend integration consistent.

----------

### Overview

-   `lazy-ninja init` (alias `startproject`) — create a Django project scaffold (`api.py`, `urls.py` ready).
    
-   `lazy-ninja generate-client` — generate OpenAPI clients/SDKs (TypeScript, Dart, Python, Java, Go, C#, Ruby, Swift, etc.).
    
-   CLI auto-exports your schema from Django + Ninja (no server run needed), or you can provide `--schema`.
    

----------

### Prerequisites

-   **`generate-client`** needs `openapi-generator-cli`.
    
    -   Install with `pip install lazy-ninja[standard]` (includes JDK via `jdk4py`).
        
    -   If you already have Java: `pip install lazy-ninja[no-jdk]`.
        
-   For `typescript-types`: requires **Node.js/npm** (uses `npx openapi-typescript`).
    
-   Offline mode: pre-generate schema and use `--schema openapi.json`.
    

----------

### `init` — Project scaffold
```bash
lazy-ninja init myproject --title "My API"
``` 

Creates a Django project, adds `api.py` + `urls.py`, and comments in `settings.py` showing how to enable the API.

----------

### `generate-client` — Client/SDK generation

`lazy-ninja generate-client <language> \
  --settings myproject.settings \
  --api-module myproject.api \
  --output ./clients/<target>` 

Options:

-   `<language>` — generator name (`typescript-axios`, `python`, `dart`, etc.).
    
-   `--schema` — skip Django import, use a pre-generated OpenAPI JSON.
    
-   `--api-var` — defaults to `api`.
    

Examples:
```bash
# TypeScript axios client 
lazy-ninja generate-client typescript-axios --settings myproject.settings --output ./clients/ts-axios
 
# Dart client 
lazy-ninja generate-client dart --settings myproject.settings --output ./clients/dart

# From pre-generated schema 
lazy-ninja generate-client python --schema ./openapi.json --output ./clients/python
``` 

----------

### Supported generators

-   `typescript-types` (via `npx openapi-typescript`)
    
-   `typescript-axios`, `typescript-fetch`
    
-   `dart`, `dart-dio`
    
-   `python`
    
-   `java`, `kotlin`, `go`, `csharp`, `ruby`, `swift5`  
    _(see `GENERATOR_CONFIG` for full list)_
    

----------

### Benefits

-   **Zero-boilerplate** — scaffold project + API with one command.
    
-   **Automatic schema export** — generate clients without running the server.
    
-   **Multi-target** — TypeScript clients for frontend, SDKs for backend.
    
-   **Offline ready** — use `--schema` for CI/CD or locked-down environments.


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

---
## File Upload Support

Lazy Ninja supports handling file uploads for models with `FileField` and `ImageField` using `multipart/form-data`. This feature allows you to define which fields should use `multipart/form-data` and provides flexibility to handle mixed models where some routes use JSON while others use `multipart/form-data`.

### How to Use File Upload Parameters

When initializing `DynamicAPI`, you can configure the following parameters:

- **`file_fields`**: Specify which fields in a model should use `multipart/form-data`.
- **`use_multipart`**: Explicitly define whether `create` and `update` operations for specific models should use `multipart/form-data`.
- **`auto_detect_files`**: Automatically detect `FileField` and `ImageField` in models (default: `True`).
- **`auto_multipart`**: Automatically enable `multipart/form-data` for models with detected file fields (default: `True`).

### Example Usage
```python
from ninja import NinjaAPI
from lazy_ninja.builder import DynamicAPI

api = NinjaAPI()

auto_api = DynamicAPI(
    api,
    is_async=True,
    file_fields={"Gallery": ["images"], "Product": ["pimages"]},  # Specify file fields
    use_multipart={
        "Product": {
            "create": True,  # Use multipart/form-data for creation
            "update": True   # Use multipart/form-data for updates
        }
    },
    auto_multipart=False  # Disable automatic multipart/form-data for detected file fields
)

auto_api.register_all_models()
```

In this example:
- The `Gallery` model will use `multipart/form-data` for the `images` field.
- The `Product` model will use `multipart/form-data` for the `pimages` field during `create` and `update` operations.
- Models without file fields will continue to use JSON by default.

>By default, `auto_multipart` is True and routes for models with file fields will use `multipart/form-data` automatically. If you want to disable this behavior, set auto_multipart=False.

---

## Custom Middleware for PUT/PATCH with Multipart

To handle `PUT` and `PATCH` requests with `multipart/form-data`, Lazy Ninja includes a custom middleware: `ProcessPutPatchMiddleware`. This middleware ensures that `PUT` and `PATCH` requests are processed correctly by temporarily converting them to `POST` for form data handling.

### Why This Middleware is Needed
Django has a known limitation where `PUT` and `PATCH` requests with `multipart/form-data` are not processed correctly. While Django Ninja recently introduced updates to address this, certain scenarios still require a custom solution. This middleware resolves those issues and ensures compatibility with both synchronous and asynchronous request handlers.

### How to Use the Middleware
Add the middleware to your Django project's `MIDDLEWARE` setting:
```python
MIDDLEWARE = [
    ...
    'lazy_ninja.middleware.ProcessPutPatchMiddleware',
    ...
]
```

### How It Works
- Converts `PUT` and `PATCH` requests with `multipart/form-data` to `POST` temporarily for proper processing.
- Restores the original HTTP method after processing the request.

---

## Contributing & Feedback
Lazy Ninja is still evolving — contributions, suggestions, and feedback are more than welcome! Feel free to open issues, discuss ideas, or submit PRs.

## License
This project is licensed under the terms of the MIT license.