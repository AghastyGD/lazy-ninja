# Authorization for generated routes

Generated CRUD routes support an optional permission policy. Configure it on `DynamicAPI`:

```python
from ninja import NinjaAPI
from lazy_ninja.builder import DynamicAPI
from lazy_ninja.permissions import DjangoModelPermissions

api = NinjaAPI()
dynamic = DynamicAPI(api, auth=True, permission_policy=DjangoModelPermissions())
dynamic.init()
```

`auth=True` enables Lazy Ninja's JWT authenticator. You can instead configure any Django Ninja authenticator that returns a Django user. The permission policy is opt-in. Existing projects that omit it retain their previous CRUD access rules. JWT authentication alone does not grant model permissions.

## Django groups and permissions

`DjangoModelPermissions` uses Django's existing users, groups, authentication backends, and model permissions. It does not create role tables or encode roles in tokens. Grant model permissions directly or through groups:

| Route action | Required Django permission |
| --- | --- |
| List and retrieve | `view_<model>` |
| Create | `add_<model>` |
| Update | `change_<model>` |
| Delete | `delete_<model>` |

The permission name includes the model's app label. The authenticator's returned user is read on each request, so permission changes take effect on the next request. An unauthenticated or inactive user receives HTTP 401; a user without the required permission receives HTTP 403.

For an authenticator that returns another value, pass `DjangoModelPermissions(user_resolver=...)`. The resolver receives the request and must return an active Django user. Failed resolution returns HTTP 401.

## Queryset and object restrictions

The built-in policy leaves querysets unscoped and checks model permissions. Django's default `ModelBackend` does not implement object permissions. If your project has an object-permission backend, use `DjangoModelPermissions(check_object_permissions=True)`; the user must still pass the model permission check before lookup.

For ownership or tenant boundaries, subclass the policy and scope the queryset. A record outside the scope returns HTTP 404. You can also override `has_permission` for per-record decisions, which return HTTP 403 after lookup:

```python
class TenantPermissions(DjangoModelPermissions):
    def scope_queryset(self, request, model, action, queryset):
        return queryset.filter(tenant_id=request.auth.tenant_id)

    def has_permission(self, request, model, action, obj=None):
        return super().has_permission(request, model, action, obj) and (
            obj is None or obj.tenant_id == request.auth.tenant_id
        )
```

Custom policies passed as `permission_policy` implement `has_permission(request, model, action, obj=None)` and `scope_queryset(request, model, action, queryset)`. They must reject unauthenticated callers themselves, usually with `ninja.errors.HttpError(401, ...)`. The scope method must return a queryset for the routed model. It runs before list filtering and pagination or object lookup, and runs again after a `pre_list` hook. Model permission checks happen before hooks and mutations. For retrieve, update, and delete, an object check happens after scoped lookup and before serialization or mutation.

Authorization of referenced foreign-key, one-to-one, or many-to-many records, ownership defaults on create, and field-level restrictions belong in a project-specific policy, schema, or hook. The configured `AUTH_USER_MODEL` is never exposed by generated CRUD routes.

## Migration

1. Keep your existing Django Ninja authenticator, or enable Lazy Ninja's built-in authentication with `auth=True`.
2. Grant the relevant Django model permissions to users or groups.
3. Add `permission_policy=DjangoModelPermissions()` to `DynamicAPI`.
4. Add queryset scoping or object checks before using generated routes for tenant-owned data.

The same policy is used by synchronous and asynchronous routes. Projects using object permissions should verify their authentication backend supports `user.has_perm(permission, obj)`.
