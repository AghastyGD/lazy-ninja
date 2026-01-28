# Type Safety Guide for Lazy Ninja Contributors

This document explains how we handle type safety in Lazy Ninja, a framework that heavily uses metaprogramming.

## The Challenge

Lazy Ninja generates code **dynamically at runtime**:
- Discovers Django models via reflection
- Generates Pydantic schemas automatically  
- Creates API routes programmatically

Type checkers (Pylance/mypy) work **statically** - they analyze code without running it. This creates a fundamental conflict.

## Our Approach

We balance type safety with the dynamic nature of the framework using:

### 1. Type Guards (`utils/type_guards.py`)

Encapsulate runtime checks in reusable functions:

```python
# ❌ Bad: Inline checks scattered everywhere
if hasattr(User, "username"):
    field = User._meta.get_field("username")
    if getattr(field, "unique", False):
        # ...

# ✅ Good: Reusable type guard
if has_unique_field(User, "username"):
    # ...
```

**Available type guards:**
- `has_field(model, field_name)` - Check if model has field
- `has_unique_field(model, field_name)` - Check if field is unique
- `get_model_field(model, field_name)` - Safely get field
- `get_user_identifier(user)` - Get best user identifier
- `sanitize_filters(model, filters)` - Remove invalid filters
- And 20+ more...

### 2. Strategic `type: ignore`

Use **only** for Django-guaranteed attributes:

```python
# ✅ Acceptable: Django always adds .id
user.id  # type: ignore[attr-defined]

# ✅ Acceptable: Django model meta
model._meta.get_fields()  # type: ignore[attr-defined]

# ❌ Avoid: Custom attributes
user.custom_field  # type: ignore[attr-defined]  # Use hasattr instead!
```

**Rules:**
- Must be documented with inline comment
- Only for Django framework guarantees
- Include type: ignore comment type (e.g., `[attr-defined]`, `[misc]`)

### 3. Complete Type Hints

All public functions **must** have type hints:

```python
# ❌ Bad
def generate_schema(model, exclude=None):
    ...

# ✅ Good
def generate_schema(
    model: Type[Model],
    exclude: Optional[List[str]] = None,
) -> Type[BaseModel]:
    """Generate Pydantic schema from Django model.
    
    Note on typing:
        Return type is dynamically created. Use type: ignore[attr-defined]
        when accessing fields on schema instances.
    """
    ...
```

### 4. Safe Attribute Access

Use `getattr()` with defaults for optional attributes:

```python
# ❌ Risky
content_type = file.content_type  # Might not exist!

# ✅ Safe
content_type = getattr(file, "content_type", None)
if content_type:
    # Use it safely
```

### 5. Cast for Dynamic Types

When you know the type but type checker doesn't:

```python
from typing import cast, Type
from pydantic import BaseModel

schema = create_model("DynamicSchema", **fields)  # Type: Type[BaseModel] | Any
return cast(Type[BaseModel], schema)  # Now type checker knows!
```

## When to Use Each Technique

| Situation | Solution | Example |
|-----------|----------|---------|
| **Django guaranteed field** | `# type: ignore[attr-defined]` | `user.id`, `model._meta` |
| **Optional attribute** | `getattr(obj, "attr", default)` | `getattr(file, "size", 0)` |
| **Complex validation** | Type guard function | `has_unique_field(User, "email")` |
| **Dynamic type known** | `cast(TargetType, value)` | `cast(Type[BaseModel], schema)` |
| **Conditional logic** | `hasattr()` + if | `if hasattr(user, "profile")` |

## File Organization

```
lazy_ninja/
├── utils/
│   ├── type_guards.py      # All type guards (centralized!)
│   ├── schema.py           # Schema generation with type hints
│   └── base.py             # Base utilities
├── core.py                 # Route registration with type hints
├── builder.py              # DynamicAPI with type safety
└── auth.py                 # Auth module (uses type guards)
```

## Common Patterns

### Pattern 1: Model Field Access

```python
# Import type guard
from .utils.type_guards import has_field, get_model_field

# Check if field exists
if has_field(User, "email"):
    # Safe to use

# Get field safely
field = get_model_field(User, "email")
if field:
    max_length = getattr(field, "max_length", None)
```

### Pattern 2: User Identification

```python
# Import type guard
from .utils.type_guards import get_user_identifier

# Get best identifier (email > username > id)
logger.info("User action: %s", get_user_identifier(user))
```

### Pattern 3: File Upload Handling

```python
from .utils.type_guards import is_image_file, get_file_size

if is_image_file(uploaded_file):
    size = get_file_size(uploaded_file)
    if size > MAX_SIZE:
        raise ValidationError("File too large")
```

### Pattern 4: Query Filtering

```python
from .utils.type_guards import sanitize_filters

# Remove invalid filter fields
safe_filters = sanitize_filters(User, request.GET.dict())
queryset = User.objects.filter(**safe_filters)  # type: ignore[misc]
```

## Testing Type Guards

All type guards in `utils/type_guards.py` should be tested:

```python
# tests/test_type_guards.py
def test_has_unique_field():
    assert has_unique_field(User, "username") == True
    assert has_unique_field(User, "first_name") == False
    assert has_unique_field(User, "nonexistent") == False
```

## Pylance/mypy Configuration

Recommended `pyproject.toml`:

```toml
[tool.pylance]
typeCheckingMode = "basic"  # or "standard" for stricter
reportGeneralTypeIssues = "warning"
reportAttributeAccessIssue = "warning"
reportUnknownMemberType = "none"  # For highly dynamic code

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # Too strict for dynamic framework
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = "lazy_ninja.utils.schema"
disallow_any_generics = false  # Dynamic schema generation
```

## Adding New Features

When adding new features to Lazy Ninja:

1. **Start with type hints** - Define function signatures first
2. **Use type guards** - Add to `utils/type_guards.py` if reusable
3. **Document dynamic behavior** - Explain in docstrings why `type: ignore` is needed
4. **Test edge cases** - Especially around optional attributes

## Examples from Codebase

### Good: Auth Module

```python
# auth.py
from .utils.type_guards import has_unique_field, get_user_identifier

# ✅ Uses type guard
if has_unique_field(User, "username"):
    if User.objects.filter(username__iexact=username).exists():
        raise HttpError(400, "Username taken")

# ✅ Uses helper for logging
logger.info("User logged in: %s", get_user_identifier(user))

# ✅ Strategic type: ignore for Django guarantee
user.id  # type: ignore[attr-defined]
```

### Good: Schema Generation

```python
# utils/schema.py
def generate_schema(
    model: Type[models.Model],
    exclude: Optional[List[str]] = None,
) -> Type[BaseModel]:
    """Generate schema with proper type hints.
    
    Note on typing:
        Return type is dynamically created. Type checker
        cannot infer fields. Use type: ignore[attr-defined]
        when accessing schema instance fields.
    """
    fields: Dict[str, Any] = {}
    for field in model._meta.fields:  # type: ignore[attr-defined]
        field_name = getattr(field, "name", None)  # ✅ Safe access
        if field_name and field_name not in (exclude or []):
            fields[field_name] = (get_pydantic_type(field), ...)
    
    return cast(Type[BaseModel], create_model(...))  # ✅ Cast to known type
```

## Resources

- [Python Type Hints (PEP 484)](https://peps.python.org/pep-0484/)
- [Django-stubs](https://github.com/typeddjango/django-stubs) - Better Django typing
- [Pylance Documentation](https://github.com/microsoft/pylance-release)
- [Lazy Ninja Type Guards](./type_guards.py) - Our centralized type safety utilities

## Questions?

If you're unsure whether to use `type: ignore` or a type guard, ask:

1. **Is this attribute guaranteed by Django?** → `type: ignore[attr-defined]`
2. **Might this attribute not exist?** → `getattr()` or type guard
3. **Is this check used multiple times?** → Create type guard
4. **Is this for logging/debug only?** → `getattr()` with fallback

When in doubt, **prefer type guards over type: ignore**.
