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
    sha256 = Column(Unicode, nullable=False)

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
               sha256: str,
               last_sync: Optional[datetime.datetime] = None):
        """
        Sets and returns a ref_data object referenced by its table_name.
        """
        ref_data = cls.get(table_name, for_update=True)

        if ref_data:
            ref_data.sha256 = sha256
            ref_data.last_sync = last_sync if \
                last_sync else datetime.datetime.now(datetime.timezone.utc)
        else:
            ref_data = cls(table_name=table_name,
                           last_sync=last_sync,
                           sha256=sha256)

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
