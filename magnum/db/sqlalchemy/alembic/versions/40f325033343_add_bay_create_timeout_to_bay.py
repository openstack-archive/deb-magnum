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

"""add bay_create_timeout to bay

Revision ID: 40f325033343
Revises: 5977879072a7
Create Date: 2015-12-02 16:38:54.697413

"""

# revision identifiers, used by Alembic.
revision = '40f325033343'
down_revision = '5977879072a7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('bay', sa.Column('bay_create_timeout',
                  sa.Integer(), nullable=True))
