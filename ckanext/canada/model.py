# encoding: utf-8

import datetime
import logging

from sqlalchemy import Column, Unicode, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base

from ckan.model import meta

log = logging.getLogger(__name__)


Base = declarative_base(metadata=meta.metadata)


class PackageSync(Base):
    __tablename__ = 'package_sync'

    id = Column(Integer, primary_key=True, autoincrement=True)
    package_id = Column(Unicode)
    created = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    last_successful_sync = Column(DateTime, nullable=True)
    error_on = Column(Unicode, nullable=True)
    error = Column(Unicode, nullable=True)

    @classmethod
    def get(cls, package_id, for_update=False):
        '''Returns a package_sync object referenced by its package_id.'''
        if not package_id:
            return None

        q = meta.Session.query(cls).autoflush(True).filter_by(package_id=package_id)
        if for_update:
            q = q.with_for_update()
        return q.first()


    @classmethod
    def upsert(cls, package_id, last_successful_sync=None, error_on=None, error=None):
        '''Sets and returns a package_sync object referenced by its package_id.'''
        package_sync = cls.get(package_id, for_update=True)

        if package_sync:
            package_sync.error_on = error_on
            package_sync.error = error
            package_sync.created = datetime.datetime.now(datetime.timezone.utc)
            package_sync.last_successful_sync = last_successful_sync
        else:
            package_sync = cls(package_id=package_id, last_successful_sync=last_successful_sync,
                               error_on=error_on, error=error)

        meta.Session.add(package_sync)
        meta.Session.commit()

        return cls.get(package_id)


    @classmethod
    def delete(cls, package_id):
        '''Deletes a pacage_sync object referenced by its package_id.'''
        package_sync = cls.get(package_id, for_update=True)

        if not package_sync:
            return

        meta.Session.query(cls).filter_by(package_id=package_id).delete()
        meta.Session.commit()


def _get_models():
    return [PackageSync]


def create_tables(models=_get_models()):
    for model in models:
        model.__table__.create()

        log.info('%s database table created' % model.__tablename__)


def tables_no_exist():
    return [model for model in _get_models() if not model.__table__.exists()]


def tables_exist():
    return [model for model in _get_models() if model.__table__.exists()]
