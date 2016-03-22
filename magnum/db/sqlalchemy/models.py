# Copyright 2013 Hewlett-Packard Development Company, L.P.
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

"""
SQLAlchemy models for container service
"""

import json

from oslo_config import cfg
from oslo_db.sqlalchemy import models
import six.moves.urllib.parse as urlparse
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Integer
from sqlalchemy import schema
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator, TEXT


def table_args():
    engine_name = urlparse.urlparse(cfg.CONF.database.connection).scheme
    if engine_name == 'mysql':
        return {'mysql_engine': cfg.CONF.database.mysql_engine,
                'mysql_charset': "utf8"}
    return None


class JsonEncodedType(TypeDecorator):
    """Abstract base type serialized as json-encoded string in db."""
    type = None
    impl = TEXT

    def process_bind_param(self, value, dialect):
        if value is None:
            # Save default value according to current type to keep the
            # interface the consistent.
            value = self.type()
        elif not isinstance(value, self.type):
            raise TypeError("%s supposes to store %s objects, but %s given"
                            % (self.__class__.__name__,
                               self.type.__name__,
                               type(value).__name__))
        serialized_value = json.dumps(value)
        return serialized_value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class JSONEncodedDict(JsonEncodedType):
    """Represents dict serialized as json-encoded string in db."""
    type = dict


class JSONEncodedList(JsonEncodedType):
    """Represents list serialized as json-encoded string in db."""
    type = list


class MagnumBase(models.TimestampMixin,
                 models.ModelBase):

    metadata = None

    def as_dict(self):
        d = {}
        for c in self.__table__.columns:
            d[c.name] = self[c.name]
        return d

    def save(self, session=None):
        import magnum.db.sqlalchemy.api as db_api

        if session is None:
            session = db_api.get_session()

        super(MagnumBase, self).save(session)

Base = declarative_base(cls=MagnumBase)


class Bay(Base):
    """Represents a bay."""

    __tablename__ = 'bay'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_bay0uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    project_id = Column(String(255))
    user_id = Column(String(255))
    uuid = Column(String(36))
    name = Column(String(255))
    baymodel_id = Column(String(255))
    stack_id = Column(String(255))
    api_address = Column(String(255))
    node_addresses = Column(JSONEncodedList)
    node_count = Column(Integer())
    master_count = Column(Integer())
    status = Column(String(20))
    status_reason = Column(Text)
    bay_create_timeout = Column(Integer())
    discovery_url = Column(String(255))
    master_addresses = Column(JSONEncodedList)
    # TODO(wanghua): encrypt trust_id in db
    trust_id = Column(String(255))
    trustee_username = Column(String(255))
    trustee_user_id = Column(String(255))
    # TODO(wanghua): encrypt trustee_password in db
    trustee_password = Column(String(255))
    # (yuanying) if we use barbican,
    # cert_ref size is determined by below format
    # * http(s)://${DOMAIN_NAME}/v1/containers/${UUID}
    # as a result, cert_ref length is estimated to 312 chars.
    # but we can use another backend to store certs.
    # so, we use 512 chars to get some buffer.
    ca_cert_ref = Column(String(512))
    magnum_cert_ref = Column(String(512))


class BayModel(Base):
    """Represents a bay model."""

    __tablename__ = 'baymodel'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_baymodel0uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    project_id = Column(String(255))
    user_id = Column(String(255))
    name = Column(String(255))
    image_id = Column(String(255))
    flavor_id = Column(String(255))
    master_flavor_id = Column(String(255))
    keypair_id = Column(String(255))
    external_network_id = Column(String(255))
    fixed_network = Column(String(255))
    network_driver = Column(String(255))
    volume_driver = Column(String(255))
    dns_nameserver = Column(String(255))
    apiserver_port = Column(Integer())
    docker_volume_size = Column(Integer())
    cluster_distro = Column(String(255))
    coe = Column(String(255))
    http_proxy = Column(String(255))
    https_proxy = Column(String(255))
    no_proxy = Column(String(255))
    registry_enabled = Column(Boolean, default=False)
    labels = Column(JSONEncodedDict)
    tls_disabled = Column(Boolean, default=False)
    public = Column(Boolean, default=False)
    server_type = Column(String(255))


class Container(Base):
    """Represents a container."""

    __tablename__ = 'container'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_container0uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    project_id = Column(String(255))
    user_id = Column(String(255))
    uuid = Column(String(36))
    name = Column(String(255))
    image = Column(String(255))
    command = Column(String(255))
    bay_uuid = Column(String(36))
    status = Column(String(20))
    memory = Column(String(255))
    environment = Column(JSONEncodedDict)


class Pod(Base):
    """Represents a pod."""

    __tablename__ = 'pod'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_pod0uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    name = Column(String(255))
    desc = Column(String(255))
    bay_uuid = Column(String(36))
    images = Column(JSONEncodedList)
    labels = Column(JSONEncodedDict)
    status = Column(String(255))
    project_id = Column(String(255))
    user_id = Column(String(255))
    host = Column(String(255))


class Service(Base):
    """Represents a software service."""

    __tablename__ = 'service'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_service0uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    name = Column(String(255))
    bay_uuid = Column(String(36))
    labels = Column(JSONEncodedDict)
    selector = Column(JSONEncodedDict)
    ip = Column(String(36))
    ports = Column(JSONEncodedList)
    project_id = Column(String(255))
    user_id = Column(String(255))


class ReplicationController(Base):
    """Represents a pod replication controller."""

    __tablename__ = 'replicationcontroller'
    __table_args__ = (
        schema.UniqueConstraint('uuid',
                                name='uniq_replicationcontroller0uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    name = Column(String(255))
    bay_uuid = Column(String(36))
    images = Column(JSONEncodedList)
    labels = Column(JSONEncodedDict)
    replicas = Column(Integer())
    project_id = Column(String(255))
    user_id = Column(String(255))


class X509KeyPair(Base):
    """X509KeyPair"""
    __tablename__ = 'x509keypair'
    __table_args__ = (
        schema.UniqueConstraint('uuid',
                                name='uniq_x509keypair0uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    name = Column(String(255))
    bay_uuid = Column(String(36))
    ca_cert = Column(Text())
    certificate = Column(Text())
    private_key = Column(Text())
    project_id = Column(String(255))
    user_id = Column(String(255))


class MagnumService(Base):
    """Represents health status of various magnum services"""
    __tablename__ = 'magnum_service'
    __table_args__ = (
        schema.UniqueConstraint("host", "binary",
                                name="uniq_magnum_service0host0binary"),
        table_args()
    )

    id = Column(Integer, primary_key=True)
    host = Column(String(255))
    binary = Column(String(255))
    disabled = Column(Boolean, default=False)
    disabled_reason = Column(String(255))
    last_seen_up = Column(DateTime, nullable=True)
    forced_down = Column(Boolean, default=False)
    report_count = Column(Integer, nullable=False, default=0)


class Quota(Base):
    """Represents Quota for a resource within a project"""
    __tablename__ = 'quotas'
    __table_args__ = (
        schema.UniqueConstraint(
            "project_id", "resource",
            name='uniq_quotas0project_id0resource'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    project_id = Column(String(255))
    resource = Column(String(255))
    hard_limit = Column(Integer())
