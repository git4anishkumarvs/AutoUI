from abc import ABC, abstractmethod

class BaseAutomationWrapper(ABC):
    """
    Abstract base class for UI Automation wrappers. 
    Defines the universal contract for clicking, typing, scrolling, etc.
    This guarantees that the BDD step definitions and AppManager can easily
    swap underlying automation tools (PyGUITest, Playwright, Selenium) 
    without changing test logic.
    """
    
    @abstractmethod
    def launch(self, app_path: str):
        pass
        
    @abstractmethod
    def terminate(self):
        pass

    @abstractmethod
    def click(self, locator: str, locator_type: str = "default"):
        pass

    @abstractmethod
    def type_text(self, locator: str, text: str, locator_type: str = "default"):
        pass

    @abstractmethod
    def scroll(self, direction: str):
        pass
