grammar RelTable;

program
  : statement* EOF
  ;

statement
  : funcDecl
  | funcCallStmt SEMI?
  | tableStmt SEMI?
  | controlStmt
  | assignStmt SEMI?
  | writeStmt SEMI?
  | dropStmt SEMI?
  | updateStmt SEMI?
  | breakStmt
  | exprStmt SEMI?
  | SEMI
  ;

exprStmt
  : expr
  ;
  

lambdaParam
  : type Identifier       
  | Identifier            
  ;

lambdaParamList
  : lambdaParam (COMMA lambdaParam)*
  ;

lambdaName
  : Identifier
  | ROW
  ;

lambdaExpr
  : LAMBDA lambdaName ARROW expr                
  | LAMBDA lambdaName ARROW block               
  | LPAREN lambdaParamList? RPAREN ARROW expr   
  | LPAREN lambdaParamList? RPAREN ARROW block  
  | LAMBDA lambdaName block                     
  ;

funcDecl
  : FUNC Identifier LPAREN paramList? RPAREN block
  ;

paramList
  : param (COMMA param)*
  ;

param
  : type Identifier
  ;

block
  : LBRACE statement* RBRACE
  ;

funcCallExpr
  : Identifier LPAREN argList? RPAREN
  ;

funcCallStmt
  : funcCallExpr
  ;
  
argList
  : expr (COMMA expr)*
  ;

 
tableStmt
  : createTable
  | addColumn
  | addRow
  | deleteColumn
  | deleteRow
  ;

createTable
  : ( Identifier ASSIGN )? CREATE_TABLE LPAREN expr RPAREN
  ;

dropStmt
  : DROP_TABLE LPAREN expr RPAREN
  ;

addColumn
  : ADD_COLUMN LPAREN expr COMMA expr COMMA type RPAREN
  ;

deleteColumn
  : DELETE_COLUMN LPAREN expr COMMA expr RPAREN
  ;

addRow
  : ADD_ROW LPAREN expr (COMMA expr)+ RPAREN
  ;

deleteRow
  : DELETE_ROW LPAREN expr (COMMA expr)+ RPAREN
  ;

assignStmt
  : Identifier ASSIGN expr
  ;

updateStmt
  : UPDATE_ROW LPAREN expr COMMA expr COMMA expr (COMMA expr)? RPAREN
  ;

writeStmt
  : WRITE LPAREN expr (COMMA expr)* RPAREN
  ;

controlStmt
  : ifStmt
  | switchStmt
  | forStmt
  | returnStmt
  ;

ifStmt
  : IF expr ( block | statement )
    ( ELIF expr ( block | statement ) )*
    ( ELSE ( block | statement ) )?
  ;
 
switchStmt
  : SWITCH (expr)? LBRACE switchCase* defaultCase? RBRACE
  ;

switchCase
  : CASE caseExprList COLON statement*
  ;

caseExprList
  : caseExpr (COMMA caseExpr)*
  ;

caseExpr
  : expr ( TO expr )?
  ;

defaultCase
  : DEFAULT COLON statement*
  ;

forStmt
  : FOR Identifier ASSIGN expr TO expr ( block | statement )
  ;

returnStmt
  : RETURN expr?
  ;

breakStmt
  : BREAK SEMI?
  ;

// ---------------- Expressions ----------------

rowsetBase
  : primaryExpr
  ;

rowsetExpr
  : rowsetBase whereClause? orderClause?
  ;

baseExpr
  : literal
  | Identifier
  | lambdaExpr
  | selectExpr
  | LPAREN expr RPAREN
  ;

whereClause
  : WHERE expr
  ;

orderClause
  : ORDER BY expr ( ASC | DESC )?
  ;

primaryExpr
  : baseExpr                                     
  | primaryExpr LPAREN argList? RPAREN           
  | primaryExpr DOT Identifier                     
  | primaryExpr LBRACK expr RBRACK                
  ;

 
expr
  : expr (AND | OR) expr                   
  | expr (EQ | NEQ | GT | LT | GTE | LTE | CONTAINS) expr  
  | expr (PLUS | MINUS) expr                
  | expr (MUL | DIV) expr                
  | expr PIPE expr                         
  | NOT expr                               
  | primaryExpr                            
  ;


selectExpr
  : SELECT LPAREN expr (COMMA expr)* RPAREN whereClause? orderClause?
  ;

literal
  : IntegerLiteral
  | DecimalLiteral
  | StringLiteral
  | BooleanLiteral
  | MUL
  ;

type
  : TABLE
  | ROW
  | COLUMN
  | INT
  | DECIMAL
  | STRING
  | BOOL
  ;

// ---------- LEXER ----------

// ключевые слова
FUNC        : 'func' ;
CREATE_TABLE: 'create_table' ;
DROP_TABLE  : 'drop_table' ;
ADD_COLUMN  : 'add_column' ;
DELETE_COLUMN : 'delete_column' ;
ADD_ROW     : 'add_row' ;
DELETE_ROW  : 'delete_row' ;
UPDATE_ROW  : 'update_row' ;
WRITE       : 'write' ;
IF          : 'if' ;
ELIF        : 'elif' ;
ELSE        : 'else' ;
SWITCH      : 'switch' ;
CASE        : 'case' ;
DEFAULT     : 'default' ;
FOR         : 'for' ;
TO          : 'to' ;
RETURN      : 'return' ;
BREAK       : 'break' ;
SELECT      : 'select' ;
WHERE       : 'where' ;
ORDER       : 'order' ;
BY          : 'by' ;
CONTAINS    : 'contains' ;
ASC         : 'asc' ;
DESC        : 'desc' ;

TABLE       : 'table' ;
ROW         : 'row' ;
COLUMN      : 'column' ;
INT         : 'int' ;
DECIMAL     : 'decimal' ;
STRING      : 'string' ;
BOOL        : 'bool' ;

// логические / сравнительные операторы
ARROW  : '=>' ;
LAMBDA : '\\' ;
AND   : 'and' ;
OR    : 'or' ;
NOT   : 'not' ;
EQ    : '==' ;
NEQ   : '!=' ;
GTE   : '>=' ;
LTE   : '<=' ;
GT    : '>' ;
LT    : '<' ;

// символы и операторы 
ASSIGN : '=' ;
PLUS   : '+' ;
MINUS  : '-' ;
MUL    : '*' ;
DIV    : '/' ;
PIPE   : '|' ;

// пунктуация
LPAREN : '(' ;
RPAREN : ')' ;
LBRACE : '{' ;
RBRACE : '}' ;
LBRACK : '[' ;
RBRACK : ']' ;
SEMI   : ';' ;
COMMA  : ',' ;
DOT    : '.' ;
COLON  : ':' ;

// литералы
StringLiteral  : '"' (~["\r\n])* '"' ;
IntegerLiteral : [0-9]+ ;
DecimalLiteral : [0-9]+ '.' [0-9]+ ;
BooleanLiteral : 'true' | 'false' ;

// идентификаторы (латиница + кириллица если нужно)
fragment ASCII_LETTER : [A-Za-z] ;
fragment CYRILLIC_LETTER : [\u0400-\u04FF] ;
fragment LETTER : ASCII_LETTER | CYRILLIC_LETTER | '_' ;
Identifier : LETTER ( LETTER | [0-9] )* ;

// пробелы и комментарии
WS : [ \t\r\n]+ -> skip ;
LINE_COMMENT : '//' ~[\r\n]* -> skip ;
DASH_COMMENT : '--' ~[\r\n]* -> skip ;
BLOCK_COMMENT : '/*' .*? '*/' -> skip ;
