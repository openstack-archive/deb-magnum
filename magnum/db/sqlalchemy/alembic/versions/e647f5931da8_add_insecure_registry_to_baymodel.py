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
"""add insecure_registry to baymodel

Revision ID: e647f5931da8
Revises: 049f81f6f584
Create Date: 2016-03-28 09:08:07.467102

"""

# revision identifiers, used by Alembic.
revision = 'e647f5931da8'
down_revision = '049f81f6f584'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('baymodel', sa.Column('insecure_registry',
                                        sa.String(length=255), nullable=True))
