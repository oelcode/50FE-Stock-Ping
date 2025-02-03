from abc import ABC, abstractmethod
import asyncio
import importlib
import inspect
import os
from datetime import datetime
from typing import Dict, List, Type

def get_timestamp() -> str:
    """Return current timestamp in a readable format"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class NotificationHandler(ABC):
    """Abstract base class for notification handlers"""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the notification handler"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Cleanup and shutdown the notification handler"""
        pass
    
    @abstractmethod
    async def send_stock_alert(self, sku: str, price: str, url: str, in_stock: bool) -> None:
        """Send a stock status notification"""
        pass
    
    @abstractmethod
    async def send_status_update(self, message: str) -> None:
        """Send a status update message"""
        pass
    
    @abstractmethod
    async def send_startup_message(self, message: str) -> None:
        """Send a startup notification"""
        pass

class NotificationManager:
    """Manages multiple notification handlers"""
    
    def __init__(self):
        self.handlers: List[NotificationHandler] = []
        self.loop = asyncio.get_event_loop()
    
    def register_handler(self, handler: NotificationHandler) -> None:
        """Register a new notification handler"""
        self.handlers.append(handler)
    
    async def initialize_handlers(self) -> None:
        """Initialize all registered handlers"""
        initialized_handlers = []
        for handler in self.handlers:
            try:
                if await handler.initialize():
                    initialized_handlers.append(handler)
            except Exception as e:
                print(f"[{get_timestamp()}] ❌ Failed to initialize {handler.__class__.__name__}: {str(e)}")
        self.handlers = initialized_handlers
    
    async def shutdown_handlers(self) -> None:
        """Shutdown all handlers"""
        for handler in self.handlers:
            try:
                await handler.shutdown()
            except Exception as e:
                print(f"[{get_timestamp()}] ❌ Error shutting down {handler.__class__.__name__}: {str(e)}")
    
    async def send_stock_alert(self, sku: str, price: str, url: str, in_stock: bool) -> None:
        """Send stock alert to all handlers"""
        for handler in self.handlers:
            try:
                await handler.send_stock_alert(sku, price, url, in_stock)
            except Exception as e:
                print(f"[{get_timestamp()}] ❌ Error in {handler.__class__.__name__}: {str(e)}")
    
    async def send_status_update(self, message: str) -> None:
        """Send status update to all handlers"""
        for handler in self.handlers:
            try:
                await handler.send_status_update(message)
            except Exception as e:
                print(f"[{get_timestamp()}] ❌ Error in {handler.__class__.__name__}: {str(e)}")
    
    async def send_startup_message(self, message: str) -> None:
        """Send startup message to all handlers"""
        for handler in self.handlers:
            try:
                await handler.send_startup_message(message)
            except Exception as e:
                print(f"[{get_timestamp()}] ❌ Error in {handler.__class__.__name__}: {str(e)}")

    @classmethod
    def load_handlers(cls) -> 'NotificationManager':
        """
        Dynamically load all notification handlers from the current directory.
        Returns a configured NotificationManager instance.
        """
        manager = cls()
        
        # Get the path to this directory
        handlers_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Import all .py files from the handlers directory
        for filename in os.listdir(handlers_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                module_name = filename[:-3]  # Remove .py extension
                try:
                    # Import the module
                    module = importlib.import_module(f"handlers.{module_name}")
                    
                    # Find all classes in the module that inherit from NotificationHandler
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, NotificationHandler) and 
                            obj != NotificationHandler):
                            
                            # Create instance and register it
                            handler = obj()
                            manager.register_handler(handler)
                            print(f"[{get_timestamp()}] ✅ Loaded notification handler: {name}")
                            
                except Exception as e:
                    print(f"[{get_timestamp()}] ❌ Failed to load handler {module_name}: {str(e)}")
        
        return manager
