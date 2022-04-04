class Singleton(type):
    def __new__(cls, name, bases, cls_dict):
        klazz = super().__new__(cls, name, bases, cls_dict)

        def clean():
            if hasattr(klazz, "instance"):
                delattr(klazz, "instance")

        setattr(klazz, "clean", clean)
        return klazz

    def __call__(cls, *args, **kwargs):
        if not hasattr(cls, "instance"):
            cls.instance = super(Singleton, cls).__call__(*args, **kwargs)
        return cls.instance


class SingletonNotInstantiatedException(Exception):
    """Raised when a singelton is accessed without being initialized"""
