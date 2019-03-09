from jinja2 import Template, Environment, FileSystemLoader, StrictUndefined
from pathlib import Path
from chipmunk_pickle import ChipmunkPickle
from transforms import LexicalForwardTransform, LexicalBackwardTransform
import sys
import pickle
import subprocess


def usage():
    print("Usage: python3 " + sys.argv[0] +
          " sketch1_name sketch2_name transform_name" +
          " num_pipeline_stages num_alus_per_stage")
    print("transform_name: lexical_forward | lexical_backward")
    sys.exit(1)

if len(sys.argv) < 6:
    usage()
else:
    sketch1_name = str(sys.argv[1])
    sketch2_name = str(sys.argv[2])
    transform = str(sys.argv[3])
    transform_class_map = {"lexical_forward": LexicalForwardTransform,
                           "lexical_backward": LexicalBackwardTransform}
    if not transform in transform_class_map.keys():
        usage()
    num_pipeline_stages = int(sys.argv[4])
    num_alus_per_stage = int(sys.argv[5])
    num_phv_containers = num_alus_per_stage
    env = Environment(
        loader=FileSystemLoader('./templates'), undefined=StrictUndefined)
    assert (pickle.load(open(
        sketch1_name + ".pickle", "rb")).num_fields_in_prog_ == pickle.load(
            open(sketch2_name + ".pickle", "rb")).num_fields_in_prog_)
    assert (pickle.load(open(
        sketch1_name + ".pickle", "rb")).num_state_groups_ == pickle.load(
            open(sketch2_name + ".pickle", "rb")).num_state_groups_)
    num_fields_in_prog = pickle.load(open(sketch1_name + ".pickle",
                                          "rb")).num_fields_in_prog_
    num_state_groups = pickle.load(open(sketch1_name + ".pickle",
                                      "rb")).num_state_groups_
    num_state_slots = pickle.load(open(sketch1_name + ".pickle",
                                      "rb")).num_state_slots_
    opt_verify_template = env.get_template("opt_verify.j2")
    sketch1_holes = pickle.load(open(sketch1_name + ".pickle", "rb")).holes_
    sketch2_holes = pickle.load(open(sketch2_name + ".pickle", "rb")).holes_
    tf_class = transform_class_map[transform]
    tf = tf_class(sketch1_name, sketch2_name,
                  num_pipeline_stages, num_alus_per_stage, num_fields_in_prog,
                  num_phv_containers, sketch1_holes, sketch2_holes)
    transform_function = tf.get_full_transform()
    opt_verifier = opt_verify_template.render(
        sketch1_name=sketch1_name,
        sketch2_name=sketch2_name,
        sketch1_file_name=sketch1_name + "_optverify.sk",
        sketch2_file_name=sketch2_name + "_optverify.sk",
        hole1_arguments=pickle.load(open(sketch1_name + ".pickle",
                                         "rb")).hole_arguments_,
        hole2_arguments=pickle.load(open(sketch2_name + ".pickle",
                                         "rb")).hole_arguments_,
        sketch1_holes=sketch1_holes,
        sketch2_holes=sketch2_holes,
        sketch1_asserts=pickle.load(open(sketch1_name + ".pickle",
                                         "rb")).constraints_,
        sketch2_asserts=pickle.load(open(sketch2_name + ".pickle",
                                         "rb")).constraints_,
        num_fields_in_prog=num_fields_in_prog,
        num_state_groups=num_state_groups,
        transform_function=transform_function,
        num_state_slots=num_state_slots)
    print("Verifier file is ",
          sketch1_name + "_" + sketch2_name + "_verifier.sk")
    verifier_file = sketch1_name + "_" + sketch2_name + "_verifier.sk"
    verifier_file_handle = open(verifier_file, "w")
    verifier_file_handle.write(opt_verifier)
    verifier_file_handle.close()

    # Call sketch on it
    (ret_code,
     output) = subprocess.getstatusoutput("time sketch -V 12 " + verifier_file)
    if (ret_code != 0):
        errors_file = open(verifier_file + ".errors", "w")
        errors_file.write(output)
        errors_file.close()
        print("Verification failed. Output left in " + errors_file.name)
        sys.exit(1)
    else:
        success_file = open(verifier_file + ".success", "w")
        success_file.write(output)
        success_file.close()
        print("Verification succeeded. Output left in " + success_file.name)
        sys.exit(0)
