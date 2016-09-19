# Copyright (c) 2015 Intel, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import re

import pep8

"""
Guidelines for writing new hacking checks

 - Use only for Magnum specific tests. OpenStack general tests
   should be submitted to the common 'hacking' module.
 - Pick numbers in the range M3xx. Find the current test with
   the highest allocated number and then pick the next value.
   If nova has an N3xx code for that test, use the same number.
 - Keep the test method code in the source file ordered based
   on the M3xx value.
 - List the new rule in the top level HACKING.rst file
 - Add test cases for each new rule to magnum/tests/unit/test_hacking.py

"""
UNDERSCORE_IMPORT_FILES = []

mutable_default_args = re.compile(r"^\s*def .+\((.+=\{\}|.+=\[\])")
assert_equal_in_end_with_true_or_false_re = re.compile(
    r"assertEqual\((\w|[][.'\"])+ in (\w|[][.'\", ])+, (True|False)\)")
assert_equal_in_start_with_true_or_false_re = re.compile(
    r"assertEqual\((True|False), (\w|[][.'\"])+ in (\w|[][.'\", ])+\)")
assert_equal_end_with_none_re = re.compile(
    r"(.)*assertEqual\((\w|\.|\'|\"|\[|\])+, None\)")
assert_equal_start_with_none_re = re.compile(
    r"(.)*assertEqual\(None, (\w|\.|\'|\"|\[|\])+\)")
assert_not_equal_end_with_none_re = re.compile(
    r"(.)*assertNotEqual\((\w|\.|\'|\"|\[|\])+, None\)")
assert_not_equal_start_with_none_re = re.compile(
    r"(.)*assertNotEqual\(None, (\w|\.|\'|\"|\[|\])+\)")
assert_equal_with_true_re = re.compile(
    r"assertEqual\(True,")
assert_equal_with_false_re = re.compile(
    r"assertEqual\(False,")
asse_equal_with_is_not_none_re = re.compile(
    r"assertEqual\(.*?\s+is+\s+not+\s+None\)$")
assert_true_isinstance_re = re.compile(
    r"(.)*assertTrue\(isinstance\((\w|\.|\'|\"|\[|\])+, "
    "(\w|\.|\'|\"|\[|\])+\)\)")
dict_constructor_with_list_copy_re = re.compile(r".*\bdict\((\[)?(\(|\[)")
assert_xrange_re = re.compile(
    r"\s*xrange\s*\(")
log_translation = re.compile(
    r"(.)*LOG\.(audit|error|critical)\(\s*('|\")")
log_translation_info = re.compile(
    r"(.)*LOG\.(info)\(\s*(_\(|'|\")")
log_translation_exception = re.compile(
    r"(.)*LOG\.(exception)\(\s*(_\(|'|\")")
log_translation_LW = re.compile(
    r"(.)*LOG\.(warning|warn)\(\s*(_\(|'|\")")
custom_underscore_check = re.compile(r"(.)*_\s*=\s*(.)*")
underscore_import_check = re.compile(r"(.)*import _(.)*")
translated_log = re.compile(
    r"(.)*LOG\.(audit|error|info|critical|exception)"
    "\(\s*_\(\s*('|\")")
string_translation = re.compile(r"[^_]*_\(\s*('|\")")


def assert_equal_none(logical_line):
    """Check for assertEqual(A, None) or assertEqual(None, A) sentences

    M318
    """
    msg = ("M318: assertEqual(A, None) or assertEqual(None, A) "
           "sentences not allowed")
    res = (assert_equal_start_with_none_re.match(logical_line) or
           assert_equal_end_with_none_re.match(logical_line))
    if res:
        yield (0, msg)


def assert_not_equal_none(logical_line):
    """Check for assertNotEqual(A, None) or assertNotEqual(None, A) sentences

    M319
    """
    msg = ("M319: assertNotEqual(A, None) or assertNotEqual(None, A) "
           "sentences not allowed")
    res = (assert_not_equal_start_with_none_re.match(logical_line) or
           assert_not_equal_end_with_none_re.match(logical_line))
    if res:
        yield (0, msg)


def no_mutable_default_args(logical_line):
    msg = "M322: Method's default argument shouldn't be mutable!"
    if mutable_default_args.match(logical_line):
        yield (0, msg)


def assert_equal_true_or_false(logical_line):
    """Check for assertEqual(True, A) or assertEqual(False, A) sentences

    M323
    """
    res = (assert_equal_with_true_re.search(logical_line) or
           assert_equal_with_false_re.search(logical_line))
    if res:
        yield (0, "M323: assertEqual(True, A) or assertEqual(False, A) "
               "sentences not allowed")


def assert_equal_not_none(logical_line):
    """Check for assertEqual(A is not None) sentences M302"""
    msg = "M302: assertEqual(A is not None) sentences not allowed."
    res = asse_equal_with_is_not_none_re.search(logical_line)
    if res:
        yield (0, msg)


def assert_true_isinstance(logical_line):
    """Check for assertTrue(isinstance(a, b)) sentences

    M316
    """
    if assert_true_isinstance_re.match(logical_line):
        yield (0, "M316: assertTrue(isinstance(a, b)) sentences not allowed")


def validate_log_translations(logical_line, physical_line, filename=None):
    if pep8.noqa(physical_line):
        return
    msg = "M328: LOG.info messages require translations `_LI()`!"
    if log_translation_info.match(logical_line):
        yield (0, msg)
    msg = "M329: LOG.exception messages require translations `_LE()`!"
    if log_translation_exception.match(logical_line):
        yield (0, msg)
    msg = "M330: LOG.warning, LOG.warn messages require translations `_LW()`!"
    if log_translation_LW.match(logical_line):
        yield (0, msg)
    msg = "M321: Log messages require translations!"
    if log_translation.match(logical_line):
        yield (0, msg)


def assert_equal_in(logical_line):
    """Check for assertEqual(True|False, A in B), assertEqual(A in B, True|False)

    M338
    """
    res = (assert_equal_in_start_with_true_or_false_re.search(logical_line) or
           assert_equal_in_end_with_true_or_false_re.search(logical_line))
    if res:
        yield (0, "M338: Use assertIn/NotIn(A, B) rather than "
                  "assertEqual(A in B, True/False) when checking collection "
                  "contents.")


def no_xrange(logical_line):
    """Disallow 'xrange()'

    M339
    """
    if assert_xrange_re.match(logical_line):
        yield(0, "M339: Do not use xrange().")


def use_timeutils_utcnow(logical_line, filename):
    # tools are OK to use the standard datetime module
    if "/tools/" in filename:
        return

    msg = "M310: timeutils.utcnow() must be used instead of datetime.%s()"
    datetime_funcs = ['now', 'utcnow']
    for f in datetime_funcs:
        pos = logical_line.find('datetime.%s' % f)
        if pos != -1:
            yield (pos, msg % f)


def dict_constructor_with_list_copy(logical_line):
    msg = ("M336: Must use a dict comprehension instead of a dict constructor"
           " with a sequence of key-value pairs."
           )
    if dict_constructor_with_list_copy_re.match(logical_line):
        yield (0, msg)


def no_log_warn(logical_line):
    """Disallow 'LOG.warn('

    Deprecated LOG.warn(), instead use LOG.warning
    https://bugs.launchpad.net/magnum/+bug/1508442

    M352
    """

    msg = ("M352: LOG.warn is deprecated, please use LOG.warning!")
    if "LOG.warn(" in logical_line:
        yield (0, msg)


def check_explicit_underscore_import(logical_line, filename):
    """Check for explicit import of the _ function

    We need to ensure that any files that are using the _() function
    to translate logs are explicitly importing the _ function.  We
    can't trust unit test to catch whether the import has been
    added so we need to check for it here.
    """

    # Build a list of the files that have _ imported.  No further
    # checking needed once it is found.
    if filename in UNDERSCORE_IMPORT_FILES:
        pass
    elif (underscore_import_check.match(logical_line) or
          custom_underscore_check.match(logical_line)):
        UNDERSCORE_IMPORT_FILES.append(filename)
    elif (translated_log.match(logical_line) or
          string_translation.match(logical_line)):
        yield(0, "M340: Found use of _() without explicit import of _ !")


def factory(register):
    register(no_mutable_default_args)
    register(assert_equal_none)
    register(assert_not_equal_none)
    register(assert_equal_true_or_false)
    register(assert_equal_not_none)
    register(assert_true_isinstance)
    register(assert_equal_in)
    register(use_timeutils_utcnow)
    register(dict_constructor_with_list_copy)
    register(no_xrange)
    register(no_log_warn)
    register(validate_log_translations)
    register(check_explicit_underscore_import)
