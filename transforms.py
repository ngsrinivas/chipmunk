""" Transform for the lexical mapping optimization """

class Transform:
    """ Base class defining a transformation from the holes of sketch1 to
    sketch2. """
    def __init__(self, sketch1_name, sketch2_name, num_pipeline_stages,
                 num_alus_per_stage, num_fields_in_prog, num_phv_containers,
                 sketch1_holes, sketch2_holes):
        self.sketch1_name = sketch1_name
        self.sketch2_name = sketch2_name
        self.num_pipeline_stages = num_pipeline_stages
        self.num_alus_per_stage  = num_alus_per_stage
        self.num_fields_in_prog  = num_fields_in_prog
        self.num_phv_containers  = num_phv_containers
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

class LexicalForwardTransform(Transform):
    """ Sketch1 does not have holes for PHV mappings (optimized sketch with
    lexical mappings). Sketch2 does have explicit field to PHV mappings. 
    """
    def __init__(self, sketch1_name, sketch2_name, num_pipeline_stages,
                 num_alus_per_stage, num_fields_in_prog, num_phv_containers,
                 sketch1_holes, sketch2_holes):
        super().__init__(sketch1_name, sketch2_name, num_pipeline_stages,
                         num_alus_per_stage, num_fields_in_prog,
                         num_phv_containers, sketch1_holes, sketch2_holes)
        self.set_real_holes = set()
        
    def build_many_to_one_transform(self):
        # For sketch1 (*without* PHV mappings), construct the appropriate mapping
        # for sketch2 (*with* PHV mappings).
        transform_list = list()
        for i in range(self.num_phv_containers):
            for j in range(self.num_fields_in_prog):
                real_hole_name = "phv_config_" + str(i) + "_" + str(j)
                transform_list.append(self.sketch2_name + "_" + real_hole_name
                                      + " =  " +
                                      ("1" if i == j else "0") + ";")
                self.set_real_holes.add(real_hole_name)
        return "\n".join(transform_list)

    def get_full_transform(self):
        phv_transform = self.build_many_to_one_transform()
        rest_of_the_transform = super().emit_transforms_unset_holes(
            self.set_real_holes)
        return phv_transform + "\n" + rest_of_the_transform

class LexicalBackwardTransform(Transform):
    """ Sketch1 does have holes for PHV mappings (unoptimized sketch). Sketch2
    does not have explicit field to PHV mappings (optimizsed sketch).
    """
    def __init__(self, sketch1_name, sketch2_name, num_pipeline_stages,
                 num_alus_per_stage, num_fields_in_prog, num_phv_containers,
                 sketch1_holes, sketch2_holes):
        super().__init__(sketch1_name, sketch2_name, num_pipeline_stages,
                         num_alus_per_stage, num_fields_in_prog,
                         num_phv_containers, sketch1_holes, sketch2_holes)
        self.set_real_holes = set()

    def build_one_to_many_transform(self):
        # For sketch1 (*with* PHV mappings), construct the appropriate
        # mapping for sketch2 (*without* PHV mappings).
        # Basic idea is that if mapping[phv_i][field_j] is set, then all
        # occurrences of phv_j (input or output) must be replaced by phv_i.
        # We do this by learning a permutation j --> i from the given PHV
        # mappings.
        transform_list = list()
        # (0) Set up the permutation array from fields to PHVs
        transform_list.append("int[" + str(self.num_fields_in_prog) + "] perm;")
        for j in range(self.num_fields_in_prog):
            for i in range(self.num_phv_containers):
                hole_name = (self.sketch1_name + "_phv_config_" + str(i) +
                             "_" + str(j))
                perm =  "if (" + hole_name + " == 1) {\n"
                perm += "  perm[" + str(j) + "] = " + str(i) + ";\n"
                perm += "}"
                transform_list.append(perm)
        # TODO: Is perm[x] always set for all field indices x?
        # (1) If input stateless_alu_p_q_mux{1|2}_ctrl has value r, then must set
        # stateless_alu_p_perm[q]_mux{1|2}_ctrl to have value perm[r].
        for i in range(self.num_pipeline_stages):
            for j in range(self.num_alus_per_stage):
                for q in [1, 2]:
                    sketch1_real_hole = ("stateless_alu_" + str(i) + "_" +
                                         str(j) + "_mux" + str(q) + "_ctrl")
                    sketch1_hole = (self.sketch1_name + "_" + sketch1_real_hole)
                    for r in range(self.num_fields_in_prog):
                        sketch2_real_hole = ("stateless_alu_" + str(i) + "_" +
                                             str(r) + "_mux" + str(q) + "_ctrl")
                        sketch2_hole = (self.sketch2_name + "_" +
                                        sketch2_real_hole)
                        perm = "if " if r == 0 else "else if "
                        perm += "(perm[" + str(j) + "] == " + str(r) + ") {\n"
                        perm += sketch2_hole + " = perm[" + sketch1_hole + "];\n} "
                        transform_list.append(perm)
                    self.set_real_holes.add(self.sketch2_name + "_" +
                                            sketch1_real_hole)
        return "\n".join(transform_list)
        # (2) If stateful_operand_mux_p_t_s has value r, then must set
        # stateful_operand_mux_p_t_perm[s] to have value perm[r].
        # (3) If output_mux_phv_p_q_ctrl has value r, then must set
        # output_mux_phv_p_perm[q]_ctrl has value perm[r].

    def get_full_transform(self):
        phv_transform = self.build_one_to_many_transform()
        rest_of_the_transform = super().emit_transforms_unset_holes(
            self.set_real_holes)
        return phv_transform + "\n" + rest_of_the_transform

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
                       "salu_config_0_0",
                       "salu_config_1_0"]
    sketch1_holes = ["trial1_" + hole for hole in real_hole_names]
    sketch2_holes = ["trial2_" + hole for hole in real_hole_names]
    sketch2_holes += ["trial2_phv_config_0_0",
                      "trial2_phv_config_1_0"]
    lft = LexicalForwardTransform("trial1", "trial2", 3, 3, 1, 2,
                                 sketch1_holes, sketch2_holes)
    print("Total holes in sketch1: " + str(len(real_hole_names)))
    print("Holes in sketch2 but not sketch1: " + str(len(lft.get_hole_difference())))
    print("---- many to one transform ----")
    print(lft.build_many_to_one_transform())
    print("---- transforms for 'unset' but common holes ----")
    set_real_holes = lft.set_real_holes
    print(lft.emit_transforms_unset_holes(set_real_holes))
    print("---- full transform ---")
    print(lft.get_full_transform())
    print("---- one to many transform ----")
    lbt = LexicalBackwardTransform("trial2", "trial1", 3, 3, 1, 2,
                                   sketch2_holes, sketch1_holes)
    print(lbt.build_one_to_many_transform())
    print("---- transforms for 'unset' but common holes ----")
    set_real_holes = lbt.set_real_holes
    print(lbt.emit_transforms_unset_holes(set_real_holes))
    print("---- full transform ---")
    print(lbt.get_full_transform())
