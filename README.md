
# Lazy Ninja 🥷

  

**Lazy Ninja** is a Django library that automates the generation of CRUD API endpoints using Django Ninja. It dynamically scans your Django models and creates Pydantic schemas for listing, detailing, creating, and updating records—all while allowing you to customize behavior via hook functions (controllers) and schema configurations.

  

By leveraging Django Ninja, Lazy Ninja benefits from automatic, interactive API documentation generated through OpenAPI, giving developers an intuitive interface to quickly visualize and interact with API endpoints.

----------

> **Important Note:** This pre-release (alpha) version only supports JSON data.  `multipart/form-data` (file uploads) is *not* supported.  For `ImageField`/`FileField` fields, store the full URL as a string. See the [Roadmap](#roadmap) for future plans.

----------

<details>
  <summary>Table of Contents</summary>
  
- [Lazy Ninja 🥷](#lazy-ninja-)
  - [Installation](#installation)
  - [Quick Start](#quick-start)
  - [Features](#features)
  - [Usage](#usage)
    - [Automatic route generation](#automatic-route-generation)
    - [Customizing schemas](#customizing-schemas)
    - [Controller hooks and model registry](#controller-hooks-and-model-registry)
  - [Configuration options](#configuration-options)
  - [Roadmap](#roadmap)
  - [License](#license)
  - [Contact](#contact)

</details>

----------



## Installation

Install Lazy Ninja via pip:

```bash
pip install lazy-ninja
```

Alternatively, clone the repository and install locally:

```bash
git clone https://github.com/AghastyGD/lazy-ninja.git
cd lazy-ninja
pip install -e .
```

----------

## Quick Start

Here’s a simple example of integrating Lazy Ninja into your Django project to automatically generate CRUD endpoints:

```python
# django_project/core/api.py

from ninja import NinjaAPI
from lazy_ninja.builder import DynamicAPI 

api = NinjaAPI()

# Initialize the DynamicAPI instance
dynamic_api = DynamicAPI(api)

# Automatically register routes for all Django models.
dynamic_api.register_all_models()

# Include api.urls in your project's urls.py
```

You can also customize schema generation and specify excluded apps:

```python
from ninja import NinjaAPI
from lazy_ninja.builder import DynamicAPI

api = NinjaAPI()

# Optional: Schema configuration for models (e.g., excluding fields or marking fields as optional)
schema_config = {
    "Genre": {"optional_fields": ["slug"], "exclude": ["id"]}, # "id" excluded from create/update by default
}

# Custom schemas for specific models
custom_schemas = {
    "Tag": {
        "list": TagListSchema,
        "detail": TagDetailSchema,
        "create": TagCreateSchema,
        "update": TagUpdateSchema,
    }
}

# Instantiate DynamicAPI with your custom settings.
# By default, the following apps are excluded: {"auth", "contenttypes", "admin", "sessions"}.
# To generate endpoints for these apps, pass an empty set.
dynamic_api = DynamicAPI(
    api,
    schema_config=schema_config,
    custom_schemas=custom_schemas,
    excluded_apps={"auth", "contenttypes", "admin", "sessions"}
)

dynamic_api.register_all_models()
```
----------

## Features

-   **Automatic CRUD endpoints:**  
    Scans all installed Django models (excluding specified apps) and automatically registers CRUD routes using Django Ninja.
    
-   **Dynamic schema generation:**  
    Uses Pydantic (via Django Ninja) to generate schemas for listing, detailing, creating, and updating models, with options to exclude or mark fields as optional.
    
-   **Custom controllers (Hooks):**  
    Override default behavior by registering custom controllers via the Model Registry. Available hooks include:
    
    -   **before_create:** Modify the creation payload.
    -   **after_create:** Post-process after record creation.
    -   **before_update / after_update:** Adjust data during updates.
    -   **before_delete / after_delete:** Handle pre- and post-deletion logic.
    -   **pre_list / post_list:** Filter or transform list results.
    -   **custom_response:** Customize the API response.

----------

## Usage

### Automatic route generation

For example, a model named `Book` will have endpoints like:

-   `GET /book/` for listing
-   `GET /book/{id}` for detail
-   `POST /book/` for creation
-   `PUT /book/{id}` for update
-   `DELETE /book/{id}` for deletion

### Customizing schemas

1.  **Schema config:**  
    Provide a dictionary mapping model names to configuration settings. For example:
    
	  ```python
	    schema_config = {
	        "Book": {"optional_fields": ["description"], "exclude": ["id"]},
	    }
	   ```
    
2.  **Custom schemas:**  
    Provide your own Pydantic schema classes for specific operations:
	   ```python    
	    custom_schemas = {
	        "Book": {
	            "list": BookListSchema,
	            "detail": BookDetailSchema,
	            "create": BookCreateSchema,
	            "update": BookUpdateSchema,
	        }
	    }
	 ```
	 
### Controller hooks and model registry
As we see above, Lazy Ninja allows you to register custom controllers that override the default behavior. A custom controller can modify the payload before creating or updating an object, or perform actions after deletion.

To use custom controllers:

1.  **Organize your controllers:**  
    Create a `controllers` directory (with an `__init__.py`) in your Django app and add your controller files (e.g., `book.py`, `genre.py`). Then, In the directory's `__init__.py`, import your controllers:
    ```python
    # django_project/core/controllers/__init__.py

    from .genre import GenreController
    from .book import BookController
    ````
    
2.  **Register controllers:**  
    In your controller file (e.g., `book.py`), define and register a controller:
    
    ```python
    # django_project/core/controllers/book.py
    
    from django.utils.text import slugify
    from lazy_ninja.base import BaseModelController
    from lazy_ninja.registry import ModelRegistry
    
    class BookController(BaseModelController):
     @classmethod
        def before_create(cls, request, payload, create_schema):
            """
            Hook executed before creating a new Book.
            It validates the 'title' field against forbidden words,
            converts it to lowercase, and automatically generates a slug.
            """
            forbidden_words = ["forbidden", "banned", "test"]
            payload_data = payload.model_dump()
    
            for word in forbidden_words:
                if word in payload_data['title'].lower():
                    raise ValueError(f"Invalid title: contains forbidden word '{word}'")
            
            payload_data['title'] = payload_data['title'].lower()
            payload_data['slug'] = slugify(payload_data['title'])
            
            return create_schema(**payload_data)
    
     @classmethod
        def before_update(cls, request, instance, payload, update_schema):
            """
            Hook executed before updating an existing Book.
            If the 'title' field is updated, it automatically updates the slug.
            """
            payload_data = payload.model_dump()
            if 'title' in payload_data:
                payload_data['slug'] = slugify(payload_data['title'])
            return update_schema(**payload_data)
    
    # Register the controller for the Book model.
    ModelRegistry.register_controller("Book", BookController)
    ```
    
3.  **Auto-load controllers:**  
    Update your `apps.py` file to import the controllers package when your app is ready:
    
    ```python
    # django_project/core/apps.py
    
    from django.apps import AppConfig
    
    class CoreConfig(AppConfig):
        default_auto_field = 'django.db.models.BigAutoField'
        name = 'core'
        
        def ready(self):
            import core.controllers  # Automatically imports all controllers
    ```

----------

## Configuration options

-   **excluded_apps:**  
    Lazy Ninja automatically skips models from apps like `auth`, `contenttypes`, `admin`, and `sessions`. You can override this by passing your own set of apps when initializing DynamicAPI.
    
-   **schema_config:**  
    Define which fields to exclude or mark as optional for each model.
    
-   **custom_schemas:**  
    Provide custom Pydantic schemas for list, detail, create, and update operations for specific models.
    

----------

## Roadmap

- [x] **Basic CRUD operations:**  Support for listing, retrieving, creating, updating, and deleting objects for Django models (JSON only).
- [ ] **File upload:**
    - [ ] Support for `multipart/form-data` uploads.
    - [ ] Configurable automatic handling of `ImageField` and `FileField`.
    - [ ] Option for custom upload handling via hooks.
    - [ ] Support single and multiple files fields.
- [ ] **Asynchronous operations:**
    - [ ] Make all CRUD operations asynchronous by default (using Django's async ORM).
    - [ ] Provide an option to use synchronous operations for specific models or globally.
- [ ] **Authentication and RBAC:**
    - [ ] Planned integration of token-based authentication.
    - [ ] Role-based access control to protect automatically generated routes.
- [ ] **Centralized schema and security config:**
    - [ ] Future versions may allow combining schema customization and security settings into a single configuration object.
- [ ] **Advanced model relationships:**
    - [ ] Improved handling of relationships (foreign keys, many-to-many).
    - [ ] Support for nested schemas.
- [ ] **Filtering and sorting:**
    - [ ] Built-in support for filtering and sorting list results based on query parameters.
- [ ] **Pagination:**
    - [ ] Configurable pagination for list results.
- [ ] **Customizable endpoints:**
     - [ ] Allow to add custom extra endpoints.
- [ ] **API versioning:**
    - [ ] Built-in support for API versioning.


## License

This project is licensed under the MIT License.  
See the [LICENSE](LICENSE) file for details and full license text.

----------

## Contact

**Augusto Domingos**  
[www.augustodomingos.dev](https://www.augustodomingos.dev)

Project link: https://github.com/AghastyGD/lazy-ninja

Feel free to reach out for questions, suggestions, or contributions ❤️.