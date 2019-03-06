""" Transform for the lexical mapping optimization """

class Transform:
    """ Base class defining a transformation from the holes of sketch1 to
    sketch2. """
    def __init__(self, sketch1_name, sketch2_name, num_pipeline_stages,
                 num_alus_per_stage, sketch1_holes, sketch2_holes):
        self.sketch1_name = sketch1_name
        self.sketch2_name = sketch2_name
        self.num_pipeline_stages = num_pipeline_stages
        self.num_alus_per_stage  = num_alus_per_stage
        self.sketch1_holes = sketch1_holes
        self.sketch2_holes = sketch2_holes

    def get_real_hole_intersection(self):
        return set(self._get_real_hole_names(1)).intersection(
            set(self._get_real_hole_names(2)))

    def _get_real_hole_names(self, sketch_index):
        """ Return a set of hole names (without the sketch names) given a sketch
        index which is either 1 or 2. """
        assert sketch_index in [1, 2]
        sketch_name  = self.sketch1_name  if sketch_index == 1 else self.sketch2_name
        sketch_holes = self.sketch1_holes if sketch_index == 1 else self.sketch2_holes
        return [hole[len(sketch_name)+1:] for hole in sketch_holes]

class LexicalTransform(Transform):
    """ Sketch1 does not have holes for PHV mappings (optimized sketch with
    lexical mappings). Sketch2 does have explicit field to PHV mappings. 
    """
    def __init__(self, sketch1_name, sketch2_name, num_pipeline_stages,
                 num_alus_per_stage, sketch1_holes, sketch2_holes):
        super().__init__(sketch1_name, sketch2_name, num_pipeline_stages,
                         num_alus_per_stage, sketch1_holes, sketch2_holes)
        
    def manyToOneTransform(self):
        # For sketch1 (*without* PHV mappings), construct the appropriate mapping
        # for sketch2 (*with* PHV mappings).
        # TODO
        print("Hello, world!")

if __name__ == "__main__":
    hole_names = ["trial_simple_stateless_alu_0_0_mux1_ctrl",
                  "trial_simple_stateless_alu_0_0_mux2_ctrl",
                  "trial_simple_stateless_alu_0_0_opcode",
                  "trial_simple_stateless_alu_0_0_immediate",
                  "trial_simple_stateless_alu_0_0_mode",
                  "trial_simple_stateless_alu_0_1_mux1_ctrl",
                  "trial_simple_stateless_alu_0_1_mux2_ctrl",
                  "trial_simple_stateless_alu_0_1_opcode",
                  "trial_simple_stateless_alu_0_1_immediate",
                  "trial_simple_stateless_alu_0_1_mode",
                  "trial_simple_stateful_alu_0_0_Mux2_0_global",
                  "trial_simple_stateful_alu_0_0_Opt_0_global",
                  "trial_simple_stateful_alu_0_0_const_0_global",
                  "trial_simple_stateless_alu_1_0_mux1_ctrl",
                  "trial_simple_stateless_alu_1_0_mux2_ctrl",
                  "trial_simple_stateless_alu_1_0_opcode",
                  "trial_simple_stateless_alu_1_0_immediate",
                  "trial_simple_stateless_alu_1_0_mode",
                  "trial_simple_stateless_alu_1_1_mux1_ctrl",
                  "trial_simple_stateless_alu_1_1_mux2_ctrl",
                  "trial_simple_stateless_alu_1_1_opcode",
                  "trial_simple_stateless_alu_1_1_immediate",
                  "trial_simple_stateless_alu_1_1_mode",
                  "trial_simple_stateful_alu_1_0_Mux2_0_global",
                  "trial_simple_stateful_alu_1_0_Opt_0_global",
                  "trial_simple_stateful_alu_1_0_const_0_global",
                  "trial_simple_stateful_operand_mux_0_0_0_ctrl",
                  "trial_simple_stateful_operand_mux_1_0_0_ctrl",
                  "trial_simple_output_mux_phv_0_0_ctrl",
                  "trial_simple_output_mux_phv_0_1_ctrl",
                  "trial_simple_output_mux_phv_1_0_ctrl",
                  "trial_simple_output_mux_phv_1_1_ctrl",
                  "trial_simple_phv_config_0_0",
                  "trial_simple_phv_config_1_0",
                  "trial_simple_salu_config_0_0",
                  "trial_simple_salu_config_1_0"]
    lt = LexicalTransform("trial_simple", "trial_simple", 3, 3,
                          hole_names, hole_names)
    print(len(hole_names))
    print(len(lt.get_real_hole_intersection()))
    print(lt.get_real_hole_intersection())
