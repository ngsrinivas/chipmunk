from instructionVisitor import instructionVisitor
class SimpleVisitor(instructionVisitor):
  def visitInstruction(self, ctx):
    return "hello, hi, bye"
