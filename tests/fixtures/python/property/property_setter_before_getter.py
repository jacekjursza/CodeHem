class MyClass:
    @my_value.setter
    def my_value(self, value):
        self._value = value

    @property
    def my_value(self):
        return self._value