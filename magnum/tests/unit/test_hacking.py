#    Copyright 2015 Intel, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import textwrap

import mock
import pep8

from magnum.hacking import checks
from magnum.tests import base


class HackingTestCase(base.TestCase):
    """Hacking test class.

    This class tests the hacking checks in magnum.hacking.checks by passing
    strings to the check methods like the pep8/flake8 parser would. The parser
    loops over each line in the file and then passes the parameters to the
    check method. The parameter names in the check method dictate what type of
    object is passed to the check method. The parameter types are::

        logical_line: A processed line with the following modifications:
            - Multi-line statements converted to a single line.
            - Stripped left and right.
            - Contents of strings replaced with "xxx" of same length.
            - Comments removed.
        physical_line: Raw line of text from the input file.
        lines: a list of the raw lines from the input file
        tokens: the tokens that contribute to this logical line
        line_number: line number in the input file
        total_lines: number of lines in the input file
        blank_lines: blank lines before this one
        indent_char: indentation character in this file (" " or "\t")
        indent_level: indentation (with tabs expanded to multiples of 8)
        previous_indent_level: indentation on previous line
        previous_logical: previous logical line
        filename: Path of the file being run through pep8

    When running a test on a check method the return will be False/None if
    there is no violation in the sample input. If there is an error a tuple is
    returned with a position in the line, and a message. So to check the result
    just assertTrue if the check is expected to fail and assertFalse if it
    should pass.
    """
    # We are patching pep8 so that only the check under test is actually
    # installed.

    @mock.patch('pep8._checks',
                {'physical_line': {}, 'logical_line': {}, 'tree': {}})
    def _run_check(self, code, checker, filename=None):
        pep8.register_check(checker)

        lines = textwrap.dedent(code).strip().splitlines(True)

        checker = pep8.Checker(filename=filename, lines=lines)
        checker.check_all()
        checker.report._deferred_print.sort()
        return checker.report._deferred_print

    def _assert_has_errors(self, code, checker, expected_errors=None,
                           filename=None):
        actual_errors = [e[:3] for e in
                         self._run_check(code, checker, filename)]
        self.assertEqual(expected_errors or [], actual_errors)

    def _assert_has_no_errors(self, code, checker, filename=None):
        self._assert_has_errors(code, checker, filename=filename)

    def test_assert_equal_in(self):
        errors = [(1, 0, "M338")]
        check = checks.assert_equal_in

        code = "self.assertEqual(a in b, True)"
        self._assert_has_errors(code, check, errors)

        code = "self.assertEqual('str' in 'string', True)"
        self._assert_has_errors(code, check, errors)

        code = "self.assertEqual(any(a==1 for a in b), True)"
        self._assert_has_no_errors(code, check)

        code = "self.assertEqual(True, a in b)"
        self._assert_has_errors(code, check, errors)

        code = "self.assertEqual(True, 'str' in 'string')"
        self._assert_has_errors(code, check, errors)

        code = "self.assertEqual(True, any(a==1 for a in b))"
        self._assert_has_no_errors(code, check)

        code = "self.assertEqual(a in b, False)"
        self._assert_has_errors(code, check, errors)

        code = "self.assertEqual('str' in 'string', False)"
        self._assert_has_errors(code, check, errors)

        code = "self.assertEqual(any(a==1 for a in b), False)"
        self._assert_has_no_errors(code, check)

        code = "self.assertEqual(False, a in b)"
        self._assert_has_errors(code, check, errors)

        code = "self.assertEqual(False, 'str' in 'string')"
        self._assert_has_errors(code, check, errors)

        code = "self.assertEqual(False, any(a==1 for a in b))"
        self._assert_has_no_errors(code, check)

    def test_assert_equal_none(self):
        errors = [(1, 0, "M318")]
        check = checks.assert_equal_none

        code = "self.assertEqual(A, None)"
        self._assert_has_errors(code, check, errors)

        code = "self.assertEqual(None, A)"
        self._assert_has_errors(code, check, errors)

        code = "self.assertIsNone()"
        self._assert_has_no_errors(code, check)

    def test_assert_equal_true_or_false(self):
        errors = [(1, 0, "M323")]
        check = checks.assert_equal_true_or_false

        code = "self.assertEqual(True, A)"
        self._assert_has_errors(code, check, errors)

        code = "self.assertEqual(False, A)"
        self._assert_has_errors(code, check, errors)

        code = "self.assertTrue()"
        self._assert_has_no_errors(code, check)

        code = "self.assertFalse()"
        self._assert_has_no_errors(code, check)

    def test_no_mutable_default_args(self):
        errors = [(1, 0, "M322")]
        check = checks.no_mutable_default_args

        code = "def get_info_from_bdm(virt_type, bdm, mapping=[])"
        self._assert_has_errors(code, check, errors)

        code = "defined = []"
        self._assert_has_no_errors(code, check)

        code = "defined, undefined = [], {}"
        self._assert_has_no_errors(code, check)

    def test_assert_is_not_none(self):
        errors = [(1, 0, "M302")]
        check = checks.assert_equal_not_none

        code = "self.assertEqual(A is not None)"
        self._assert_has_errors(code, check, errors)

        code = "self.assertIsNone()"
        self._assert_has_no_errors(code, check)

    def test_assert_true_isinstance(self):
        errors = [(1, 0, "M316")]
        check = checks.assert_true_isinstance

        code = "self.assertTrue(isinstance(e, exception.BuilAbortException))"
        self._assert_has_errors(code, check, errors)

        code = "self.assertTrue()"
        self._assert_has_no_errors(code, check)

    def test_use_timeunitls_utcow(self):
        errors = [(1, 0, "M310")]
        check = checks.use_timeutils_utcnow

        code = "datetime.now"
        self._assert_has_errors(code, check, errors)

        code = "datetime.utcnow"
        self._assert_has_errors(code, check, errors)

        code = "datetime.aa"
        self._assert_has_no_errors(code, check)

        code = "aaa"
        self._assert_has_no_errors(code, check)

    def test_dict_constructor_with_list_copy(self):
        self.assertEqual(1, len(list(checks.dict_constructor_with_list_copy(
            "    dict([(i, connect_info[i])"))))

        self.assertEqual(1, len(list(checks.dict_constructor_with_list_copy(
            "    attrs = dict([(k, _from_json(v))"))))

        self.assertEqual(1, len(list(checks.dict_constructor_with_list_copy(
            "        type_names = dict((value, key) for key, value in"))))

        self.assertEqual(1, len(list(checks.dict_constructor_with_list_copy(
            "   dict((value, key) for key, value in"))))

        self.assertEqual(1, len(list(checks.dict_constructor_with_list_copy(
            "foo(param=dict((k, v) for k, v in bar.items()))"))))

        self.assertEqual(1, len(list(checks.dict_constructor_with_list_copy(
            " dict([[i,i] for i in range(3)])"))))

        self.assertEqual(1, len(list(checks.dict_constructor_with_list_copy(
            "  dd = dict([i,i] for i in range(3))"))))

        self.assertEqual(0, len(list(checks.dict_constructor_with_list_copy(
            "        create_kwargs = dict(snapshot=snapshot,"))))

        self.assertEqual(0, len(list(checks.dict_constructor_with_list_copy(
            "      self._render_dict(xml, data_el, data.__dict__)"))))
