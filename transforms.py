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

    def emit_transforms_unset_holes(self, set_real_holes):
        assert isinstance(set_real_holes, set)
        unset_holes = self._get_unset_common_holes(set_real_holes)
        return "\n".join([self.sketch2_name + "_" + h + " = " +
                          self.sketch1_name + "_" + h + ";"
                          for h in unset_holes])

    def _get_unset_common_holes(self, set_real_holes):
        return self._get_real_hole_intersection() - set_real_holes

    def _get_real_hole_intersection(self):
        return set(self._get_real_hole_names(1)).intersection(
            set(self._get_real_hole_names(2)))

    def get_hole_difference(self):
        """ Return the set of holes that are unique to sketch2. """
        real_hole_diff = set(self._get_real_hole_names(2)) - set(
            self._get_real_hole_names(1))
        return [self.sketch2_name + "_" + hole for hole in real_hole_diff]

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
    real_hole_names = ["stateless_alu_0_0_mux1_ctrl",
                       "stateless_alu_0_0_mux2_ctrl",
                       "stateless_alu_0_0_opcode",
                       "stateless_alu_0_0_immediate",
                       "stateless_alu_0_0_mode",
                       "stateless_alu_0_1_mux1_ctrl",
                       "stateless_alu_0_1_mux2_ctrl",
                       "stateless_alu_0_1_opcode",
                       "stateless_alu_0_1_immediate",
                       "stateless_alu_0_1_mode",
                       "stateful_alu_0_0_Mux2_0_global",
                       "stateful_alu_0_0_Opt_0_global",
                       "stateful_alu_0_0_const_0_global",
                       "stateless_alu_1_0_mux1_ctrl",
                       "stateless_alu_1_0_mux2_ctrl",
                       "stateless_alu_1_0_opcode",
                       "stateless_alu_1_0_immediate",
                       "stateless_alu_1_0_mode",
                       "stateless_alu_1_1_mux1_ctrl",
                       "stateless_alu_1_1_mux2_ctrl",
                       "stateless_alu_1_1_opcode",
                       "stateless_alu_1_1_immediate",
                       "stateless_alu_1_1_mode",
                       "stateful_alu_1_0_Mux2_0_global",
                       "stateful_alu_1_0_Opt_0_global",
                       "stateful_alu_1_0_const_0_global",
                       "stateful_operand_mux_0_0_0_ctrl",
                       "stateful_operand_mux_1_0_0_ctrl",
                       "output_mux_phv_0_0_ctrl",
                       "output_mux_phv_0_1_ctrl",
                       "output_mux_phv_1_0_ctrl",
                       "output_mux_phv_1_1_ctrl",
                       "phv_config_0_0",
                       "phv_config_1_0",
                       "salu_config_0_0",
                       "salu_config_1_0"]
    sketch1_holes = ["trial1_" + hole for hole in real_hole_names]
    sketch2_holes = ["trial2_" + hole for hole in real_hole_names]
    sketch2_holes += ["trial_simple_test_config_x_y"]
    lt = LexicalTransform("trial1", "trial2", 3, 3, sketch1_holes,
                          sketch2_holes)
    print(len(real_hole_names))
    print(len(lt.get_hole_difference()))
    set_real_holes = lt._get_real_hole_intersection() - set(
        ["stateful_operand_mux_0_0_0_ctrl", "salu_config_0_0"])
    print(lt.emit_transforms_unset_holes(set_real_holes))
