from instructionParser import instructionParser
class ChipmunkAluGenVisitor(instructionVisitor):
  def __init__(self):
    self.state_vars = set()
    self.packet_fields = set()

  def visitState_vars(self, ctx):
    for i in range(ctx.getChildCount()):
      if (type(ctx.getChild(i)) is instructionParser.State_varContext):
        assert(ctx.getChild(i).getChildCount() == 1)
        assert(ctx.getChild(i).getChild(0).getText() not in self.state_vars)
        self.state_vars.add(ctx.getChild(i).getChild(0).getText())
      else:
        assert(type(ctx.getChild(i)) is instructionParser.State_var_with_commaContext)
        assert(ctx.getChild(i).getChildCount() == 2)
        assert(ctx.getChild(i).getChild(1).getText() not in self.state_vars)
        self.state_vars.add(ctx.getChild(i).getChild(1).getText())

  def visitPacket_fields(self, ctx):
    for i in range(ctx.getChildCount()):
      if (type(ctx.getChild(i)) is instructionParser.Packet_fieldContext):
        assert(ctx.getChild(i).getChildCount() == 1)
        assert(ctx.getChild(i).getChild(0).getText() not in self.state_vars)
        self.packet_fields.add(ctx.getChild(i).getChild(0).getText())
      else:
        assert(type(ctx.getChild(i)) is instructionParser.Packet_field_with_commaContext)
        assert(ctx.getChild(i).getChildCount() == 2)
        assert(ctx.getChild(i).getChild(1).getText() not in self.packet_fields)
        self.packet_fields.add(ctx.getChild(i).getChild(1).getText())

