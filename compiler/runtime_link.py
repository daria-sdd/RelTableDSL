import llvmlite.ir as ir

class RuntimeLinker:
    def __init__(self, module, types):
        self.module = module
        self.t = types

    def declare(self):
        self.rt_create_table = ir.Function(self.module, ir.FunctionType(self.t.table, [self.t.char_ptr]), name="rt_create_table")
        self.rt_add_column = ir.Function(self.module, ir.FunctionType(self.t.void, [self.t.table, self.t.char_ptr, self.t.char_ptr]), name="rt_add_column")
        self.rt_add_row = ir.Function(self.module, ir.FunctionType(self.t.void, [self.t.table]), name="rt_add_row")
        
        self.rt_write_int = ir.Function(self.module, ir.FunctionType(self.t.void, [self.t.int]), name="rt_write_int")
        self.rt_write_str = ir.Function(self.module, ir.FunctionType(self.t.void, [self.t.char_ptr]), name="rt_write_string")
        self.rt_write_bool = ir.Function(self.module, ir.FunctionType(self.t.void, [self.t.bool]), name="rt_write_bool")

        malloc_ty = ir.FunctionType(self.t.char_ptr, [ir.IntType(64)])
        self.malloc = ir.Function(self.module, malloc_ty, name="malloc")
         
        self.rt_get_int = ir.Function(self.module, 
            ir.FunctionType(self.t.int, [self.t.row, self.t.char_ptr]), name="rt_get_int")
        
        self.rt_get_string = ir.Function(self.module, 
            ir.FunctionType(self.t.char_ptr, [self.t.row, self.t.char_ptr]), name="rt_get_string")
         
        self.rt_table_select = ir.Function(self.module,
            ir.FunctionType(self.t.table, [self.t.table, self.t.closure]), name="rt_table_select")

    def declare_relational(self):
        self.rt_get_int = ir.Function(self.module, 
            ir.FunctionType(self.t.int, [self.t.row, self.t.char_ptr]), name="rt_get_int")
        self.rt_get_str = ir.Function(self.module, 
            ir.FunctionType(self.t.char_ptr, [self.t.row, self.t.char_ptr]), name="rt_get_string")
        self.rt_table_select = ir.Function(self.module,
            ir.FunctionType(self.t.table, [self.t.table, self.t.closure]), name="rt_table_select")