from typing import Optional

# The point of these exceptions is to provide more specific error messages which
# also embed the ID or name of the object that was not found. This is useful for
# debugging and logging purposes.


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


class ShapeCollectionNotFound(Exception):
    def __init__(self, name: Optional[str] = None, idnum: Optional[int] = None):
        self.shape_collection_name = name
        self.shape_collection_id = idnum

    def __str__(self):
        if self.shape_collection_name:
            return (
                f"Shape Collection with name '{self.shape_collection_name}' not found"
            )
        return f"Shape Collection with id '{self.shape_collection_id}' not found"


class ModelNotFound(Exception):
    def __init__(self, name: Optional[str] = None, idnum: Optional[int] = None):
        self.model_name = name
        self.model_id = idnum

    def __str__(self):
        if self.model_name:
            return f"Model with name '{self.model_name}' not found"
        return f"Model with id '{self.model_id}' not found"
