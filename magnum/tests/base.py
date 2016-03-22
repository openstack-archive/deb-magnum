# Copyright 2010-2011 OpenStack Foundation
# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
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

import copy
import os

import mock
from oslo_config import cfg
from oslo_log import log
from oslotest import base
import pecan
import testscenarios

from magnum.common import context as magnum_context
from magnum.objects import base as objects_base
from magnum.tests import conf_fixture
from magnum.tests import policy_fixture


CONF = cfg.CONF
try:
    log.register_options(CONF)
except cfg.ArgsAlreadyParsedError:
    pass
CONF.set_override('use_stderr', False)


class BaseTestCase(testscenarios.WithScenarios, base.BaseTestCase):
    """Test base class."""

    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.addCleanup(cfg.CONF.reset)


class TestCase(base.BaseTestCase):
    """Test case base class for all unit tests."""

    def setUp(self):
        super(TestCase, self).setUp()
        token_info = {
            'token': {
                'project': {
                    'id': 'fake_project'
                },
                'user': {
                    'id': 'fake_user'
                }
            }
        }
        self.context = magnum_context.RequestContext(
            auth_token_info=token_info,
            project_id='fake_project',
            user_id='fake_user')

        self.policy = self.useFixture(policy_fixture.PolicyFixture())

        def make_context(*args, **kwargs):
            # If context hasn't been constructed with token_info
            if not kwargs.get('auth_token_info'):
                kwargs['auth_token_info'] = copy.deepcopy(token_info)
            if not kwargs.get('project_id'):
                kwargs['project_id'] = 'fake_project'
            if not kwargs.get('user_id'):
                kwargs['user_id'] = 'fake_user'

            context = magnum_context.RequestContext(*args, **kwargs)
            return magnum_context.RequestContext.from_dict(context.to_dict())

        p = mock.patch.object(magnum_context, 'make_context',
                              side_effect=make_context)
        self.mock_make_context = p.start()
        self.addCleanup(p.stop)

        self.useFixture(conf_fixture.ConfFixture())

        self._base_test_obj_backup = copy.copy(
            objects_base.MagnumObjectRegistry._registry._obj_classes)
        self.addCleanup(self._restore_obj_registry)

        def reset_pecan():
            pecan.set_config({}, overwrite=True)

        self.addCleanup(reset_pecan)

    def _restore_obj_registry(self):
        objects_base.MagnumObjectRegistry._registry._obj_classes \
            = self._base_test_obj_backup

    def config(self, **kw):
        """Override config options for a test."""
        group = kw.pop('group', None)
        for k, v in kw.items():
            CONF.set_override(k, v, group)

    def get_path(self, project_file=None):
        """Get the absolute path to a file. Used for testing the API.

        :param project_file: File whose path to return. Default: None.
        :returns: path to the specified file, or path to project root.
        """
        root = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            '..',
                                            '..',
                                            )
                               )
        if project_file:
            return os.path.join(root, project_file)
        else:
            return root
