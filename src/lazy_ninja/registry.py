import importlib
from pathlib import Path
from typing import Type, Dict, Any, Optional

from django.apps import apps

class ModelRegistry:
    """Registry for model controllers."""
    
    _controllers: Dict[str, Any] = {}
    _discovered = False
    
    @classmethod
    def register_controller(cls, model_name: str, controller: Any) -> None:
        """Register a controller for a model."""
        cls._controllers[model_name.lower()] = controller
        
    @classmethod
    def get_controller(cls, model_name: str) -> Optional[Any]:
        """Get the controller for a model."""
        if not cls._discovered:
            cls.discover_controllers()

        return cls._controllers.get(model_name.lower())
    
    @classmethod
    def discover_controllers(cls) -> None:
        """
        Automatically discover and register controller in all Django apps.
        Looks for controllers in:
        - controllers/*.py
        - controllers.py
        """
        if cls._discovered:
            return

        for app_config in apps.get_app_configs():
            # Skip Django's built-in apps
            if app_config.name.startswith('django.'):
                continue

            app_path = Path(app_config.path)

            # Try controllers/*.py
            controllers_dir = app_path / 'controllers'
            if controllers_dir.is_dir():
                for file in controllers_dir.glob('*.py'):
                    if file.name != '__init__.py':
                        module_path = f"{app_config.name}.controllers.{file.stem}"
                        try:
                            importlib.import_module(module_path)
                        except ImportError as e:
                            continue

        cls._discovered = True
def controller_for(model_name: str):
    """
    Decorator to automatically register a controller for a model.
    
    Usage:
        @controller_for('Post')
        class PostController(BaseModelController):
            ...
    """
    def decorator(controller_class: Type):
        ModelRegistry.register_controller(model_name, controller_class)
        return controller_class
    return decorator

