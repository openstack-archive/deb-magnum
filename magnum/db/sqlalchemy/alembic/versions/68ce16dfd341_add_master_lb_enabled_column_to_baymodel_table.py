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
"""add master_lb_enabled column to baymodel table

Revision ID: 68ce16dfd341
Revises: 085e601a39f6
Create Date: 2016-06-23 18:44:55.312413

"""

# revision identifiers, used by Alembic.
revision = '68ce16dfd341'
down_revision = '085e601a39f6'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('baymodel',
                  sa.Column('master_lb_enabled', sa.Boolean(), default=False))
