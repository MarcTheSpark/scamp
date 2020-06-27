#! /usr/bin/python3
import scamp
import importlib.util
import os
import json
import sys
import difflib


if len(sys.argv) > 1 and sys.argv[1] == "-s":
    SAVE_NEW = True
else:
    SAVE_NEW = False


MAX_DIFF_LINES = 8


example_test_directory = "example_tests"

examples = [
    os.path.join(dp, f)
    for dp, dn, filenames in os.walk(example_test_directory)
    for f in filenames if os.path.splitext(f)[1] == '.py'
]


def import_module(python_file_path):
    spec = importlib.util.spec_from_file_location("mod_name", python_file_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def get_example_result(python_file_path):
    mod = import_module(python_file_path)
    results = []
    for result in mod.test_results():
        if isinstance(result, scamp.Score):
            result.composer = ""
            result.title = ""
            results.append(str(result))
            results.append(str(result.to_music_xml().to_xml(pretty_print=True)))
            results.append(str(result.to_lilypond()))
        else:
            results.append(str(result))
    return results


def save_example_result(python_file_path):
    json_path = python_file_path.replace(".py", ".json")
    with open(json_path, 'w') as fp:
        json.dump(get_example_result(python_file_path), fp, sort_keys=True, indent=4)


def test_example_result(python_file_path):
    json_path = python_file_path.replace(".py", ".json")
    if os.path.exists(json_path):
        with open(json_path, 'r') as fp:
            saved_results = json.load(fp)
        new_results = get_example_result(python_file_path)
        if saved_results == new_results:
            return True
        else:
            out = []
            for a, b in zip(saved_results, new_results):
                if a == b:
                    out.append(True)
                else:
                    diffs = [x for x in difflib.ndiff(a.split("\n"), b.split("\n")) if x.startswith(("-", "+"))]
                    if len(diffs) > MAX_DIFF_LINES:
                        out.append("\n".join(diffs[:MAX_DIFF_LINES]) + "\n ... etc ...")
                    else:
                        out.append("\n".join(diffs))
            return out
    else:
        raise FileNotFoundError("Could not test example result for {}. No prior result has been saved.".format(
            python_file_path
        ))


failures = 0
total = 0

for example_path in examples:
    if SAVE_NEW:
        print("Saving result for {}...".format(example_path))
        save_example_result(example_path)
        print("DONE")
    else:
        print("Testing result for {}...".format(example_path))
        test_results = test_example_result(example_path)
        if test_results is True:
            print("SUCCESS")
        else:
            print('\033[91m' + "FAILURE")
            for i, item in enumerate(test_results):
                if item is not True:
                    print("Failed result {} with diff:".format(i + 1))
                    print(item)
            print('\033[0m')
            failures += 1
        total += 1


if not SAVE_NEW:
    print('\033[1m' + "{}/{} scripts tested successfully".format(total - failures, total) + '\033[0m')
