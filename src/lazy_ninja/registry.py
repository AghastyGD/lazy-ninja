from typing import Type, Dict, Optional
from .base import BaseModelController

class ModelRegistry:
    """
    Registry class to manage custom controllers for Django models.

    Controllers can override the default behavior by providing custom hook implementations.
    """
    _controllers: Dict[str, Type[BaseModelController]] = {}
    
    @classmethod
    def register_controller(cls, model_name: str, controller: Type[BaseModelController]):
        """
        Register a controller for a specific model.

        Parameters:
          - model_name: The name of the Django model.
          - controller: A subclass of BaseModelController with custom hook implementations.
        """
        cls._controllers[model_name] = controller
        
    @classmethod
    def get_controller(cls, model_name: str) -> Optional[Type[BaseModelController]]:
        """
        Retrieve the registered controller for a given model.

        Parameters:
          - model_name: The name of the Django model.
        
        Returns:
          - The registered controller if found, otherwise None.
        """
        return cls._controllers.get(model_name)
