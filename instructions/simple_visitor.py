from instructionVisitor import instructionVisitor
class SimpleVisitor(instructionVisitor):
  def visitUpdate(self, ctx):
    print(ctx.getText())
  def visitGuard(self, ctx):
    print(ctx.getText())
