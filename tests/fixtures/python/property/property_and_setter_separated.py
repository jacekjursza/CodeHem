class MyClass:
    @property
    def my_value(self):
        return self._value

    def other_method(self):
        pass

    @my_value.setter
    def my_value(self, value):
        self._value = value