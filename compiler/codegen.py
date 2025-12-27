import llvmlite.ir as ir
import llvmlite.binding as llvm
from antlr4 import ParseTreeVisitor
from .types import LLVMTypes
from .runtime_link import RuntimeLinker

class RelTableCompiler(ParseTreeVisitor):
    def __init__(self, semantic_info):
        self.module = ir.Module(name="reltable_module")
        self.module.triple = llvm.get_default_triple()
        
        self.t = LLVMTypes()
        self.rt = RuntimeLinker(self.module, self.t)
        self.rt.declare()

        self.semantic_info = semantic_info  
        self.builder = None
        self.func = None
         
        self.scopes = [{}]
        self.strings = {}

        self.loop_stack = []  
        self.func_exit_block = None  
        self.func_return_ptr = None  
        self.lambda_count = 0

    def _get_str_const(self, string):
        """Кеширование глобальных строк с правильным подсчетом байтов (UTF-8)"""
        if string in self.strings:
            return self.strings[string]
        
        enc_string = (string + '\0').encode('utf-8')
        byte_len = len(enc_string)  
        
        val = ir.Constant(ir.ArrayType(ir.IntType(8), byte_len), 
                          bytearray(enc_string))
        
         
        global_var = ir.GlobalVariable(self.module, val.type, name=f".str{len(self.strings)}")
        global_var.linkage = 'internal'
        global_var.global_constant = True  
        global_var.initializer = val
         
        ptr = global_var.gep([ir.IntType(32)(0), ir.IntType(32)(0)])
        self.strings[string] = ptr
        return ptr
     

    def visitProgram(self, ctx):
        fnty = ir.FunctionType(self.t.int, [])
        self.func = ir.Function(self.module, fnty, name="main")
        block = self.func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)
         
        self.visitChildren(ctx)
         
        if not self.builder.block.is_terminated:
            self.builder.ret(ir.Constant(self.t.int, 0))
        return self.module

    def visitAssignStmt(self, ctx):
        name = ctx.Identifier().getText()
        val, typ = self.visit(ctx.expr())
         
        if name not in self.scopes[-1]:
            with self.builder.goto_entry_block():
                ptr = self.builder.alloca(typ, name=name)
            self.scopes[-1][name] = (ptr, typ)
        
        ptr, _ = self.scopes[-1][name]
        self.builder.store(val, ptr)
        return None

    def visitLiteral(self, ctx):
        if ctx.IntegerLiteral():
            return ir.Constant(self.t.int, int(ctx.IntegerLiteral().getText())), self.t.int
        if ctx.StringLiteral():
            s = ctx.StringLiteral().getText()[1:-1]  
            return self._get_str_const(s), self.t.char_ptr
        if ctx.BooleanLiteral():
            b = 1 if ctx.BooleanLiteral().getText() == 'true' else 0
            return ir.Constant(self.t.bool, b), self.t.bool
        return None
    
    def visitFuncDecl(self, ctx):
        name = ctx.Identifier().getText()
         
        param_names = []
        if ctx.paramList():
             
            for p in ctx.paramList().param():
                param_names.append(p.Identifier().getText())
         
        closure, _ = self._generate_lambda(param_names, ctx.block(), name)
         
        with self.builder.goto_entry_block():
            ptr = self.builder.alloca(self.t.closure, name=name)
        self.builder.store(closure, ptr)
        self.set_var(name, ptr, self.t.closure)

        return None

    def visitLambdaExpr(self, ctx):
        param_names = []
        if ctx.lambdaParamList():
            for p in ctx.lambdaParamList().lambdaParam():
                param_names.append(p.Identifier().getText())
        elif ctx.lambdaName():
            param_names.append(ctx.lambdaName().getText())
 
        closure, _ = self._generate_lambda(param_names, ctx.expr() if ctx.expr() else ctx.block(), f"lambda_{self.lambda_count}")
        self.lambda_count += 1
        return closure, self.t.closure

    def _generate_lambda(self, param_names, body_ctx, name): 
        parent_lambda_ctx = body_ctx.parentCtx
        captured_dict = getattr(parent_lambda_ctx, '_captured_vars', {})
        
        captured_list = []
        for v_name in captured_dict:
            ptr, ty = self.get_var(v_name)
            captured_list.append((v_name, ptr, ty))
 
        env_types = [v[2] for v in captured_list]  
        env_struct_ty = ir.LiteralStructType(env_types)
         
        null_ptr = ir.Constant(env_struct_ty.as_pointer(), None)
        size_gep = self.builder.gep(null_ptr, [ir.Constant(ir.IntType(32), 1)])
        env_size = self.builder.ptrtoint(size_gep, ir.IntType(64))
        env_ptr_raw = self.builder.call(self.rt.malloc, [env_size])
        env_ptr_typed = self.builder.bitcast(env_ptr_raw, env_struct_ty.as_pointer())

        for i, (v_name, v_ptr, v_ty) in enumerate(captured_list):
            curr_val = self.builder.load(v_ptr)
            field_ptr = self.builder.gep(env_ptr_typed, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), i)])
            self.builder.store(curr_val, field_ptr)

        old_builder = self.builder
         
        arg_types = [self.t.char_ptr] if (len(param_names) == 1 and name.startswith("lambda")) else [self.t.int] * len(param_names)
        fnty = self.t.get_function_type(self.t.int, arg_types)
        l_func = ir.Function(self.module, fnty, name=name)
        
        entry = l_func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(entry)
        self.enter_scope()

        if captured_list:
            lambda_env_ptr = self.builder.bitcast(l_func.args[0], env_struct_ty.as_pointer())
            for i, (v_name, _, v_ty) in enumerate(captured_list):
                 
                val_ptr = self.builder.gep(lambda_env_ptr, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), i)])
                 
                local_ptr = self.builder.alloca(v_ty, name=f"captured_{v_name}")
                self.builder.store(self.builder.load(val_ptr), local_ptr)
                self.set_var(v_name, local_ptr, v_ty)

        for i, p_name in enumerate(param_names):
            p_val = l_func.args[i+1]
            p_ptr = self.builder.alloca(arg_types[i], name=p_name)
            self.builder.store(p_val, p_ptr)
            self.set_var(p_name, p_ptr, arg_types[i])

        from gen.RelTableParser import RelTableParser
        if isinstance(body_ctx, RelTableParser.BlockContext):
            self.visit(body_ctx)
            if not self.builder.block.is_terminated: self.builder.ret(ir.Constant(self.t.int, 0))
        else:
            res = self.visit(body_ctx)
            val = self.builder.zext(res[0], self.t.int) if res[1] == self.t.bool else res[0]
            self.builder.ret(val)

        self.exit_scope()
        self.builder = old_builder

        closure = ir.Constant(self.t.closure, ir.Undefined)
        closure = self.builder.insert_value(closure, self.builder.bitcast(l_func, self.t.char_ptr), 0)
        closure = self.builder.insert_value(closure, env_ptr_raw, 1)
        return closure, self.t.closure
    

    def visitPrimaryCall(self, ctx):
        closure_obj, _ = self.visit(ctx.primaryExpr())
         
        func_ptr_raw = self.builder.extract_value(closure_obj, 0)
        env_ptr = self.builder.extract_value(closure_obj, 1)
        
        args = []
        if ctx.argList():
            for expr in ctx.argList().expr():
                val, _ = self.visit(expr)
                args.append(val)
        
        fnty = self.t.get_function_type(self.t.int, [self.t.int] * len(args))
        func_ptr = self.builder.bitcast(func_ptr_raw, fnty.as_pointer())
        
        result = self.builder.call(func_ptr, [env_ptr] + args)
        return result, self.t.int
    
    def visitIfStmt(self, ctx):
        conditions = ctx.expr()  
        end_block = self.func.append_basic_block(name="if.end")

        for i in range(len(conditions)):
            cond_val, _ = self.visit(conditions[i])
            
            then_block = self.func.append_basic_block(name=f"if.then.{i}")
            next_cond_block = self.func.append_basic_block(name=f"if.next.{i}")
             
            self.builder.cbranch(cond_val, then_block, next_cond_block)
            self.builder.position_at_end(then_block)
            self.enter_scope()
             
            body = ctx.children[i*2 + 2] 
            self.visit(body)
            self.exit_scope()
            
            if not self.builder.block.is_terminated:
                self.builder.branch(end_block)
                
            self.builder.position_at_end(next_cond_block)

        if ctx.ELSE():
            self.enter_scope()
            self.visit(ctx.children[-1])  
            self.exit_scope()

        if not self.builder.block.is_terminated:
            self.builder.branch(end_block)
            
        self.builder.position_at_end(end_block)

     
    def visitForStmt(self, ctx):
        iter_name = ctx.Identifier().getText()
        start_val, _ = self.visit(ctx.expr(0))
        end_val, _ = self.visit(ctx.expr(1))
         
        with self.builder.goto_entry_block():
            iter_ptr = self.builder.alloca(self.t.int, name=iter_name)
        self.builder.store(start_val, iter_ptr)
        
        cond_block = self.func.append_basic_block(name="for.cond")
        body_block = self.func.append_basic_block(name="for.body")
        after_block = self.func.append_basic_block(name="for.end")
        
        self.builder.branch(cond_block)
        
        self.builder.position_at_end(cond_block)
        curr_val = self.builder.load(iter_ptr)
        cmp = self.builder.icmp_signed("<=", curr_val, end_val)
        self.builder.cbranch(cmp, body_block, after_block)
        
        self.builder.position_at_end(body_block)
        self.loop_stack.append(after_block)  
        
        self.enter_scope()
        self.scopes[-1][iter_name] = (iter_ptr, self.t.int)
        self.visit(ctx.children[-1])
        self.exit_scope()
        
        self.loop_stack.pop()
        
        if not self.builder.block.is_terminated:
            new_val = self.builder.add(self.builder.load(iter_ptr), ir.Constant(self.t.int, 1))
            self.builder.store(new_val, iter_ptr)
            self.builder.branch(cond_block)
            
        self.builder.position_at_end(after_block)

     
    def visitSwitchStmt(self, ctx):
        switch_val, _ = self.visit(ctx.expr()) if ctx.expr() else (None, None)
        end_block = self.func.append_basic_block(name="switch.end")
        
        for case in ctx.switchCase():
            case_cond_block = self.func.append_basic_block(name="case.check")
            case_body_block = self.func.append_basic_block(name="case.body")
            next_case_block = self.func.append_basic_block(name="case.next")
            
            self.builder.branch(case_cond_block)
            self.builder.position_at_end(case_cond_block)
            
            combined_match = ir.Constant(self.t.bool, 0)
            for case_expr in case.caseExprList().caseExpr():
                v_start, _ = self.visit(case_expr.expr(0))
                
                if case_expr.TO():  
                    v_end, _ = self.visit(case_expr.expr(1))
                    is_ge = self.builder.icmp_signed(">=", switch_val, v_start)
                    is_le = self.builder.icmp_signed("<=", switch_val, v_end)
                    match = self.builder.and_(is_ge, is_le)
                else:  
                    match = self.builder.icmp_signed("==", switch_val, v_start)
                
                combined_match = self.builder.or_(combined_match, match)

            self.builder.cbranch(combined_match, case_body_block, next_case_block)
            
            self.builder.position_at_end(case_body_block)
            for stmt in case.statement():
                self.visit(stmt)
            if not self.builder.block.is_terminated:
                self.builder.branch(end_block)
            
            self.builder.position_at_end(next_case_block)

        if ctx.defaultCase():
            for stmt in ctx.defaultCase().statement():
                self.visit(stmt)
        
        if not self.builder.block.is_terminated:
            self.builder.branch(end_block)
        self.builder.position_at_end(end_block)

     
    def visitReturnStmt(self, ctx):
        if ctx.expr():
            val, typ = self.visit(ctx.expr())
            if typ == self.t.bool:
                val = self.builder.zext(val, self.t.int) 
            self.builder.ret(val)
        else:
            self.builder.ret(ir.Constant(self.t.int, 0))

    def visitBreakStmt(self, ctx):
        if self.loop_stack:
            target = self.loop_stack[-1]
            self.builder.branch(target)
        else:
            raise Exception("Break outside of loop")
        
    def visitSelectExpr(self, ctx):
        table_val, _ = self.visit(ctx.expr(0))
        
        if ctx.whereClause():
            res = self.visit(ctx.whereClause())
            if res is None:
                raise Exception("Codegen Error: WHERE clause returned None. Check visitPrimary or visitLambda.")
            closure, _ = res
        else:
            closure = ir.Constant(self.t.closure, ir.Undefined)
           
        result_table = self.builder.call(self.rt.rt_table_select, [table_val, closure])
        return result_table, self.t.table
    
     
    def visitPrimaryBase(self, ctx):
        child = ctx.baseExpr()
        
        if child.Identifier():
            name = child.Identifier().getText()
            ptr, typ = self.get_var(name)
            return self.builder.load(ptr, name=f"load_{name}"), typ
        
        if child.expr():
            return self.visit(child.expr())  
        
        return self.visit(child)

     
    def visitPrimaryCall(self, ctx):
        closure_obj, _ = self.visit(ctx.primaryExpr())
        
        f_ptr_raw = self.builder.extract_value(closure_obj, 0)
        e_ptr = self.builder.extract_value(closure_obj, 1)
        
        args = []
        if ctx.argList():
            for expr in ctx.argList().expr():
                val, _ = self.visit(expr)
                args.append(val)
        
        fnty = self.t.get_function_type(self.t.int, [self.t.int] * len(args))
        f_ptr = self.builder.bitcast(f_ptr_raw, fnty.as_pointer())
        
        res = self.builder.call(f_ptr, [e_ptr] + args)
        return res, self.t.int

    def visitPrimaryMember(self, ctx):
        row_val, _ = self.visit(ctx.primaryExpr())
        
        field_name = ctx.Identifier().getText()
        field_name_ptr = self._get_str_const(field_name)
        
        res = self.builder.call(self.rt.rt_get_int, [row_val, field_name_ptr])
        return res, self.t.int

     
    def visitPrimaryIndex(self, ctx):
        return None, self.t.void
    
    def visitCreateTable(self, ctx):
        name_val, _ = self.visit(ctx.expr())
        table_ptr = self.builder.call(self.rt.rt_create_table, [name_val])
        if ctx.Identifier():
            var_name = ctx.Identifier().getText()
            with self.builder.goto_entry_block():
                 
                var_ptr = self.builder.alloca(self.t.table, name=var_name)
            self.builder.store(table_ptr, var_ptr)
            self.set_var(var_name, var_ptr, self.t.table)
        return table_ptr, self.t.table

    def visitAddColumn(self, ctx):
            tbl_ptr, _ = self.visit(ctx.expr(0))
            col_name, _ = self.visit(ctx.expr(1))
            
            type_str = ctx.type_().getText()
            type_ptr = self._get_str_const(type_str)
            
            self.builder.call(self.rt.rt_add_column, [tbl_ptr, col_name, type_ptr])
            return None

    def visitAddRow(self, ctx):
        tbl_ptr, _ = self.visit(ctx.expr(0))
        
        self.builder.call(self.rt.rt_add_row, [tbl_ptr])
        return None
    
    def enter_scope(self):
        self.scopes.append({})

    def exit_scope(self):
        self.scopes.pop()

    def set_var(self, name, ptr, typ):
        """Записывает переменную в текущий (самый верхний) скоуп"""
        self.scopes[-1][name] = (ptr, typ)

    def get_var(self, name):
        """Ищет переменную, начиная с текущего скоупа вверх до глобального"""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise Exception(f"Codegen Error: Variable '{name}' not defined")
    
    def _find_captured_vars(self, ctx):
      return []  
    
    def visitPrimary(self, ctx):
        return self.visit(ctx.primaryExpr())
    
     
    def visitCompareOp(self, ctx):
        left, _ = self.visit(ctx.expr(0))
        right, _ = self.visit(ctx.expr(1))
        
        op = ctx.getChild(1).getText()
         
        op_map = {
            "==": "==", "!=": "!=", 
            ">": ">", "<": "<", 
            ">=": ">=", "<=": "<="
        }
        
        if op in op_map:
            res = self.builder.icmp_signed(op_map[op], left, right)
            return res, self.t.bool
        return ir.Constant(self.t.bool, 0), self.t.bool
    
    def visitLogicalOp(self, ctx):
        left, _ = self.visit(ctx.expr(0))
        right, _ = self.visit(ctx.expr(1))
        
        if ctx.AND():
            return self.builder.and_(left, right), self.t.bool
        if ctx.OR():
            return self.builder.or_(left, right), self.t.bool
        return ir.Constant(self.t.bool, 0), self.t.bool

     
    def visitNotOp(self, ctx):
        val, _ = self.visit(ctx.expr())
        return self.builder.not_(val), self.t.bool
    
    def visitWhereClause(self, ctx):
       return self.visit(ctx.expr())

    def visitOrderClause(self, ctx):
       return None