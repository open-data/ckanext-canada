# encoding: utf-8
from typing import Optional

import datetime
import logging

from sqlalchemy import Column, Unicode, DateTime
from sqlalchemy.ext.declarative import declarative_base

from ckan.model import meta

log = logging.getLogger(__name__)


Base = declarative_base(metadata=meta.metadata)


# type_ignore_reason: incomplete typing
class RefData(Base):  # type: ignore
    __tablename__ = 'ref_data'

    table_name = Column(Unicode, primary_key=True)
    last_sync = Column(DateTime, nullable=False,
                       default=datetime.datetime.now(datetime.timezone.utc))
    file_hash = Column(Unicode, nullable=False)

    Session = meta.Session

    @classmethod
    def get(cls, table_name: str, for_update: Optional[bool] = False):
        """
        Returns a ref_data object referenced by its table_name.
        """
        if not table_name:
            return None

        q = cls.Session.query(cls).autoflush(True).filter_by(table_name=table_name)
        if for_update:
            q = q.with_for_update()
        return q.first()

    @classmethod
    def save(cls):
        """
        Adds the current object to the database Session. Requires Session.commit()
        """
        cls.Session.add(cls)

    @classmethod
    def upsert(cls, table_name: str,
               file_hash: str,
               last_sync: Optional[datetime.datetime] = None):
        """
        Sets and returns a ref_data object referenced by its table_name.
        """
        ref_data = cls.get(table_name, for_update=True)

        if ref_data:
            ref_data.file_hash = file_hash
            ref_data.last_sync = last_sync if \
                last_sync else datetime.datetime.now(datetime.timezone.utc)
        else:
            ref_data = cls(table_name=table_name,
                           last_sync=last_sync,
                           file_hash=file_hash)

        cls.Session.add(ref_data)
        cls.Session.commit()

        return cls.get(table_name)

    @classmethod
    def delete(cls, table_name: str):
        """
        Deletes a ref_data object referenced by its table_name.
        """
        ref_data = cls.get(table_name, for_update=True)

        if not ref_data:
            return

        cls.Session.query(cls).filter_by(table_name=table_name).delete()
        cls.Session.commit()


# type_ignore_reason: incomplete typing
class PackageSync(Base):  # type: ignore
    __tablename__ = 'package_sync'

    package_id = Column(Unicode, primary_key=True)
    last_run = Column(DateTime, nullable=False,
                      default=datetime.datetime.now(datetime.timezone.utc))
    last_successful_sync = Column(DateTime, nullable=True)
    error_on = Column(Unicode, nullable=True)
    error = Column(Unicode, nullable=True)

    Session = meta.Session

    @classmethod
    def get(cls, package_id: str, for_update: Optional[bool] = False):
        """
        Returns a package_sync object referenced by its package_id.
        """
        if not package_id:
            return None

        q = cls.Session.query(cls).autoflush(True).filter_by(package_id=package_id)
        if for_update:
            q = q.with_for_update()
        return q.first()

    @classmethod
    def save(cls):
        """
        Adds the current object to the database Session. Requires Session.commit()
        """
        cls.Session.add(cls)

    @classmethod
    def upsert(cls, package_id: str,
               last_successful_sync: Optional[datetime.datetime] = None,
               error_on: Optional[str] = None,
               error: Optional[str] = None):
        """
        Sets and returns a package_sync object referenced by its package_id.
        """
        package_sync = cls.get(package_id, for_update=True)

        if package_sync:
            package_sync.error_on = error_on
            package_sync.error = error
            package_sync.last_run = datetime.datetime.now(datetime.timezone.utc)
            package_sync.last_successful_sync = last_successful_sync if \
                last_successful_sync else package_sync.last_successful_sync
        else:
            package_sync = cls(package_id=package_id,
                               last_successful_sync=last_successful_sync,
                               error_on=error_on, error=error)

        cls.Session.add(package_sync)
        cls.Session.commit()

        return cls.get(package_id)

    @classmethod
    def delete(cls, package_id: str):
        """
        Deletes a pacage_sync object referenced by its package_id.
        """
        package_sync = cls.get(package_id, for_update=True)

        if not package_sync:
            return

        cls.Session.query(cls).filter_by(package_id=package_id).delete()
        cls.Session.commit()
