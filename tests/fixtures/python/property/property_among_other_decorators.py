class MyClass:
    @staticmethod
    def static_method():
        pass

    @classmethod
    def class_method(cls):
        pass

    @custom_decorator
    @property
    def my_value(self):
        return self._value