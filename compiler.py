from pathlib import Path
import pickle
import re
import subprocess
import sys

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from chipmunk_pickle import ChipmunkPickle
from sketch_generator import SketchGenerator
from utils import get_num_pkt_fields_and_state_groups


class Compiler:
    def __init__(self, program_file, alu_file, num_pipeline_stages,
                 num_alus_per_stage, sketch_name, parallel_or_serial,
                 lex_opt_enabled):
        self.program_file = program_file
        self.alu_file = alu_file
        self.num_pipeline_stages = num_pipeline_stages
        self.num_alus_per_stage = num_alus_per_stage
        self.sketch_name = sketch_name
        self.parallel_or_serial = parallel_or_serial
        self.lex_opt_enabled = lex_opt_enabled

        (self.num_fields_in_prog,
         self.num_state_groups) = get_num_pkt_fields_and_state_groups(
             Path(program_file).read_text())

        assert self.num_fields_in_prog <= num_alus_per_stage

        # Initialize jinja2 environment for templates
        self.jinja2_env = Environment(
            loader=FileSystemLoader('./templates'), undefined=StrictUndefined, trim_blocks = True, lstrip_blocks = True)
        # Create an object for sketch generation
        self.sketch_generator = SketchGenerator(
            sketch_name=sketch_name,
            num_pipeline_stages=num_pipeline_stages,
            num_alus_per_stage=num_alus_per_stage,
            num_phv_containers=num_alus_per_stage,
            num_state_groups=self.num_state_groups,
            num_fields_in_prog=self.num_fields_in_prog,
            jinja2_env=self.jinja2_env,
            alu_file=alu_file,
            lex_opt_enabled=lex_opt_enabled)

        # Create stateless and stateful ALUs, operand muxes for stateful ALUs,
        # and output muxes.
        self.alu_definitions = self.sketch_generator.generate_alus()
        self.stateful_operand_mux_definitions = (
            self.sketch_generator.generate_stateful_operand_muxes())
        self.output_mux_definitions = (
            self.sketch_generator.generate_output_muxes())
        self.field_to_phv_mappings, self.phv_to_field_mappings = "", ""
        if lex_opt_enabled == "no":
            fst, snd = self.sketch_generator.generate_phv_config()
            self.field_to_phv_mappings = fst
            self.phv_to_field_mappings = snd

        # Create allocator to ensure each state var is assigned to exactly
        # stateful ALU and vice versa.
        self.sketch_generator.generate_state_allocator()

        # Get number of state slots in stateful ALU from sketch_generator
        self.num_state_slots = self.sketch_generator.num_state_slots_

    def codegen(self):
        """Codegeneration"""
        codegen_code = self.sketch_generator.generate_sketch(
            program_file=self.program_file,
            alu_definitions=self.alu_definitions,
            stateful_operand_mux_definitions=self.
            stateful_operand_mux_definitions,
            mode="codegen",
            output_mux_definitions=self.output_mux_definitions,
            field_to_phv_mappings=self.field_to_phv_mappings,
            phv_to_field_mappings=self.phv_to_field_mappings)

        # Create file and write sketch_harness into it.
        sketch_file_name = self.sketch_name + "_codegen.sk"
        with open(sketch_file_name, "w") as sketch_file:
            sketch_file.write(codegen_code)

        # Call sketch on it
        print("Total number of hole bits is",
              self.sketch_generator.total_hole_bits_)
        print("Sketch file is ", sketch_file_name)
        if self.parallel_or_serial == "parallel":
            (ret_code, output) = subprocess.getstatusoutput(
                "time sketch -V 12 --slv-seed=1 --slv-parallel " +
                "--bnd-inbits=2 --bnd-int-range=50 " + sketch_file_name)
        else:
            (ret_code, output) = subprocess.getstatusoutput(
                "time sketch -V 12 --slv-seed=1 --bnd-inbits=2 " +
                "--bnd-int-range=50 " + sketch_file_name)

        return (ret_code, output)

    def optverify(self):
        """Opt Verify"""
        optverify_code = self.sketch_generator.generate_sketch(
            program_file=self.program_file,
            alu_definitions=self.alu_definitions,
            stateful_operand_mux_definitions=self.
            stateful_operand_mux_definitions,
            mode="optverify",
            output_mux_definitions=self.output_mux_definitions,
            field_to_phv_mappings=self.field_to_phv_mappings,
            phv_to_field_mappings=self.phv_to_field_mappings)

        # Create file and write sketch_function into it
        with open(self.sketch_name + "_optverify.sk", "w") as sketch_file:
            sketch_file.write(optverify_code)
            print("Sketch file is ", sketch_file.name)

        # Put the rest (holes, hole arguments, constraints, etc.) into a .pickle
        # file.
        with open(self.sketch_name + ".pickle", "wb") as pickle_file:
            pickle.dump(
                ChipmunkPickle(
                    holes=self.sketch_generator.holes_,
                    hole_arguments=self.sketch_generator.hole_arguments_,
                    constraints=self.sketch_generator.constraints_,
                    num_fields_in_prog=self.num_fields_in_prog,
                    num_state_groups=self.num_state_groups,
                    num_state_slots=self.num_state_slots), pickle_file)
            print("Pickle file is ", pickle_file.name)

        print("Total number of hole bits is",
              self.sketch_generator.total_hole_bits_)
