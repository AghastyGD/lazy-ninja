# Lazy Ninja

**Lazy Ninja** is a django library that automates the generation of CRUD API endpoints using Django Ninja. It dynamically scans your django models and creates pydantic schemas for listing, detailing, creating, and updating records—all while allowing you to customize behavior via hook functions (controllers) and schema configurations.

By leveraging django ninja, lazy ninja benefits from automatic, interactive API documentation generated through OpenAPI. This integration provides developers with an intuitive interface to visualize and interact with the API endpoints, streamlining the development and testing processes.

----------

## Table of contents

- [Lazy Ninja](#lazy-ninja)
  - [Table of contents](#table-of-contents)
  - [Installation](#installation)
  - [Quick start](#quick-start)
  - [Features](#features)
  - [Usage](#usage)
    - [Automatic route generation](#automatic-route-generation)
    - [Customizing schemas](#customizing-schemas)
    - [Controller hooks and model registry](#controller-hooks-and-model-registry)
  - [Configuration options](#configuration-options)
    - [excluded\_apps](#excluded_apps)
    - [schema\_config](#schema_config)
    - [custom\_schemas](#custom_schemas)
  - [Future enhancements](#future-enhancements)

----------

## Installation

You can install Lazy Ninja via pip:

```bash
pip install lazy-ninja`
```` 

Alternatively, you can clone the GitHub repository and install it locally:

```bash
git clone https://github.com/AghastyGD/lazy-ninja.git
cd lazy-ninja
pip install -e .
```
----------

## Quick start

Here is a simple example of how to integrate Lazy Ninja into your Django project:

```python
#django_project/core/api.py

from ninja import NinjaAPI
from lazy_ninja.builder import DynamicAPI 

api = NinjaAPI()

 #Optional: schema configuration for models (e.g., excluding fields or marking fields optional)
schema_config = {
    "Genre": {"optional_fields": ["slug"], "exclude": ["id"]},
}

#Optional: custom schemas for specific models can be provided
custom_schemas = {
    "Tag": {
        "list": TagListSchema,
        "detail": TagDetailSchema,
        "create": TagCreateSchema,
        "update": TagUpdateSchema,
    }
}

#Initialize the DynamicAPI instance
dynamic_api = DynamicAPI(api, schema_config=schema_config, custom_schemas=custom_schemas)

#Automatically register routes for all Django models
dynamic_api.register_all_models()

#Now include api.urls in your project's urls.py` 

```



## Features

-   **Automatic CRUD endpoints:**  
    Lazy Ninja scans all installed Django models (excluding specified apps) and automatically registers CRUD routes using Django Ninja.
    
-   **Dynamic schema generation:**  
    Uses Pydantic (via Django Ninja) to generate schemas for listing, detailing, creating, and updating models.  
    Customization options allow you to exclude certain fields (e.g., `id`) or mark fields as optional.
    
-   **Custom controllers (hooks):**  
    Override default behavior by registering custom controllers via the Model Registry.  
    Available hooks include:
    
    -   `before_create`
    -   `after_create`
    -   `before_update`
    -   `after_update`
    -   `before_delete`
    -   `after_delete`
    -   `pre_list` and `post_list`
    -   `custom_response`
-   **Extensibility:**  
    The library is designed to be extended. Future releases plan to include built-in authentication and centralized schema/security configuration.
    

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

You can customize how schemas are generated in two ways:

1.  **Schema config:**  
    Provide a dictionary mapping model names to configuration settings. For example:
    
    ````python
    schema_config = {
        "Book": {"optional_fields": ["description"], "exclude": ["id"]},
    } 
	 ````
 
2.  **Custom schemas:**  
    Provide your own Pydantic schema classes for specific operations:
	   ````python
	    custom_schemas = {
	        "Book": {
	            "list": BookListSchema,
	            "detail": BookDetailSchema,
	            "create": BookCreateSchema,
	            "update": BookUpdateSchema,
	        }
	    }
	   ````
    
### Controller hooks and model registry

**Lazy Ninja** allows you to register custom controllers that override the default behavior.  
A custom controller can modify the payload before creating or updating an object, or perform actions after deletion.

To use custom controllers, follow these steps:

1.  **Create the  `__init__.py`  file in the  controllers  directory**:
     Ensure that the  controllers  directory has an  `__init__.py`  file to make it a Python package. This file can contain import statements for the controller modules.
	````python
	# django_project/core/controllers/__init__.py
	from .book import BookController
	from .genre import GenreController
	````
2. **Create custom controller files**:
Create individual controller files like  `book.py`  and  `genre.py`  in the  controllers  directory. 	Here is an example of a custom controller for the  `Book`  model:
	````python
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

	#Register the controller for the Book model.
	ModelRegistry.register_controller("Book", BookController) 
	````
3. 	**Update the  apps.py  file to import the controllers**:
	Modify the  ready  method in the  CoreConfig  class to import the  controllers  package. This ensures that all controllers are registered when the application is ready.
	````python 
	# django_project/core/apps.py
	
	from django.apps import AppConfig
	import importlib

	class CoreConfig(AppConfig):
	    default_auto_field = 'django.db.models.BigAutoField'
	    name = 'core'
	    
	    def ready(self):
	        import core.controllers  # Imports all controllers
	````

----
## Configuration options

### excluded_apps

**Lazy Ninja** automatically skips models from apps like `auth`, `contenttypes`, `admin`, and `sessions`. You can pass your own set of excluded apps when initializing DynamicAPI.

### schema_config

Pass a dictionary to define which fields to exclude or mark as optional for each model.

### custom_schemas

Pass a dictionary mapping model names to custom Pydantic schemas for list, detail, create, and update operations.

----------

## Future enhancements

-   **Authentication and RBAC:**  
    Planned integration of authentication features (e.g., token-based, JWT) and role-based access control (RBAC) to protect automatically generated routes.
    
-   **Centralized schema and security config:**  
    Future versions may allow you to define both schema customization and security settings in a single configuration object, reducing redundancy.
    
-   **Advanced model relationships:**  
    Better handling of relationships (foreign keys, many-to-many) and nested schemas.