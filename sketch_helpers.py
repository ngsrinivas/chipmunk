# Helper functions to generate sketch code for synthesis
from jinja2 import Template
from pathlib import Path
import math
import sys
import re

def file_to_str(file_name):
  return Path(file_name).read_text()

# Generate sketch code for stateful ALU by inlining stateful ALU sketch file
def generate_stateful_alu(alu_name, alu_sketch_file):
  # Get alu as a string.
  alu_as_string = Path(alu_sketch_file).read_text()

  # Replace function signature with new function signature.
  function_name = r"StateResult atom_template"
  assert(function_name in alu_as_string)
  alu_as_string = alu_as_string.replace(function_name, "int " + alu_name)

  arg_list = r"(int state_1, int state_2, int pkt_1, int pkt_2, int pkt_3, int pkt_4, int pkt_5) {";
  assert(arg_list in alu_as_string)
  alu_as_string = alu_as_string.replace(arg_list, "(ref int state_1, int pkt_1) { int old_state = state_1;\n")
  # TODO: Fix this. Currently assumes one state variable and one packet variable and no more.

  # Replace return statement with nothing
  alu_as_string = re.sub(r"StateResult ret = new StateResult\(\);\n  ret\.result_state_1 = state_1;\n  ret\.result_state_2 = state_2;\n  return ret;", "return old_state;\n", alu_as_string);

  return alu_as_string
 
# Write all holes to a single hole string for ease of debugging
def generate_hole(hole_name, hole_bit_width):
  generate_hole.hole_names += [hole_name]
  generate_hole.hole_preamble += "int " + hole_name + "= ??(" + str(hole_bit_width) + ");\n"
  generate_hole.total_hole_bits += hole_bit_width
generate_hole.total_hole_bits = 0
generate_hole.hole_names = []
generate_hole.hole_preamble = ""

def add_assert(assert_predicate):
  add_assert.asserts += "assert(" + assert_predicate + ");\n"
add_assert.asserts = ""

# Generate Sketch code for a simple stateless alu (+,-,*,/) 
def generate_stateless_alu(alu_name, potential_operands):
  operand_mux_template   = Template(Path("templates/mux.j2").read_text())
  stateless_alu_template = Template(Path("templates/stateless_alu.j2").read_text())
  stateless_alu = stateless_alu_template.render(potential_operands = potential_operands,
                                                arg_list = ["int " + x for x in potential_operands],
                                                alu_name = alu_name, opcode_hole = alu_name + "_opcode",
                                                immediate_operand_hole = alu_name + "_immediate",
                                                alu_mode_hole = alu_name + "_mode",
                                                mux1 = alu_name + "_mux1", mux2 = alu_name + "_mux2")
  mux_op_1 = generate_mux(len(potential_operands), alu_name + "_mux1")
  mux_op_2 = generate_mux(len(potential_operands), alu_name + "_mux2")
  generate_hole(alu_name + "_opcode", 1)
  generate_hole(alu_name + "_immediate", 2)
  generate_hole(alu_name + "_mode", 2)
  add_assert(alu_name + "_mux1_ctrl <= " + alu_name + "_mux2_ctrl") # symmetry breaking for commutativity
  # add_assert(alu_name +  "_opcode" + "< 2") # Comment out because assert is redundant
  add_assert(alu_name + "_mode" + "< 3")
  return mux_op_1 + mux_op_2 + stateless_alu

def generate_state_allocator(num_pipeline_stages, num_alus_per_stage, num_state_vars):
  for i in range(num_pipeline_stages):
    for l in range(num_state_vars):
      generate_hole("salu_config_" + str(i) + "_" + str(l), 1)

  for i in range(num_pipeline_stages):
    assert_predicate = "("
    for l in range(num_state_vars):
      assert_predicate += "salu_config_" + str(i) + "_" + str(l) + " + "
    assert_predicate += "0) <= " + str(num_alus_per_stage)
    add_assert(assert_predicate)

  for l in range(num_state_vars):
    assert_predicate = "("
    for i in range(num_pipeline_stages):
      assert_predicate += "salu_config_" + str(i) + "_" + str(l) + " + "
    assert_predicate += "0) <= 1"
    add_assert(assert_predicate)

# Sketch code for an n-to-1 mux
def generate_mux(n, mux_name):
  assert(n > 1)
  num_bits = math.ceil(math.log(n, 2))
  operand_mux_template   = Template(Path("templates/mux.j2").read_text())
  mux_code = operand_mux_template.render(mux_name = mux_name,
                                         operand_list = ["input" + str(i) for i in range(0, n)],
                                         arg_list = ["int input" + str(i) for i in range(0, n)],
                                         num_operands = n)
  generate_hole(mux_name + "_ctrl", num_bits)
  add_assert(mux_name + "_ctrl" + "<" + str(n))
  return mux_code
