from jinja2 import Template, Environment, FileSystemLoader, StrictUndefined
import pickle
from pathlib import Path
import sys
import math
from   sketch_helpers import *
import re
import subprocess
import random
import tempfile

# Use a regex to scan the program and extract the largest packet field index and largest state variable index
def get_num_pkt_fields_and_state_vars(program):
  pkt_fields = [int(x) for x in re.findall("state_and_packet.pkt_(\d+)", program)]
  state_vars = [int(x) for x in re.findall("state_and_packet.state_(\d+)", program)]
  return (max(pkt_fields) + 1, max(state_vars) + 1)

# Convention for indices:
# i : pipeline stage
# j : ALU within pipeline stage
# k : PHV container within pipeline stage
# l : packet field or state variable from program

if (len(sys.argv) < 6):
  print("Usage: python3 " + sys.argv[0] + " <program file> <number of pipeline stages> <number of stateless/stateful ALUs per stage> <codegen/optverif> <output_name (w/o file extension)>")
  sys.exit(1)
else:
  program_file         = str(sys.argv[1])
  (num_fields_in_prog, num_state_vars) = get_num_pkt_fields_and_state_vars(Path(program_file).read_text())
  num_pipeline_stages  = int(sys.argv[2])
  num_alus_per_stage   = int(sys.argv[3])
  num_phv_containers   = num_alus_per_stage
  assert(num_fields_in_prog <= num_phv_containers)
  mode                 = str(sys.argv[4])
  output_name          = str(sys.argv[5])

operand_mux_definitions = ""
output_mux_definitions  = ""
alu_definitions         = ""
# Generate one mux for inputs: num_phv_containers+1 to 1. The +1 is to support constant/immediate operands.
for i in range(num_pipeline_stages):
  for l in range(num_state_vars):
    operand_mux_definitions += generate_mux(num_phv_containers, "stateful_operand_mux_" + str(i) + "_" + str(l)) + "\n"

# Output mux for stateful ALUs
for i in range(num_pipeline_stages):
  for k in range(num_phv_containers):
    # Note: We are generating a mux that takes as input all virtual stateful ALUs + corresponding stateless ALU
    # The number of virtual stateful ALUs is more or less than the physical stateful ALUs because it equals the
    # number of state variables in the program_file, but this doesn't affect correctness
    # because we enforce that the total number of active virtual stateful ALUs is within the physical limit.
    # It also doesn't affect the correctness of modeling the output mux because the virtual output mux setting can be
    # translated into the physical output mux setting during post processing.
    output_mux_definitions += generate_mux(num_state_vars + 1, "output_mux_phv_" + str(i) + "_" + str(k)) + "\n"

# Generate sketch code for alus and immediate operands in each stage
for i in range(num_pipeline_stages):
  for j in range(num_alus_per_stage):
    alu_definitions += generate_stateless_alu("stateless_alu_" + str(i) + "_" + str(j), ["input" + str(k) for k in range(0, num_phv_containers)]) + "\n"
  for l in range(num_state_vars):
    alu_definitions += generate_stateful_alu("stateful_alu_" + str(i) + "_" + str(l)) + "\n"

# Ensures each state var is assigned to exactly stateful ALU and vice versa.
generate_state_allocator(num_pipeline_stages, num_alus_per_stage, num_state_vars)

# Create sketch_file_as_string
env = Environment(loader = FileSystemLoader('./templates'), undefined = StrictUndefined)

if (mode == "codegen"):
  code_gen_template = env.get_template("code_generator.j2")
  code_generator = code_gen_template.render(mode = "codegen",
                                            program_file = program_file,
                                            num_pipeline_stages = num_pipeline_stages,
                                            num_alus_per_stage = num_alus_per_stage,
                                            num_phv_containers = num_phv_containers,
                                            hole_definitions = generate_hole.hole_preamble,
                                            operand_mux_definitions = operand_mux_definitions,
                                            output_mux_definitions = output_mux_definitions,
                                            alu_definitions = alu_definitions,
                                            num_fields_in_prog = num_fields_in_prog,
                                            num_state_vars = num_state_vars,
                                            spec_as_sketch = Path(program_file).read_text(),
                                            all_assertions = add_assert.asserts)

  # Create file and write sketch_harness into it.
  sketch_file = open(output_name + ".sk", "w")
  sketch_file.write(code_generator)
  sketch_file.close()

  # Call sketch on it
  print("Total number of hole bits is", generate_hole.total_hole_bits)
  print("Sketch file is ", sketch_file.name)
  (ret_code, output) = subprocess.getstatusoutput("time sketch -V 12 --slv-seed=1 --slv-parallel --bnd-inbits=2 --bnd-int-range=50 " + sketch_file.name)
  if (ret_code != 0):
    errors_file = open(output_name + ".errors", "w")
    errors_file.write(output)
    errors_file.close()
    print("Sketch failed. Output left in " + errors_file.name)
    sys.exit(1)
  else:
    success_file = open(output_name + ".success", "w")
    for hole_name in generate_hole.hole_names:
      hits = re.findall("(" + hole_name + ")__" + "\w+ = (\d+)", output)
      assert(len(hits) == 1)
      assert(len(hits[0]) == 2)
      print("int ", hits[0][0], " = ", hits[0][1], ";")
    success_file.write(output)
    success_file.close()
    print("Sketch succeeded. Generated configuration is given above. Output left in " + success_file.name)
    sys.exit(0)

elif (mode == "optverif"):
  sketch_function_template = env.get_template("sketch_functions.j2")
  sketch_function = sketch_function_template.render(mode = "optverif",
                                                    program_file = program_file,
                                                    num_pipeline_stages = num_pipeline_stages,
                                                    num_alus_per_stage = num_alus_per_stage,
                                                    num_phv_containers = num_phv_containers,
                                                    operand_mux_definitions = operand_mux_definitions,
                                                    output_mux_definitions = output_mux_definitions,
                                                    alu_definitions = alu_definitions,
                                                    num_fields_in_prog = num_fields_in_prog,
                                                    num_state_vars = num_state_vars,
                                                    hole_arguments = generate_hole.hole_arguments,
                                                    sketch_name = output_name)
  # Create files and write sketch_function, holes, and constraints into them.
  sketch_file = open(output_name + ".sk", "w")
  sketch_file.write(sketch_function)
  sketch_file.close()
  print("Sketch file is ", sketch_file.name)

  holes_file   = open(output_name + ".holes", "wb")
  pickle.dump([generate_hole.holes] + [generate_hole.hole_arguments], holes_file)
  holes_file.close()
  print("Holes file is ", holes_file.name)

  constraints_file = open(output_name + ".constraints", "wb")
  pickle.dump(add_assert.constraints, constraints_file)
  constraints_file.close()
  print("Constraints file is ", constraints_file.name)

  print("Total number of hole bits is", generate_hole.total_hole_bits)

else:
  assert(False)
