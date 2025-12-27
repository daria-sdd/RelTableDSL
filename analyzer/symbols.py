from enum import Enum, auto

class Type(Enum):
    INT = auto()
    DECIMAL = auto()
    STRING = auto()
    BOOL = auto()
    TABLE = auto()
    ROW = auto()
    FUNCTION = auto()
    VOID = auto()
    ANY = auto()

class Symbol:
    def __init__(self, name, type_obj, node=None):
        self.name = name
        self.type = type_obj
        self.node = node

class Scope:
    def __init__(self, parent=None, name="global", is_func_boundary=False):  
        self.parent = parent
        self.name = name
        self.is_func_boundary = is_func_boundary
        self.symbols = {}
        self.captured_symbols = {}

    def define(self, name, symbol):
        self.symbols[name] = symbol

    def resolve(self, name):
        if name in self.symbols:
            return self.symbols[name], False  
         
        if self.parent:
            symbol, is_captured = self.parent.resolve(name)
            if symbol:
                 
                if self.is_func_boundary or is_captured:
                    self.captured_symbols[name] = symbol
                    return symbol, True
                return symbol, False
        return None, False