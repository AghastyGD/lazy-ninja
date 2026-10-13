# Model relationships

Generated schemas and CRUD routes support forward `ForeignKey`, `OneToOneField`, and automatic `ManyToManyField` relationships. Relation values are IDs; responses do not nest related objects.

```json
{
  "title": "Article",
  "category": 7,
  "detail": 12,
  "tags": [3, 5]
}
```

For a many-to-many field, POST accepts a list of related IDs and defaults to an empty list when omitted. PATCH replaces the relation when supplied; omit the field to keep it unchanged, or send `[]` to clear it. All referenced IDs are validated before the model is saved. An unknown ID returns HTTP 400. Model creation and relation assignment use one database transaction.

Nullable one-to-one fields accept `null`. Foreign-key and one-to-one values use the target field's type, including UUID and non-primary-key targets. Generated list routes prefetch many-to-many fields to avoid a query per row.

Many-to-many relations with an explicit `through` model are read-only in generated write schemas, since their intermediate rows can require additional fields or rules. Use a custom schema and controller for that workflow. Reverse relations are not included in generated schemas; expose them through a custom response schema or dedicated endpoint when needed. Project policies must validate whether a caller may reference a related record.

If you use custom create or update schemas, declare a many-to-many field as a list of IDs to write it. `generate_schema(model, write=True)` creates a default writable schema; `generate_schema(model, update=True, write=True)` creates its PATCH counterpart.
