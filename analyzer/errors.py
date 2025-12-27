class SemanticError(Exception):
    def __init__(self, message, line=None, column=None):
        self.message = message
        self.line = line
        self.column = column

    def __str__(self):
        pos = f" [Line {self.line}, Col {self.column}]" if self.line else ""
        return f"Semantic Error: {self.message}{pos}"
