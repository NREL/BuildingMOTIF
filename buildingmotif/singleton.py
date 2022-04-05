class Singleton(type):
    """Metaclass that makes a class into a singleton"""

    def __new__(cls, name, bases, cls_dict):
        singleton_cls = super().__new__(cls, name, bases, cls_dict)

        def clean():
            if hasattr(singleton_cls, "instance"):
                delattr(singleton_cls, "instance")

        setattr(singleton_cls, "clean", clean)
        return singleton_cls

    def __call__(cls, *args, **kwargs):
        if not hasattr(cls, "instance"):
            cls.instance = super(Singleton, cls).__call__(*args, **kwargs)
        return cls.instance


class SingletonNotInstantiatedException(Exception):
    """Raised when a singelton is accessed without being initialized"""
