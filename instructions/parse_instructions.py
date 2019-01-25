import sys
from antlr4 import *
from instructionLexer import instructionLexer
from instructionParser import instructionParser
 
def main(argv):
    input = FileStream(argv[1])
    lexer = instructionLexer(input)
    stream = CommonTokenStream(lexer)
    parser = instructionParser(stream)
    tree = parser.instruction()
 
if __name__ == '__main__':
    main(sys.argv)
