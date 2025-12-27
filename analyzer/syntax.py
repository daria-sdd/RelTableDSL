import sys
from antlr4 import InputStream, CommonTokenStream, FileStream
from antlr4.error.ErrorListener import ErrorListener
from gen.RelTableLexer import RelTableLexer
from gen.RelTableParser import RelTableParser

class CollectingErrorListener(ErrorListener):
    def __init__(self):
        super().__init__()
        self.errors = []
     
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        tok_text = getattr(offendingSymbol, 'text', str(offendingSymbol))
        message = f"line {line}:{column} near '{tok_text}' — {msg}"
        self.errors.append({
            'line': line,
            'col': column,
            'token': tok_text,
            'msg': msg
        })

def parse_string(source_text: str, filename: str = "<input>"):
    input_stream = InputStream(source_text)
    lexer = RelTableLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = RelTableParser(stream)

    listener = CollectingErrorListener()
    parser.removeErrorListeners()
    lexer.removeErrorListeners()
    parser.addErrorListener(listener)
    lexer.addErrorListener(listener)

    tree = parser.program()
    return listener.errors, tree

if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = open(sys.argv[1], encoding='utf-8').read()
        fname = sys.argv[1]
    else:
        print("Введите код (Ctrl-D для EOF):")
        text = sys.stdin.read()
        fname = "<stdin>"

    errors, tree = parse_string(text, fname)

    if not errors:
        print("Синтаксических ошибок не найдено.")
    else:
        print(f"Найдено {len(errors)} синтаксическая(их) ошибка(ок):")
        for e in errors:
            print(f"  Line {e['line']}, Col {e['col']}: {e['msg']} (токен: {e['token']})")
