import llvmlite.ir as ir

class LLVMTypes:
    def __init__(self):
        self.int = ir.IntType(32)
        self.double = ir.DoubleType()
        self.bool = ir.IntType(1)
        self.void = ir.VoidType()
        self.char_ptr = ir.IntType(8).as_pointer()
        
        self.closure = ir.LiteralStructType([self.char_ptr, self.char_ptr])
        
        self.table = self.char_ptr
        self.row = self.char_ptr

    def get_llvm_type(self, semantic_type):
        """Конвертирует Type Enum из семантического анализатора в LLVM тип"""
        from analyzer.symbols import Type
        mapping = {
            Type.INT: self.int,
            Type.DECIMAL: self.double,
            Type.BOOL: self.bool,
            Type.STRING: self.char_ptr,
            Type.TABLE: self.table,
            Type.ROW: self.row,
            Type.VOID: self.void,
            Type.FUNCTION: self.closure  
        }
        return mapping.get(semantic_type, self.char_ptr)
    
    def get_function_type(self, return_type, arg_types):
        full_args = [self.char_ptr] + arg_types
        return ir.FunctionType(return_type, full_args)
