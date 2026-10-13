# RBAC permission model

This is the design for a future, opt-in authorization layer on generated CRUD routes. It is **not implemented yet**. JWT authentication identifies a caller; it does not grant that caller access to every model or record.

## Source of roles and permissions

Lazy Ninja should use Django's existing users, groups, permissions, and authentication backends. It should not create its own role tables or encode roles in JWTs. Role membership and permission changes must take effect on the next request without waiting for a token to expire.

The built-in policy should map generated operations to Django model permissions:

| Operation | Django permission |
| --- | --- |
| List and retrieve | `view_<model>` |
| Create | `add_<model>` |
| Update | `change_<model>` |
| Delete | `delete_<model>` |

Applications can grant those permissions directly or through Django groups. A custom Django auth backend can implement object permissions. Authentication failures remain HTTP 401; an authenticated caller without permission receives HTTP 403.

## Proposed library contract

`DynamicAPI` should accept an optional `permission_policy` object. Omitting it preserves current behavior for existing users of the library. An included `DjangoModelPermissions` policy uses the mapping above. A custom policy must be usable by both synchronous and asynchronous routers and should provide:

```python
class PermissionPolicy:
    def has_permission(self, request, model, action, obj=None) -> bool:
        """Check model or object access for list, retrieve, create, update, delete."""

    def scope_queryset(self, request, model, action, queryset):
        """Return the records visible for list, retrieve, update, or delete."""
```

The caller identity should come from the Django user returned by the API authenticator. Projects using an authenticator that returns another type must supply an explicit user resolver. Authorization must fail closed when the configured policy cannot resolve a user.

## Enforcement order

1. Authenticate with the API's configured authenticator.
2. Check model permission before running the operation.
3. For list, retrieve, update, and delete, apply `scope_queryset` before filtering, pagination, or object lookup. An object outside the scope should return HTTP 404.
4. For retrieve, update, and delete, check object permission after lookup and before serialization or mutation.
5. For create, check model permission before saving. Project-specific constraints on submitted fields and ownership remain in custom schemas or hooks.

The default Django policy may return the original queryset after a successful model permission check. Multi-tenant or ownership-sensitive projects must supply a policy that scopes it; object checks alone cannot protect list results or counts. The configured `AUTH_USER_MODEL` remains excluded from generated CRUD routes.

## Release criteria

- The same permission decisions and HTTP responses in sync and async routers.
- Tests for each CRUD action, anonymous users, users with and without permissions, custom user models, scoped lists, object access, and mutation denial.
- A migration guide explaining that RBAC is opt-in and documenting how to enable it without changing unrelated authentication settings.
- Clear documentation that Django's default model backend does not provide object permissions; projects needing them must use a compatible backend or custom policy.
