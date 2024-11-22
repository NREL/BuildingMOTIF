from typing import Optional


class LibraryNotFound(Exception):
    def __init__(self, name: Optional[str] = None, idnum: Optional[int] = None):
        self.lib_name = name
        self.lib_id = idnum

    def __str__(self):
        if self.lib_name:
            return f"Library with name '{self.lib_name}' not found"
        return f"Library with id '{self.lib_id}' not found"

class TemplateNotFound(Exception):
    def __init__(self, name: Optional[str] = None, idnum: Optional[int] = None):
        self.template_name = name
        self.template_id = idnum

    def __str__(self):
        if self.template_name:
            return f"Template with name '{self.template_name}' not found"
        return f"Template with id '{self.template_id}' not found"
