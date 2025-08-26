# defines abstract base class (blueprint) for agents in the grocery bot application

from abc import ABC, abstractmethod
from typing import Dict, Any
from models import WeeklyPlan

class Agent(ABC):
    # any subclass must implement this method, takes a context dictionary and returns an updated context
    @abstractmethod 
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        pass