from typing import Type, Callable, Optional, List, Any, Dict, Union

from django.shortcuts import get_object_or_404
from django.db.models import Model, QuerySet
from django.db import models
from asgiref.sync import sync_to_async

from ninja import Router, Schema, NinjaAPI, Form
from ninja.pagination import paginate

from .utils import (
    convert_foreign_keys,
    handle_response_async,
    serialize_model_instance_async, 
    convert_foreign_keys_async,
    get_all_objects_async, 
    get_object_or_404_async, 
    execute_hook_async, 
)
from .pagination import BasePagination
from .helpers import execute_hook, handle_response, apply_filters, apply_filters_async
from .errors import handle_exception, handle_exception_async
from .file_upload import FileUploadConfig, detect_file_fields


def register_model_routes_internal(
    api: NinjaAPI,
    model: Type[Model],
    base_url: str,
    list_schema: Type[Schema],
    detail_schema: Type[Schema],
    create_schema: Optional[Type[Schema]] = None,
    update_schema: Optional[Type[Schema]] = None,
    pre_list: Optional[Callable[[Any, Any], Any]] = None,
    before_create: Optional[Callable[[Any, Any, Type[Schema]], Any]] = None,
    after_create: Optional[Callable[[Any, Any], Any]] = None,
    before_update: Optional[Callable[[Any, Any, Type[Schema]], Any]] = None,
    after_update: Optional[Callable[[Any, Any], Any]] = None,
    before_delete: Optional[Callable[[Any, Any], None]] = None,
    after_delete: Optional[Callable[[Any], None]] = None,
    custom_response: Optional[Callable[[Any, Any], Any]] = None,
    pagination_strategy: Optional[BasePagination] = None,
    file_upload_config: Optional[FileUploadConfig] = None,
    use_multipart_create: bool = False,
    use_multipart_update: bool = False,
    is_async: bool = True 
) -> None:
    """
    Internal function that registers CRUD routes for a Django model.
    Now supports both sync and async operations.

    Args:
        api: NinjaAPI instance.
        model: Django model class.
        base_url: Base URL for the routes.
        list_schema: Schema for list responses.
        detail_schema: Schema for detail responses.
        create_schema: Schema for create requests.
        update_schema: Schema for update requests.
        pre_list/post_list: Hooks for list operation.
        before_create/after_create: Hooks for create operation.
        before_update/after_update: Hooks for update operation.
        before_delete/after_delete: Hooks for delete operation.
        custom_response: Hook for customizing response format.
        pagination_strategy: Strategy for pagination.
        is_async: Whether to use async routes (default: True).
        
    """
    router = Router()
    model_name = model.__name__.lower()
    paginator_class = pagination_strategy.get_paginator() if pagination_strategy else None
    
    if is_async:
        @router.get("/", response=List[list_schema], tags=[model.__name__], operation_id=f"list_{model_name}")
        @paginate(paginator_class)
        async def list_items(
            request,
            q: Optional[str] = None,
            sort: Optional[str] = None,
            order: Optional[str] = "asc",
            **kwargs: Any
        ) -> List[Any]:
            """List objects with optional filtering and sorting."""
            try:
                all_items = await get_all_objects_async(model)
                
                if pre_list:
                    hook_result = await execute_hook_async(pre_list, request, all_items)
                    if hook_result is not None:
                        all_items = hook_result
                
                if q or sort or kwargs:
                    all_items = await apply_filters_async(all_items, model, q, sort, order, kwargs)
                else:
                    all_items = await sync_to_async(list)(all_items)
                
                serialized_items = []
                for item in all_items:
                    serialized = await serialize_model_instance_async(item)
                    serialized_items.append(serialized)
                
                if custom_response:
                    return await sync_to_async(custom_response)(request, serialized_items)
                
                return serialized_items
            except Exception as e:
                return await handle_exception_async(e)
            
        @router.get("/{item_id}", response=detail_schema, tags=[model.__name__], operation_id=f"get_{model_name}")
        async def get_item(request, item_id: int) -> Any:
            """Retrieve a single object by ID."""
            try:
                instance = await get_object_or_404_async(model, id=item_id)
                return await handle_response_async(instance, detail_schema, custom_response, request)
            except Exception as e:
                return await handle_exception_async(e)
        
        if create_schema:
            if use_multipart_create:
                @router.post("/", response=detail_schema, tags=[model.__name__], operation_id=f"create_{model_name}")
                async def create_item(request, payload: create_schema = Form(...)) -> Any: #type: ignore
                    """Create a new object."""
                    try:
                        if before_create:
                            payload = await execute_hook_async(before_create, request, payload, create_schema) or payload
                            
                        data = payload.model_dump()
                        file_fields_map: Dict[str, list] = {}
                        
                        if file_upload_config:
                            single_file_fields = file_upload_config.get_model_file_fields(model.__name__)
                            for field_name in single_file_fields:
                                if field_name in request.FILES:
                                    data[field_name] = request.FILES[field_name]
                                    
                            multiple_file_fields = file_upload_config.get_model_multiple_file_fields(model.__name__)
                            for field_name in multiple_file_fields:
                                files = request.FILES.getlist(field_name)
                                if files:
                                    file_fields_map[field_name] = files
                                data.pop(field_name, None)
                                
                        data = await convert_foreign_keys_async(model, data)
                        
                        create_instance = sync_to_async(lambda m, **kwargs: m.objects.create(**kwargs))
                        instance = await create_instance(model, **data)
                        
                        if file_fields_map:
                            get_fields = sync_to_async(lambda m: m._meta.get_fields())
                            model_fields = await get_fields(model)
                            
                            for field_name, files in file_fields_map.items():
                                relation = next((f for f in model_fields if f.name == field_name), None)
                                if not relation:
                                    continue
                                
                                if isinstance(relation, models.ManyToManyField):
                                    target_model = relation.remote_field.model
                                elif isinstance(relation, models.ManyToOneRel):
                                    target_model = relation.related_model
                                elif isinstance(relation, models.OneToOneField):
                                    target_model = relation.related_model
                                elif isinstance(relation, models.OneToOneRel):
                                    target_model = relation.related_model
                                else:
                                    continue
                                
                                detect_files = sync_to_async(detect_file_fields)
                                single_file_fields, _ = await detect_files(target_model)
                                if not single_file_fields:
                                    continue
                                
                                file_field = single_file_fields[0]
                                
                                if isinstance(relation, models.ManyToManyField):
                                    manager = getattr(instance, field_name)
                                    clear_manager = sync_to_async(manager.clear)
                                    await clear_manager()
                                    
                                    created_objs = []
                                    for f in files:
                                        create_related = sync_to_async(lambda model, **kwargs: model.objects.create(**kwargs))
                                        obj = await create_related(target_model, **{file_field: f})
                                        created_objs.append(obj)
                                        
                                    add_to_manager = sync_to_async(lambda mgr, objs: mgr.add(*objs))
                                    await add_to_manager(manager, created_objs)
                                    
                                elif isinstance(relation, models.ManyToOneRel):
                                    fk_name = relation.field.name
                                    for f in files:
                                        create_related = sync_to_async(lambda model, **kwargs: model.objects.create(**kwargs))
                                        await create_related(target_model, **{file_field: f, fk_name: instance})
                                        
                                elif isinstance(relation, models.OneToOneField):
                                    if files:
                                        create_related = sync_to_async(lambda model, **kwargs: model.objects.create(**kwargs))
                                        related_obj = await create_related(target_model, **{file_field: files[[0]]})
                                        
                                        setattr(instance, field_name, related_obj)
                                        save_instance = sync_to_async(lambda obj: obj.save())
                                        await save_instance(instance)
                                        
                                elif isinstance(relation, models.OneToOneRel):
                                    fk_name = relation.field.name
                                    if files:
                                        create_related = sync_to_async(lambda model, **kwargs: model.objects.create(**kwargs))
                                        await create_related(target_model, **{file_field: files[0], fk_name: instance})
                                                            
                        if after_create:
                            instance = await execute_hook_async(after_create, request, instance) or instance
                            
                        return await handle_response_async(instance, detail_schema, custom_response, request)

                    except Exception as e:
                        return await handle_exception_async(e)
            else:
                @router.post("/", response=detail_schema, tags=[model.__name__], operation_id=f"create_{model_name}")
                async def create_item(request, payload: create_schema) -> Any: #type: ignore
                    """Create a new object."""
                    try:
                        if before_create:
                            payload = await execute_hook_async(before_create, request, payload, create_schema) or payload
                            
                        data = await convert_foreign_keys_async(model, payload.model_dump())
                        
                        create_instance = sync_to_async(lambda m, **kwargs: m.objects.create(**kwargs))
                        instance = await create_instance(model, **data)
                        
                        if after_create:
                            instance = await execute_hook_async(after_create, request, instance) or instance
                            
                        return await handle_response_async(instance, detail_schema, custom_response, request)

                    except Exception as e:
                        return await handle_exception_async(e)
                
        if update_schema:
            if use_multipart_update:
                @router.patch("/{item_id}", response=detail_schema, tags=[model.__name__], operation_id=f"update_{model_name}")
                async def update_item(request, item_id: int, payload: update_schema = Form(...)) -> Any: #type: ignore
                    """Update an existing object."""
                    try:
                        instance = await get_object_or_404_async(model, id=item_id)
                        
                        if before_update:
                            payload = await execute_hook_async(before_update, request, instance, payload, update_schema) or payload
                            
                            data = payload.model_dump(exclude_unset=True)
                            file_fields_map: Dict[str, list] = {}
                            
                            if file_upload_config:
                                single_file_fields = file_upload_config.get_model_file_fields(model.__name__)
                                
                                for field_name in single_file_fields:
                                    if field_name in request.FILES:
                                        data[field_name] = request.FILES[field_name]
                                        
                                multiple_file_fields = file_upload_config.get_model_multiple_file_fields(model.__name__)
                                for field_name in multiple_file_fields:
                                    files = request.FILES.getlist(field_name)
                                    if files:
                                        file_fields_map[field_name] = files
                                    data.pop(field_name, None)
                                    
                            data = await convert_foreign_keys_async(model, data)
                            
                            for key, value in data.items():
                                setattr(instance, key, value)
                                
                                save_instance = sync_to_async(lambda obj: obj.save())
                                await save_instance(instance)
                                                
                            if file_fields_map:
                                get_fields = sync_to_async(lambda m: m._meta.get_fields())
                                model_fields = await get_fields(model)
                                
                                for field_name, files in file_fields_map.items():
                                    relation = next((f for f in model_fields if f.name == field_name), None)
                                    if not relation:
                                        continue
                                    
                                    if isinstance(relation, models.ManyToManyField):
                                        target_model = relation.remote_field.model
                                    elif isinstance(relation, models.ManyToOneRel):
                                        target_model = relation.related_model
                                    elif isinstance(relation, models.OneToOneField):
                                        target_model = relation.related_model
                                    elif isinstance(relation, models.OneToOneRel):
                                        target_model = relation.related_model
                                    else:
                                        continue
                                    
                                    detect_files = sync_to_async(detect_file_fields)
                                    single_file_fields, _ = await detect_files(target_model)
                                    if not single_file_fields:
                                        continue
                                    
                                    file_field = single_file_fields[0]
                                    
                                    if isinstance(relation, models.ManyToManyField):
                                        manager = getattr(instance, field_name)
                                        clear_manager = sync_to_async(manager.clear)
                                        await clear_manager()
                                        
                                        created_objs = []
                                        for f in files:
                                            create_related = sync_to_async(lambda model, **kwargs: model.objects.create(**kwargs))
                                            obj = await create_related(target_model, **{file_field: f})
                                            created_objs.append(obj)
                                            
                                        add_to_manager = sync_to_async(lambda mgr, objs: mgr.add(*objs))
                                        await add_to_manager(manager, created_objs)
                                        
                                    elif isinstance(relation, models.ManyToOneRel):
                                        fk_name = relation.field.name
                                        for f in files:
                                            create_related = sync_to_async(lambda model, **kwargs: model.objects.create(**kwargs))
                                            await create_related(target_model, **{file_field: f, fk_name: instance})
                                            
                                    elif isinstance(relation, models.OneToOneField):
                                        if files:
                                            create_related = sync_to_async(lambda model, **kwargs: model.objects.create(**kwargs))
                                            related_obj = await create_related(target_model, **{file_field: files[[0]]})
                                            
                                            setattr(instance, field_name, related_obj)
                                            save_instance = sync_to_async(lambda obj: obj.save())
                                            await save_instance(instance)
                                            
                                    elif isinstance(relation, models.OneToOneRel):
                                        fk_name = relation.field.name
                                        if files:
                                            create_related = sync_to_async(lambda model, **kwargs: model.objects.create(**kwargs))
                                            await create_related(target_model, **{file_field: files[0], fk_name: instance})
                                                                                                        
                        if after_update:
                            instance = await execute_hook_async(after_update, request, instance) or instance
                            
                        return await handle_response_async(instance, detail_schema, custom_response, request)
                    except Exception as e:
                        return await handle_exception_async(e)
            else:
                @router.patch("/{item_id}", response=detail_schema, tags=[model.__name__], operation_id=f"update_{model_name}")
                async def update_item(request, item_id: int, payload: update_schema) -> Any: #type: ignore
                    """Update an existing object."""
                    try:
                        instance = await get_object_or_404_async(model, id=item_id)
                        
                        if before_update:
                            payload = await execute_hook_async(before_update, request, instance, payload, update_schema) or payload
                            
                        data = await convert_foreign_keys_async(model, payload.model_dump(exclude_unset=True))
                        
                        for key, value in data.items():
                            setattr(instance, key, value)
                            
                        save_instance = sync_to_async(lambda obj: obj.save())
                        await save_instance(instance)
                        
                        if after_update:
                            instance = await execute_hook_async(after_update, request, instance) or instance
                            
                        return await handle_response_async(instance, detail_schema, custom_response, request)
                    except Exception as e:
                        return await handle_exception_async(e)
        
        @router.delete("/{item_id}", response={200: Dict[str, str]}, tags=[model.__name__], operation_id=f"delete_{model_name}")
        async def delete_item(request, item_id: int) -> Dict[str, str]:
            """Delete an object."""
            try:
                instance = await get_object_or_404_async(model, id=item_id)
                
                if before_delete:
                    await execute_hook_async(before_delete, request, instance)
                    
                delete_instance = sync_to_async(lambda obj: obj.delete())
                await delete_instance(instance)
                
                if after_delete:
                    await execute_hook_async(after_delete, instance)
                    
                return {"message": f"{model.__name__} with ID {item_id} has been deleted"}
            except Exception as e:
                return await handle_exception_async(e)
    else:
        @router.get("/", response=List[list_schema], tags=[model.__name__], operation_id=f"list_{model_name}")
        @paginate(paginator_class)
        def list_items(request, q: Optional[str] = None, sort: Optional[str] = None,
                    order: Optional[str] = "asc", **kwargs: Any) -> Union[QuerySet, Any]:
            """List objects with optional filtering and sorting."""
            try:
                queryset = model.objects.all()
                if pre_list:
                    queryset = execute_hook(pre_list, request, queryset) or queryset
                    
                queryset = apply_filters(queryset, model, q, sort, order, kwargs)
                return queryset if not custom_response else custom_response(request, queryset)
            except Exception as e:
                return handle_exception(e)

        @router.get("/{item_id}", response=detail_schema, tags=[model.__name__], operation_id=f"get_{model_name}")
        def get_item(request, item_id: int) -> Any:
            """Retrieve a single object by ID."""
            try:
                instance = get_object_or_404(model, id=item_id)
                return handle_response(instance, detail_schema, custom_response, request)
            except Exception as e:
                return handle_exception(e)

        if create_schema:
            if use_multipart_create:
                @router.post("/", response=detail_schema, tags=[model.__name__], operation_id=f"create_{model_name}")
                def create_item(request, payload: create_schema = Form(...)) -> Any: #type: ignore
                    """Create a new object."""
                    try:
                        if before_create:
                            payload = execute_hook(before_create, request, payload, create_schema) or payload
                        
                        data = payload.model_dump()
                        file_fields_map: Dict[str, list] = {}
                        
                        if file_upload_config:
                            single_file_fields = file_upload_config.get_model_file_fields(model.__name__)
                            for field_name in single_file_fields:
                                if field_name in request.FILES:
                                    data[field_name] = request.FILES[field_name]
                            
                            multiple_file_fields = file_upload_config.get_model_multiple_file_fields(model.__name__)
                            for field_name in multiple_file_fields:
                                files = request.FILES.getlist(field_name)
                                if files:
                                    file_fields_map[field_name] = files
                                data.pop(field_name, None) 

                        data = convert_foreign_keys(model, data)

                        instance = model.objects.create(**data)
                        
                        for field_name, files in file_fields_map.items():
                            relation = next((f for f in model._meta.get_fields() if f.name == field_name), None)
                            if not relation:
                                continue
                                
                            if isinstance(relation, models.ManyToManyField):
                                target_model = relation.remote_field.model
                            elif isinstance(relation, models.ManyToOneRel):  
                                target_model = relation.related_model
                            elif isinstance(relation, models.OneToOneField):
                                target_model = relation.related_model
                            elif isinstance(relation, models.OneToOneRel):
                                target_model = relation.related_model
                            else:
                                continue

                            single_file_fields, _ = detect_file_fields(target_model)
                            if not single_file_fields:
                                continue

                            file_field = single_file_fields[0] 
                            
                            if isinstance(relation, models.ManyToManyField):
                                manager = getattr(instance, field_name)
                                manager.clear()
                                created_objs = []
                                for f in files:
                                    obj = target_model.objects.create(**{file_field: f})
                                    created_objs.append(obj)
                                manager.add(*created_objs)
                                
                            elif isinstance(relation, models.ManyToOneRel):
                                fk_name = relation.field.name
                                for f in files:
                                    target_model.objects.create(**{file_field: f, fk_name: instance})
                                    
                            elif isinstance(relation, models.OneToOneField):
                                if files: 
                                    related_obj = target_model.objects.create(**{file_field: files[0]})
                                    setattr(instance, field_name, related_obj)
                                    instance.save()
                                    
                            elif isinstance(relation, models.OneToOneRel):
                                fk_name = relation.field.name
                                if files:
                                    target_model.objects.create(**{file_field: files[0], fk_name: instance})

                        if after_create:
                            instance = execute_hook(after_create, request, instance) or instance
                            
                        return handle_response(instance, detail_schema, custom_response, request)
                    
                    except Exception as e:
                        return handle_exception(e)
            else:
                @router.post("/", response=detail_schema, tags=[model.__name__], operation_id=f"create_{model_name}")
                def create_item(request, payload: create_schema) -> Any: #type: ignore
                    """Create a new object."""
                    try:
                        if before_create:
                            payload = execute_hook(before_create, request, payload, create_schema) or payload
                        data = convert_foreign_keys(model, payload.model_dump())
                        instance = model.objects.create(**data)
                        if after_create:
                            instance = execute_hook(after_create, request, instance) or instance
                        return handle_response(instance, detail_schema, custom_response, request)
                    except Exception as e:
                        return handle_exception(e)

        if update_schema:
            if use_multipart_update:
                @router.patch("/{item_id}", response=detail_schema, tags=[model.__name__], operation_id=f"update_{model_name}")
                def update_item(request, item_id: int, payload: update_schema = Form(...)) -> Any: #type: ignore
                    """Update an existing object."""
                    try:
                        instance = get_object_or_404(model, id=item_id)
                        
                        if before_update:
                            payload = execute_hook(before_update, request, instance, payload, update_schema) or payload
                        
                        data = payload.model_dump(exclude_unset=True) 
                        file_fields_map: Dict[str, list] = {}
                        
                        if file_upload_config:
                            single_file_fields = file_upload_config.get_model_file_fields(model.__name__)
                            for field_name in single_file_fields:
                                if field_name in request.FILES:
                                    data[field_name] = request.FILES[field_name]
                            
                            multiple_file_fields = file_upload_config.get_model_multiple_file_fields(model.__name__)
                            for field_name in multiple_file_fields:
                                files = request.FILES.getlist(field_name)
                                if files:
                                    file_fields_map[field_name] = files
                                data.pop(field_name, None) 

                        data = convert_foreign_keys(model, data)

                        for key, value in data.items():
                            setattr(instance, key, value)
                        instance.save()
        
                        for field_name, files in file_fields_map.items():
                            relation = next((f for f in model._meta.get_fields() if f.name == field_name), None)
                            if not relation:
                                continue
                                
                            if isinstance(relation, models.ManyToManyField):
                                target_model = relation.remote_field.model
                            elif isinstance(relation, models.ManyToOneRel):  
                                target_model = relation.related_model
                            elif isinstance(relation, models.OneToOneField):
                                target_model = relation.related_model
                            elif isinstance(relation, models.OneToOneRel):
                                target_model = relation.related_model
                            else:
                                continue

                            single_file_fields, _ = detect_file_fields(target_model)
                            if not single_file_fields:
                                continue

                            file_field = single_file_fields[0] 
                            
                            if isinstance(relation, models.ManyToManyField):
                                manager = getattr(instance, field_name)
                                manager.clear()
                                created_objs = []
                                for f in files:
                                    obj = target_model.objects.create(**{file_field: f})
                                    created_objs.append(obj)
                                manager.add(*created_objs)
                                
                            elif isinstance(relation, models.ManyToOneRel):
                                fk_name = relation.field.name
                                for f in files:
                                    target_model.objects.create(**{file_field: f, fk_name: instance})
                                    
                            elif isinstance(relation, models.OneToOneField):
                                if files: 
                                    related_obj = target_model.objects.create(**{file_field: files[0]})
                                    setattr(instance, field_name, related_obj)
                                    instance.save()
                                    
                            elif isinstance(relation, models.OneToOneRel):
                                fk_name = relation.field.name
                                if files:
                                    target_model.objects.create(**{file_field: files[0], fk_name: instance})
                                    
                        if after_update:
                            instance = execute_hook(after_update, request, instance) or instance
                        return handle_response(instance, detail_schema, custom_response, request)
                    except Exception as e:
                        return handle_exception(e)
            
            else:
                @router.patch("/{item_id}", response=detail_schema, tags=[model.__name__], operation_id=f"update_{model_name}")
                def update_item(request, item_id: int, payload: update_schema) -> Any: #type: ignore
                    """Update an existing object."""
                    try:
                        instance = get_object_or_404(model, id=item_id)
                        if before_update:
                            payload = execute_hook(before_update, request, instance, payload, update_schema) or payload
                        data = convert_foreign_keys(model, payload.model_dump(exclude_unset=True))
                        
                        for key, value in data.items():
                            setattr(instance, key, value)
                        instance.save()
                        
                        if after_update:
                            instance = execute_hook(after_update, request, instance) or instance
                        return handle_response(instance, detail_schema, custom_response, request)
                    except Exception as e:
                        return handle_exception(e)

        @router.delete("/{item_id}", response={200: Dict[str, str]}, tags=[model.__name__], operation_id=f"delete_{model_name}")
        def delete_item(request, item_id: int) -> Dict[str, str]:
            """Delete an object."""
            try:
                instance = get_object_or_404(model, id=item_id)
                if before_delete:
                    execute_hook(before_delete, request, instance)
                instance.delete()
                if after_delete:
                    execute_hook(after_delete, instance)
                return {"message": f"{model.__name__} with ID {item_id} has been deleted."}
            except Exception as e:
                return handle_exception(e)

    api.add_router(base_url, router)