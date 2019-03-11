""" Transform for the lexical mapping optimization """

import sys
import pickle
from chipmunk_pickle import ChipmunkPickle
from sketch_generator import Hole

class Transform:
    """ Base class defining a transformation from the holes of sketch1 to
    sketch2. """
    def __init__(self, sketch1_name, sketch2_name, num_pipeline_stages,
                 num_alus_per_stage, num_fields_in_prog, num_phv_containers,
                 sketch1_holes, sketch2_holes, num_state_groups,
                 num_operands_to_stateful_alu):
        self.sketch1_name = sketch1_name
        self.sketch2_name = sketch2_name
        self.num_pipeline_stages = num_pipeline_stages
        self.num_alus_per_stage  = num_alus_per_stage
        self.num_fields_in_prog  = num_fields_in_prog
        self.num_phv_containers  = num_phv_containers
        self.sketch1_holes = sketch1_holes
        self.sketch2_holes = sketch2_holes
        self.num_state_groups = num_state_groups
        self.num_operands_to_stateful_alu = num_operands_to_stateful_alu

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
        return [self._get_real_hole_name(sketch_name, hole) for hole in sketch_holes]

    def _get_real_hole_name(self, sketch_name, hole):
        if isinstance(hole, Hole):
            return hole.name[len(sketch_name) + 1:]
        elif isinstance(hole, str):
            return hole[len(sketch_name)+1:]
        else:
            print("Unknown hole type")
            assert(False)

class LexicalForwardTransform(Transform):
    """ Sketch1 does not have holes for PHV mappings (optimized sketch with
    lexical mappings). Sketch2 does have explicit field to PHV mappings. 
    """
    def __init__(self, sketch1_name, sketch2_name, num_pipeline_stages,
                 num_alus_per_stage, num_fields_in_prog, num_phv_containers,
                 sketch1_holes, sketch2_holes, num_state_groups,
                 num_operands_to_stateful_alu):
        super().__init__(sketch1_name, sketch2_name, num_pipeline_stages,
                         num_alus_per_stage, num_fields_in_prog,
                         num_phv_containers, sketch1_holes, sketch2_holes,
                         num_state_groups, num_operands_to_stateful_alu)
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
                 sketch1_holes, sketch2_holes, num_state_groups,
                 num_operands_to_stateful_alu):
        super().__init__(sketch1_name, sketch2_name, num_pipeline_stages,
                         num_alus_per_stage, num_fields_in_prog,
                         num_phv_containers, sketch1_holes, sketch2_holes,
                         num_state_groups, num_operands_to_stateful_alu)
        self.set_real_holes = set()

    def _init_perms(self):
        # Return initialized permission vector
        perm_init = list()
        perm_init.append("int[" + str(self.num_fields_in_prog) + "] perm;")
        for j in range(self.num_fields_in_prog): # for each field
            for i in range(self.num_fields_in_prog): # for each phv container
                hole_name = (self.sketch1_name + "_phv_config_" + str(i) +
                             "_" + str(j))
                perm =  "if (" + hole_name + " == 1) {\n"
                perm += "  perm[" + str(j) + "] = " + str(i) + ";\n"
                perm += "}"
                perm_init.append(perm)
        return "\n".join(perm_init)

    def _assign_perm_based_input(self, sketch1_hole, sketch2_hole, indent):
        # When some ALU input has value r in the original sketch,
        # the transformed sketch has value:
        # perm[r] if r < num_fields_in_prog
        # r, otherwise
        assign_stmt  = indent + "if (" + sketch1_hole + " < "
        assign_stmt += str(self.num_fields_in_prog) + ") {\n"
        assign_stmt += indent + "  " + sketch2_hole + " = perm[" + sketch1_hole
        assign_stmt += "];\n" + indent + "} else {\n" + indent + "  "
        assign_stmt += sketch2_hole + " = " + sketch1_hole + ";\n" + indent
        assign_stmt += "}\n"
        return assign_stmt

    def _assign_perm_based_output(self, sketch1_hole, sketch2_hole,
                                  sketch1_alu_index, sketch2_alu_index,
                                  assign_direct_value, indent):
        # Generic function to permute ALU indices while assigning values
        # sketch1_alu_index represents the index of the ALU within its stage in
        # the original sketch. Similarly, sketch2_alu_index.
        if sketch1_alu_index < self.num_fields_in_prog:
            # This ALU in the original sketch is writing to a
            # packet-field-related PHV. Need to determine if sketch2_hole is the
            # right transformed hole that will process the same inputs as this ALU.
            assign_stmt  = indent
            assign_stmt += "if " if sketch2_alu_index == 0 else "else if"
            assign_stmt += "(perm[" + str(sketch1_alu_index) + "] == "
            assign_stmt += str(sketch2_alu_index) + ") {\n"
            if assign_direct_value:
                # e.g., for a phv input mux, the value assigned to the ctrl
                # doesn't change since (1) stateful ALUs are not permuted, (2)
                # stateless ALUs are permuted to write to the phv corresponding
                # to the right field. 
                assign_stmt += sketch2_hole + " = " + sketch1_hole + ";\n"
            else:
                # e.g., for input muxes to stateless ALUs, the ctrl must also
                # change (which corresponds to permuting the ALU inputs to
                # ensure that the correct fields are read)
                assign_stmt += self._assign_perm_based_input(sketch1_hole,
                                                             sketch2_hole,
                                                             indent + "  ")
            assign_stmt += indent + "}\n"
            return assign_stmt
        else:
            if sketch2_alu_index == sketch1_alu_index:
                if assign_direct_value:
                    # e.g., a phv input mux for a non-packet-field phv
                    # container. This phv doesn't require to be permuted with
                    # another one; its inputs aren't permuted either.
                    return sketch2_hole + " = " + sketch1_hole + ";\n"
                else:
                    # e.g., a stateless ALU in the original sketch is writing to
                    # a metadata (non-packet-field) PHV. The corresponding ALU
                    # in the transformed sketch is the same. However, its inputs
                    # must still be mapped using the permutation.
                    return self._assign_perm_based_input(sketch1_hole,
                                                         sketch2_hole,
                                                         indent)
            else:
                return ""

    def _init_stateless_alus(self):
        # If stateless alu (i, j) writes to a field (ie: j < num_fields_in_prog)
        # and stateless_alu_i_j_mux{m}_ctrl has value r,
        # then set stateless_alu_i_perm[j]_mux{m}_ctrl to value:
        # perm[r] if r < num_fields_in_prog
        # r otherwise
        stateless_alu_assignments = list()
        for m in [1, 2]: # do separately for each MUX input to the ALUs
            for i in range(self.num_pipeline_stages):
                # Do an N*N iteration over all possible ALU to ALU mappings
                # between the original grid and the transformed grid.
                for j in range(self.num_alus_per_stage):
                    for k in range(self.num_alus_per_stage):
                        sketch1_hole = (self.sketch1_name
                                        + "_stateless_alu_" + str(i) + "_" +
                                        str(j) + "_mux" + str(m) + "_ctrl")
                        sketch2_hole = (self.sketch2_name
                                        + "_stateless_alu_" + str(i) + "_" +
                                        str(k) + "_mux" + str(m) + "_ctrl")
                        assign_stmt = self._assign_perm_based_output(sketch1_hole,
                                                                     sketch2_hole,
                                                                     j, k, False,
                                                                     "")
                        stateless_alu_assignments.append(assign_stmt)
                        self.set_real_holes.add(self._get_real_hole_name(
                            self.sketch2_name, sketch2_hole))
        return "\n".join(stateless_alu_assignments)

    def _init_stateful_alus(self):
        stateful_alu_assignments = list()
        # Initialize inputs?
        assert self.num_phv_containers == self.num_alus_per_stage
        for i in range(self.num_pipeline_stages):
            for j in range(self.num_alus_per_stage):
                for k in range(self.num_alus_per_stage):
                    sketch1_hole = (self.sketch1_name
                                    + "_output_mux_phv_" + str(i) + "_" +
                                    str(j) + "_ctrl")
                    sketch2_hole = (self.sketch2_name
                                    + "_output_mux_phv_" + str(i) + "_" +
                                    str(k) + "_ctrl")
                    assign_stmt = self._assign_perm_based_output(sketch1_hole,
                                                                 sketch2_hole,
                                                                 j, k, True, "")
                    stateful_alu_assignments.append(assign_stmt)
                    self.set_real_holes.add(self._get_real_hole_name(
                        self.sketch2_name, sketch2_hole))
        for i in range(self.num_pipeline_stages):
            for j in range(self.num_state_groups):
                for k in range(self.num_operands_to_stateful_alu):
                    sketch1_hole = (self.sketch1_name + "_stateful_operand_mux_"
                                    + str(i) + "_" + str(j) + "_" + str(k) +
                                    "_ctrl")
                    sketch2_hole = (self.sketch2_name + "_stateful_operand_mux_"
                                    + str(i) + "_" + str(j) + "_" + str(k) +
                                    "_ctrl")
                    stateful_alu_assignments.append(
                        self._assign_perm_based_input(sketch1_hole,
                                                      sketch2_hole, ""))
                    self.set_real_holes.add(self._get_real_hole_name(
                        self.sketch2_name, sketch2_hole))
        return "\n".join(stateful_alu_assignments)

    def build_one_to_many_transform(self):
        # For sketch1 (*with* PHV mappings), construct the appropriate
        # mapping for sketch2 (*without* PHV mappings).
        # Basic idea is that if mapping[phv_i][field_j] is set, then all
        # occurrences of phv_j (input or output) must be replaced by phv_i.
        # We do this by learning a permutation j --> i from the given PHV
        # mappings.
        # TODO: Is perm[x] always set for all field indices x?
        assert self.num_fields_in_prog <= self.num_phv_containers
        perm_init = self._init_perms()
        stateless_alus = self._init_stateless_alus()
        stateful_alus = self._init_stateful_alus()
        print("*********")
        print(perm_init)
        print("*********")
        print(stateless_alus)
        print("*********")
        print(stateful_alus)
        print("*********")
        return "\n".join([perm_init, stateless_alus, stateful_alus])

    def get_full_transform(self):
        phv_transform = self.build_one_to_many_transform()
        rest_of_the_transform = super().emit_transforms_unset_holes(
            self.set_real_holes)
        return phv_transform + "\n" + rest_of_the_transform

def sample_unit_test():
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
                      "trial2_phv_config_1_0",
                      "trial2_phv_config_2_0",
                      "trial2_phv_config_0_1",
                      "trial2_phv_config_1_1",
                      "trial2_phv_config_2_1"]
    lft = LexicalForwardTransform("trial1", "trial2", 3, 3, 2, 3,
                                  sketch1_holes, sketch2_holes, 3, 1)
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
    lbt = LexicalBackwardTransform("trial2", "trial1", 3, 3, 2, 3,
                                   sketch2_holes, sketch1_holes, 3, 1)
    print(lbt.build_one_to_many_transform())
    print("---- transforms for 'unset' but common holes ----")
    set_real_holes = lbt.set_real_holes
    print(lbt.emit_transforms_unset_holes(set_real_holes))
    print("---- full transform ---")
    print(lbt.get_full_transform())

def usage():
    print("Usage: python3 " + argv[0] + " " +
          "<original_sketch_name> <transformed_sketch_name> " +
          "<transform_name> <number of pipeline stages> " +
          "<number of stateless/stateful ALUs per stage> " +
          "<number of fields in prog> <number of state groups per stage>" +
          "<number of operands per stateful alu>")
    print("transform_name: lexical_forward | lexical_backward")
    exit(1)

if __name__ == "__main__":
    argv = sys.argv
    if len(argv) < 9:
        usage()
    sketch1_name = argv[1]
    sketch2_name = argv[2]
    transform = argv[3]
    num_pipeline_stages = int(argv[4])
    num_alus_per_stage = int(argv[5])
    num_fields_in_prog = int(argv[6])
    num_phv_containers = num_alus_per_stage
    num_state_groups = int(argv[7])
    num_operands_to_stateful_alu = int(argv[8])

    transform_class_map = {"lexical_forward": LexicalForwardTransform,
                           "lexical_backward": LexicalBackwardTransform}
    if not transform in transform_class_map.keys():
        usage()

    transform_class = transform_class_map[transform]
    sketch1_holes=pickle.load(open(sketch1_name + ".pickle", "rb")).holes_
    sketch2_holes=pickle.load(open(sketch2_name + ".pickle", "rb")).holes_

    t = transform_class(sketch1_name, sketch2_name, num_pipeline_stages,
                        num_alus_per_stage, num_fields_in_prog, num_phv_containers,
                        sketch1_holes, sketch2_holes, num_state_groups,
                        num_operands_to_stateful_alu)
    print(t.get_full_transform())
