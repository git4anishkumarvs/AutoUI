from abc import ABC, abstractmethod
from PIL import Image

class BaseVisionWrapper(ABC):
    @abstractmethod
    def load_model(self) -> None:
        """ Initialized any required memory pipelines dynamically upon cold boot """
        pass
        
    @abstractmethod
    def find_control(self, query: str, action_type: str, image: Image.Image) -> dict:
        """ 
        Strict output structure mapping:
        Returns {"status": "success", "coordinates": {"x": int, "y": int}, "raw_response": str, "parsed_action": str} 
        """
        pass

    def list_controls(self, image: Image.Image, include_grounded_image: bool = False) -> dict:
        raise NotImplementedError(f"{self.__class__.__name__} does not support control listing")
