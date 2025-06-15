from typing import Any, Callable, Optional
from asgiref.sync import sync_to_async


class BaseHookExecutor:
    """Base class for hook execution."""

    def _is_valid_hook(self, hook: Optional[Callable]) -> bool:
        """Check if hook is valid and not a default hook."""
        return hook is not None and not getattr(hook, "__is_default_hook__", False)
    

class SyncHookExecutor(BaseHookExecutor):
    """Handles hook execution for sync routes."""

    def execute(self, hook: Optional[Callable], *args, **kwargs) -> Any:
        """
        Safely execute a hook function if it exists and is not a default hook.

        Args:
            hook: The hook function to execute
            *args: Positional arguments to pass to the hook
            **kwargs: Keyword arguments to pass to the hook

        Returns:
            The result of the hook execution or None
        """
        if self._is_valid_hook(hook):
            return hook(*args, **kwargs)
        return None
    

class AsyncHookExecutor(BaseHookExecutor):
    """Handles hook execution for async routes."""

    async def execute(self, hook: Optional[Callable], *args, **kwargs) -> Any:
        """
        Safely execute a hook function asynchronously.
        
        Args:
            hook: The hook function to execute
            *args: Positional arguments to pass to the hook
            **kwargs: Keyword arguments to pass to the hook
            
        Returns:
            The result of the hook execution or None
        """
        if self._is_valid_hook(hook):
            return await sync_to_async(hook)(*args, **kwargs)
        return None
    

# Legacy function wrappers for backward compatibility
def execute_hook(hook: Optional[Callable], *args, **kwargs) -> Any:
    """Legacy wrapper for SyncHookExecutor.execute"""
    executor = SyncHookExecutor()
    return executor.execute(hook, *args, **kwargs)


async def execute_hook_async(hook: Optional[Callable], *args, **kwargs) -> Any:
    """Legacy wrapper for AsyncHookExecutor.execute"""
    executor = AsyncHookExecutor()
    return await executor.execute(hook, *args, **kwargs)


def get_hook(controller: Optional[object], hook_name: str, passed_hook: Optional[Callable] = None) -> Optional[Callable]:
    if controller:
        controller_hook = getattr(controller, hook_name, None)
        if controller_hook and not getattr(controller_hook, "__is_default_hook__", False):
                return controller_hook
    return passed_hook