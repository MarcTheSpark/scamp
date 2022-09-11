#! /usr/bin/python3

#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #
#  This file is part of SCAMP (Suite for Computer-Assisted Music in Python)                      #
#  Copyright © 2020 Marc Evanstein <marc@marcevanstein.com>.                                     #
#                                                                                                #
#  This program is free software: you can redistribute it and/or modify it under the terms of    #
#  the GNU General Public License as published by the Free Software Foundation, either version   #
#  3 of the License, or (at your option) any later version.                                      #
#                                                                                                #
#  This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;     #
#  without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.     #
#  See the GNU General Public License for more details.                                          #
#                                                                                                #
#  You should have received a copy of the GNU General Public License along with this program.    #
#  If not, see <http://www.gnu.org/licenses/>.                                                   #
#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #

from io import BytesIO
import scamp
import importlib.util
import os
import json
import sys
import re
import random
from difflib import Differ
from collections import namedtuple, defaultdict

if len(sys.argv) > 1 and sys.argv[1] == "-s":
    SAVE_NEW = True
else:
    SAVE_NEW = False

START_RED_TEXT = '\033[91m'
STOP_RED_TEXT = '\033[0m'

# number of unaltered lines before and after it shows in the diff
NUM_DIFF_CONTEXT_LINES = 2


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


def diff_comparison(a, b, num_context_lines=NUM_DIFF_CONTEXT_LINES):
    if a == b:
        return True
    diff = Differ().compare(a.splitlines(True), b.splitlines(True))
    processed_diff = []
    normal_buffer = []  # buffer of unchanged lines (don't want to print them all)
    for line in diff:
        if line.startswith(" "):  # normal line
            normal_buffer.append(line)
        else:
            if len(normal_buffer) > 2 * num_context_lines + 1:
                if len(processed_diff) > 0:
                    processed_diff.append(normal_buffer[0])
                processed_diff.append("...\n")
                processed_diff.extend(normal_buffer[-num_context_lines:])
            else:
                processed_diff.extend(normal_buffer)
            normal_buffer.clear()
            processed_diff.append(line)

    if len(normal_buffer) > num_context_lines:
        processed_diff.extend(normal_buffer[:num_context_lines])
        processed_diff.append("...\n")
    else:
        processed_diff.extend(normal_buffer)
    return f"Differences found:\n" + "".join(processed_diff)


def check_equal_comparison(a, b):
    if a == b:
        return True
    return "Differences found."


ComparisonProtocol = namedtuple("ComparisonProtocol", "name prep_function comparison")


def _performance_to_midi_byte_stream(perf):
    with BytesIO() as byte_stream:
        perf.export_to_midi_file(byte_stream)
        byte_stream.seek(0)
        return byte_stream.read()


def _prep_score(scr):
    scr.title = scr.composer = None
    return scr


result_type_to_comparison_protocols = defaultdict(
    lambda: (ComparisonProtocol(None, str, diff_comparison), ),
    {
        scamp.Score: (
            ComparisonProtocol("Score", lambda x: str(_prep_score(x)), diff_comparison),
            ComparisonProtocol(
                "Score->MusicXML",
                lambda x: re.sub(r"\n.*<encoding-date>.*</encoding-date>", "",
                                 _prep_score(x).to_music_xml().to_xml(pretty_print=True)),
                diff_comparison
            ),
            ComparisonProtocol("Score->LilyPond", lambda x: _prep_score(x).to_lilypond(), diff_comparison)
        ),
        scamp.Performance: (
            ComparisonProtocol("Performance", str, diff_comparison),
            ComparisonProtocol("Performance->MIDIFile", lambda x: str(_performance_to_midi_byte_stream(x)),
                               check_equal_comparison)
        )
    }
)


def get_example_result(python_file_path):
    # restore state
    scamp.engraving_settings.restore_factory_defaults()
    random.seed(0)
    mod = import_module(python_file_path)
    protocols_and_prepped_results = [
        (comparison_protocol._replace(name=type(raw_result).__name__ )
         if comparison_protocol.name is None else comparison_protocol, comparison_protocol.prep_function(raw_result))
        for raw_result in mod.test_results()
        for comparison_protocol in result_type_to_comparison_protocols[type(raw_result)]
    ]
    # return (list of comparison protocols, list of prepped results)
    return tuple(zip(*protocols_and_prepped_results))


def save_example_result(python_file_path):
    json_path = python_file_path.replace(".py", ".json")
    with open(json_path, 'w') as fp:
        protocols, results = get_example_result(python_file_path)
        json.dump(results, fp, sort_keys=True, indent=4)


def test_example_result(python_file_path):
    json_path = python_file_path.replace(".py", ".json")
    if os.path.exists(json_path):
        with open(json_path, 'r') as fp:
            saved_results = json.load(fp)
        new_protocols, new_results = get_example_result(python_file_path)
        if len(new_results) != len(saved_results):
            return f"{START_RED_TEXT}Mismatched number of results: {len(saved_results)} saved, " \
                   f"but {len(new_results)} new.{STOP_RED_TEXT}"

        result_comparisons = [
            protocol.comparison(saved_result, new_result)
            for protocol, saved_result, new_result in zip(new_protocols, saved_results, new_results)
        ]

        if all(x is True for x in result_comparisons):
            return True
        else:
            return START_RED_TEXT + "\n".join(
                f"FAILED result {i + 1} ({new_protocols[i].name}): \n{result_comparison}"
                for i, result_comparison in enumerate(result_comparisons)
                if result_comparison is not True
            ) + STOP_RED_TEXT
    else:
        return START_RED_TEXT + "FAILED: No saved result" + STOP_RED_TEXT


if SAVE_NEW:
    for example_path in examples:
        print("Saving result for {}...".format(example_path))
        save_example_result(example_path)
        print("DONE")
else:
    total = 0
    successes = 0
    for example_path in examples:
        print("Testing result for {}...".format(example_path))
        example_test_result = test_example_result(example_path)
        if example_test_result is True:
            successes += 1
            print("SUCCESS")
        else:
            print(example_test_result)
        total += 1
        print()
    print('\033[1m' + "{}/{} scripts tested successfully".format(successes, total) + '\033[0m')
