import sys
from antlr4 import InputStream, CommonTokenStream
from gen.RelTableLexer import RelTableLexer
from gen.RelTableParser import RelTableParser
from analyzer.semantic import RelTableSemanticAnalyzer
from compiler.codegen import RelTableCompiler

def compile_file(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        source = f.read()

    # 1. Парсинг
    input_stream = InputStream(source)
    lexer = RelTableLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = RelTableParser(stream)
    tree = parser.program()

    if parser.getNumberOfSyntaxErrors() > 0:
        print("Syntax errors found.")
        sys.exit(1)

    # 2. Семантика
    analyzer = RelTableSemanticAnalyzer()
    analyzer.visit(tree)
    if analyzer.errors:
        for err in analyzer.errors: print(err)
        sys.exit(1)

    # 3. Кодогенерация
    compiler = RelTableCompiler(semantic_info=analyzer)
    llvm_module = compiler.visit(tree)

    # 4. Сохранение по указанному пути
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(str(llvm_module))
    
    print(f"IR successfully written to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python main_compiler.py <input.dsl> <output.ll>")
    else:
        compile_file(sys.argv[1], sys.argv[2])