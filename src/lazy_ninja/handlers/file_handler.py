from typing import Dict, List, Tuple, Any, Optional
from asgiref.sync import sync_to_async

from django.db import models

from ..file_upload import FileUploadConfig, FileFieldDetector


class BaseFileHandler:
    """Base class for file upload handlers."""
    
    def __init__(self, file_upload_config: Optional[FileUploadConfig] = None):
        self.file_upload_config = file_upload_config
        self.detector = FileFieldDetector()
    
    def _extract_files_from_request(self, request, model_name: str) -> Tuple[Dict[str, Any], Dict[str, List]]:
        """Extract single and multiple files from request."""
        single_files = {}
        multiple_files = {}
        
        if not self.file_upload_config:
            return single_files, multiple_files
        
        single_file_fields = self.file_upload_config.get_model_file_fields(model_name)
        for field_name in single_file_fields:
            if field_name in request.FILES:
                single_files[field_name] = request.FILES[field_name]
        
        multiple_file_fields = self.file_upload_config.get_model_multiple_file_fields(model_name)
        for field_name in multiple_file_fields:
            files = request.FILES.getlist(field_name)
            if files:
                multiple_files[field_name] = files
        
        return single_files, multiple_files
    
    def _get_relation_info(self, model, field_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a relation field."""
        try:
            relation = next((f for f in model._meta.get_fields() if f.name == field_name), None)
            if not relation:
                return None
            
            relation_info = {
                'field': relation,
                'target_model': None,
                'relation_type': None,
                'fk_name': None
            }
            
            if isinstance(relation, models.ManyToManyField):
                relation_info['target_model'] = relation.remote_field.model
                relation_info['relation_type'] = 'many_to_many'
            elif isinstance(relation, models.ManyToOneRel):
                relation_info['target_model'] = relation.related_model
                relation_info['relation_type'] = 'many_to_one_rel'
                relation_info['fk_name'] = relation.field.name
            elif isinstance(relation, models.OneToOneField):
                relation_info['target_model'] = relation.related_model
                relation_info['relation_type'] = 'one_to_one'
            elif isinstance(relation, models.OneToOneRel):
                relation_info['target_model'] = relation.related_model
                relation_info['relation_type'] = 'one_to_one_rel'
                relation_info['fk_name'] = relation.field.name
            else:
                return None
            
            return relation_info
        except Exception:
            return None


class SyncFileHandler(BaseFileHandler):
    """Handles file upload processing for sync routes."""
    
    def process_create_files(self, request, payload, model) -> Tuple[Dict[str, Any], Dict[str, List]]:
        """Process files for create operation."""
        data = payload.model_dump()
        model_name = model.__name__
        
        single_files, multiple_files = self._extract_files_from_request(request, model_name)
        
        data.update(single_files)
        
        for field_name in multiple_files.keys():
            data.pop(field_name, None)
        
        return data, multiple_files
    
    def process_update_files(self, request, payload, model) -> Tuple[Dict[str, Any], Dict[str, List]]:
        """Process files for update operation."""
        data = payload.model_dump(exclude_unset=True)
        model_name = model.__name__
        
        single_files, multiple_files = self._extract_files_from_request(request, model_name)
        
        data.update(single_files)
        
        for field_name in multiple_files.keys():
            data.pop(field_name, None)
        
        return data, multiple_files
    
    def handle_file_relations(self, instance, file_fields_map: Dict[str, List], model) -> None:
        """Handle file relations for an instance."""
        for field_name, files in file_fields_map.items():
            relation_info = self._get_relation_info(model, field_name)
            if not relation_info:
                continue
            
            target_model = relation_info['target_model']
            relation_type = relation_info['relation_type']
            
            single_file_fields, _ = self.detector.detect_file_fields(target_model)
            if not single_file_fields:
                continue
            
            file_field = single_file_fields[0]
            
            if relation_type == 'many_to_many':
                self._handle_many_to_many_files(instance, field_name, files, target_model, file_field)
            elif relation_type == 'many_to_one_rel':
                self._handle_many_to_one_files(instance, files, target_model, file_field, relation_info['fk_name'])
            elif relation_type == 'one_to_one':
                self._handle_one_to_one_files(instance, field_name, files, target_model, file_field)
            elif relation_type == 'one_to_one_rel':
                self._handle_one_to_one_rel_files(instance, files, target_model, file_field, relation_info['fk_name'])
    
    def _handle_many_to_many_files(self, instance, field_name: str, files: List, target_model, file_field: str):
        """Handle many-to-many file relations."""
        manager = getattr(instance, field_name)
        manager.clear()
        
        created_objs = []
        for f in files:
            obj = target_model.objects.create(**{file_field: f})
            created_objs.append(obj)
        
        manager.add(*created_objs)
    
    def _handle_many_to_one_files(self, instance, files: List, target_model, file_field: str, fk_name: str):
        """Handle many-to-one file relations."""
        for f in files:
            target_model.objects.create(**{file_field: f, fk_name: instance})
    
    def _handle_one_to_one_files(self, instance, field_name: str, files: List, target_model, file_field: str):
        """Handle one-to-one file relations."""
        if files:
            related_obj = target_model.objects.create(**{file_field: files[0]})
            setattr(instance, field_name, related_obj)
            instance.save()
    
    def _handle_one_to_one_rel_files(self, instance, files: List, target_model, file_field: str, fk_name: str):
        """Handle one-to-one reverse file relations."""
        if files:
            target_model.objects.create(**{file_field: files[0], fk_name: instance})


class AsyncFileHandler(BaseFileHandler):
    """Handles file upload processing for async routes."""
    
    async def process_create_files(self, request, payload, model) -> Tuple[Dict[str, Any], Dict[str, List]]:
        """Process files for create operation asynchronously."""
        data = payload.model_dump()
        model_name = model.__name__
        
        single_files, multiple_files = self._extract_files_from_request(request, model_name)
        
        data.update(single_files)
        
        for field_name in multiple_files.keys():
            data.pop(field_name, None)
        
        return data, multiple_files
    
    async def process_update_files(self, request, payload, model) -> Tuple[Dict[str, Any], Dict[str, List]]:
        """Process files for update operation asynchronously."""
        data = payload.model_dump(exclude_unset=True)
        model_name = model.__name__
        
        single_files, multiple_files = self._extract_files_from_request(request, model_name)
        
        data.update(single_files)
        
        for field_name in multiple_files.keys():
            data.pop(field_name, None)
        
        return data, multiple_files
    
    async def handle_file_relations(self, instance, file_fields_map: Dict[str, List], model) -> None:
        """Handle file relations for an instance asynchronously."""
        get_fields = sync_to_async(lambda m: m._meta.get_fields())
        model_fields = await get_fields(model)
        
        for field_name, files in file_fields_map.items():
            relation = next((f for f in model_fields if f.name == field_name), None)
            if not relation:
                continue
            
            relation_info = await sync_to_async(self._get_relation_info)(model, field_name)
            if not relation_info:
                continue
            
            target_model = relation_info['target_model']
            relation_type = relation_info['relation_type']
            
            detect_files = sync_to_async(self.detector.detect_file_fields)
            single_file_fields, _ = await detect_files(target_model)
            if not single_file_fields:
                continue
            
            file_field = single_file_fields[0]
            
            if relation_type == 'many_to_many':
                await self._handle_many_to_many_files_async(instance, field_name, files, target_model, file_field)
            elif relation_type == 'many_to_one_rel':
                await self._handle_many_to_one_files_async(instance, files, target_model, file_field, relation_info['fk_name'])
            elif relation_type == 'one_to_one':
                await self._handle_one_to_one_files_async(instance, field_name, files, target_model, file_field)
            elif relation_type == 'one_to_one_rel':
                await self._handle_one_to_one_rel_files_async(instance, files, target_model, file_field, relation_info['fk_name'])
    
    async def _handle_many_to_many_files_async(self, instance, field_name: str, files: List, target_model, file_field: str):
        """Handle many-to-many file relations asynchronously."""
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
    
    async def _handle_many_to_one_files_async(self, instance, files: List, target_model, file_field: str, fk_name: str):
        """Handle many-to-one file relations asynchronously."""
        for f in files:
            create_related = sync_to_async(lambda model, **kwargs: model.objects.create(**kwargs))
            await create_related(target_model, **{file_field: f, fk_name: instance})
    
    async def _handle_one_to_one_files_async(self, instance, field_name: str, files: List, target_model, file_field: str):
        """Handle one-to-one file relations asynchronously."""
        if files:
            create_related = sync_to_async(lambda model, **kwargs: model.objects.create(**kwargs))
            related_obj = await create_related(target_model, **{file_field: files[0]})
            
            setattr(instance, field_name, related_obj)
            save_instance = sync_to_async(lambda obj: obj.save())
            await save_instance(instance)
    
    async def _handle_one_to_one_rel_files_async(self, instance, files: List, target_model, file_field: str, fk_name: str):
        """Handle one-to-one reverse file relations asynchronously."""
        if files:
            create_related = sync_to_async(lambda model, **kwargs: model.objects.create(**kwargs))
            await create_related(target_model, **{file_field: files[0], fk_name: instance})