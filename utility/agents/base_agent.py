import logging
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseAgent(ABC):
    """Base class for all agents in the system"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's main logic"""
        pass
    
    def log_info(self, message: str):
        """Log an info message"""
        self.logger.info(message)
    
    def log_warning(self, message: str):
        """Log a warning message"""
        self.logger.warning(message)
    
    def log_error(self, message: str):
        """Log an error message"""
        self.logger.error(message)

