from antlr4 import ParseTreeVisitor
from .symbols import Scope, Symbol, Type
from .errors import SemanticError

class RelTableSemanticAnalyzer(ParseTreeVisitor):
    def __init__(self):
        super().__init__()
        self.global_scope = Scope(name="global")
        self.scope = self.global_scope
        self.errors = []
        self._register_builtins()

    def _register_builtins(self):
        builtins = [
            ("create_table", Type.FUNCTION),
            ("add_column", Type.FUNCTION),
            ("add_row", Type.FUNCTION),
            ("write", Type.FUNCTION),
            ("print", Type.FUNCTION)
        ]
        for name, t in builtins:
            self.global_scope.define(name, Symbol(name, t))

    def error(self, msg, ctx):
        line = ctx.start.line
        col = ctx.start.column
        self.errors.append(SemanticError(msg, line, col))

    def enter_scope(self, name, is_func=False):
        print(f"DEBUG: Entering scope '{name}' with is_func={is_func}") 
        self.scope = Scope(parent=self.scope, name=name, is_func_boundary=is_func)

    def exit_scope(self):
        if self.scope.parent:
            self.scope = self.scope.parent
        else:
            pass

    def _get_type_from_ctx(self, ctx):
        if not ctx: return Type.ANY
        t_text = ctx.getText().lower()
        mapping = {
            "int": Type.INT,
            "decimal": Type.DECIMAL,
            "string": Type.STRING,
            "bool": Type.BOOL,
            "table": Type.TABLE,
            "row": Type.ROW
        }
        return mapping.get(t_text, Type.ANY)


    def visitProgram(self, ctx):
        return self.visitChildren(ctx)

    def visitFuncDecl(self, ctx):
        name = ctx.Identifier().getText()
        self.scope.define(name, Symbol(name, Type.FUNCTION, ctx))

        self.enter_scope(f"func_{name}", is_func=True)

        if ctx.paramList():
            params = ctx.paramList().param() if hasattr(ctx.paramList(), 'param') else []
            for p in params:
                p_name = p.Identifier().getText()
                type_node = p.type_() if hasattr(p, 'type_') else (p.type() if hasattr(p, 'type') else None)
                p_type = self._get_type_from_ctx(type_node)
                
                self.scope.define(p_name, Symbol(p_name, p_type, p))
                print(f"DEBUG: Defined parameter '{p_name}' in scope {self.scope.name}")

        self.visit(ctx.block())
        
        self.exit_scope()
        return Type.FUNCTION

    def visitBlock(self, ctx):
        self.enter_scope("block")
        self.visitChildren(ctx)
        self.exit_scope()


    def visitIfStmt(self, ctx):
        self.visit(ctx.expr(0)) 
        return self.visitChildren(ctx)

    def visitForStmt(self, ctx):
        iter_name = ctx.Identifier().getText()
        self.visit(ctx.expr(0)) 
        self.visit(ctx.expr(1)) 

        self.enter_scope("for_loop")
        self.scope.define(iter_name, Symbol(iter_name, Type.INT, ctx))
        self.visit(ctx.children[-1])
        self.exit_scope()

    def visitSwitchStmt(self, ctx):
        if ctx.expr(): self.visit(ctx.expr())
        for case in ctx.switchCase():
            self.visit(case)
        if ctx.defaultCase():
            self.visit(ctx.defaultCase())

    def visitReturnStmt(self, ctx):
        curr = self.scope
        in_func = False
        while curr:
            if curr.is_func_boundary:
                in_func = True
                break
            curr = curr.parent
        if not in_func:
            self.error("'return' statement outside of function", ctx)
        
        if ctx.expr():
            return self.visit(ctx.expr())
        return Type.VOID

    

    def visitPrimaryBase(self, ctx):
        child = ctx.baseExpr()
        if not child: return Type.ANY
        if child.Identifier():
            name = child.Identifier().getText()
            symbol, is_captured = self.scope.resolve(name)
            if not symbol:
                self.error(f"Undefined variable '{name}'", ctx)
                return Type.ANY
            return symbol.type
        
        
        return self.visit(child)
    
    def visitPrimaryCall(self, ctx):
        """Вызов функции: f(x)"""
        self.visit(ctx.primaryExpr())
        if ctx.argList():
            self.visit(ctx.argList())
        return Type.ANY

    def visitPrimaryMember(self, ctx):
        """Доступ к полю: row.age"""
        self.visit(ctx.primaryExpr()) 
        
        return Type.ANY

    def visitPrimaryIndex(self, ctx):
        """Доступ по индексу: table[0]"""
        self.visit(ctx.primaryExpr())
        self.visit(ctx.expr())
        return Type.ANY

    def visitLambdaExpr(self, ctx):
        self.enter_scope("lambda", is_func=True)
     
        if ctx.lambdaParamList():
            l_params = ctx.lambdaParamList().lambdaParam()
            for lp in l_params:
                p_name = lp.Identifier().getText()
                type_node = lp.type_() if hasattr(lp, 'type_') else (lp.type() if hasattr(lp, 'type') else None)
                p_type = self._get_type_from_ctx(type_node)
                self.scope.define(p_name, Symbol(p_name, p_type, lp))
                print(f"DEBUG: Defined lambda parameter '{p_name}'")
        elif ctx.lambdaName():
            p_name = ctx.lambdaName().getText()
            self.scope.define(p_name, Symbol(p_name, Type.ANY, ctx.lambdaName()))

        self.visit(ctx.block() if ctx.block() else ctx.expr())
        ctx._captured_vars = self.scope.captured_symbols.copy()
        self.exit_scope()
        return Type.FUNCTION

    def visitAssignStmt(self, ctx):
        name = ctx.Identifier().getText()
        expr_type = self.visit(ctx.expr())
        
        symbol, _ = self.scope.resolve(name)
        if not symbol:
            
            self.scope.define(name, Symbol(name, expr_type, ctx))
        else:
            
            symbol.type = expr_type

    def visitLiteral(self, ctx):
        if ctx.IntegerLiteral(): return Type.INT
        if ctx.DecimalLiteral(): return Type.DECIMAL
        if ctx.StringLiteral():  return Type.STRING
        if ctx.BooleanLiteral(): return Type.BOOL
        return Type.ANY

    def visitSelectExpr(self, ctx):
        tbl_type = self.visit(ctx.expr(0))
        if tbl_type != Type.TABLE and tbl_type != Type.ANY:
            self.error("Selection source must be a table", ctx)
        
        
        if ctx.whereClause():
            self.visit(ctx.whereClause())
        return Type.TABLE

    def visitWhereClause(self, ctx):
        
        return self.visit(ctx.expr())

    def visitRowsetExpr(self, ctx):
        self.visit(ctx.rowsetBase())
        if ctx.whereClause():
            self.visit(ctx.whereClause())
        if ctx.orderClause():
            self.visit(ctx.orderClause())
        return Type.TABLE
    
    def visitUpdateStmt(self, ctx):
        for expr in ctx.expr():
            self.visit(expr)

    def visitWriteStmt(self, ctx):
        for expr in ctx.expr():
            self.visit(expr)
    
    def visitAddOp(self, ctx):
        t1 = self.visit(ctx.expr(0))
        t2 = self.visit(ctx.expr(1))
        if t1 == Type.STRING or t2 == Type.STRING: return Type.STRING
        return Type.INT

    def visitCompareOp(self, ctx):
        self.visit(ctx.expr(0))
        self.visit(ctx.expr(1))
        return Type.BOOL
        
    def visitCreateTable(self, ctx):
        if ctx.Identifier():
            name = ctx.Identifier().getText()
            
            self.scope.define(name, Symbol(name, Type.TABLE, ctx))
        
        if ctx.expr():
            self.visit(ctx.expr())
        
        return Type.TABLE

    def visitAddColumn(self, ctx):
        self.visit(ctx.expr(0)) 
        self.visit(ctx.expr(1))
        return Type.VOID

    def visitAddRow(self, ctx):
        for expr in ctx.expr():
            self.visit(expr)
        return Type.VOID

    def visitTableStmt(self, ctx):
        return self.visitChildren(ctx)
   
    def get_var(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise Exception(f"Compiler Error: Variable '{name}' not defined in codegen")

    def set_var(self, name, ptr, typ):
        self.scopes[-1][name] = (ptr, typ)