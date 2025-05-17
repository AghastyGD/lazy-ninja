
# Lazy Ninja 

**Lazy Ninja** is a Django library that simplifies the generation of API endpoints using Django Ninja. It dynamically scans your Django models and generates Pydantic schemas for listing, retrieving, creating, and updating records. The library also allows you to customize behavior through hook functions (controllers) and schema configurations.

By leveraging Django Ninja, Lazy Ninja provides automatic, interactive API documentation via OpenAPI, making it easy to visualize and interact with your endpoints.

---

## Installation

Install Lazy Ninja via pip:

```bash
pip install lazy-ninja
```

For contributors or those who want the latest code, install from source:

```bash
git clone https://github.com/AghastyGD/lazy-ninja.git
cd lazy-ninja
pip install -r requirements.dev.txt
pip install -e .
```

---

## Quick Start

Here’s a simple example of integrating Lazy Ninja into your Django project:

```python
from ninja import NinjaAPI
from lazy_ninja.builder import DynamicAPI 

api = NinjaAPI()
auto_api = DynamicAPI(api)
auto_api.init()
```

Add `api.urls` to your `urls.py` to expose the endpoints.

---

## Features

- **Automatic Endpoints**: Instantly generate API routes for your Django models.
- **Dynamic Schema Generation**: Automatically create Pydantic schemas for your models.
- **Custom Controllers**: Customize route behavior with hooks like `before_create` and `after_update`.
- **Built-in Filtering, Sorting, and Pagination**: Simplify data handling with query parameters.
- **Interactive Documentation**: Swagger UI and ReDoc support out of the box.

---

## Roadmap

- [x] Basic CRUD operations  
- [x] Asynchronous support  
- [x] Filtering, sorting, and pagination  
- [X] File upload support  
- [ ] Authentication and RBAC  
- [ ] Advanced model relationships  

---

## Contributing

Contributions are welcome! Feel free to fork the repository and submit a pull request with any improvements or bug fixes.

---

## License

This project is licensed under the MIT License.  
See the [LICENSE](LICENSE) file for details and full license text.

----------

## Learn More

For complete documentation, including advanced usage, configuration options, and examples, visit the [Lazy Ninja Documentation](https://lazy-ninja.readthedocs.io).