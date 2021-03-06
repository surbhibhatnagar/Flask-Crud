import sys
from sqlalchemy import create_engine, Column, ForeignKey, Integer, String, \
    DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref

Base = declarative_base()
class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key = True)
    name = Column(String(50), nullable = False)
    email = Column(String(100), nullable = False)

    @property
    def serialize(self):
        """Return object data in serializeable format fro JSON endpoints"""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
        }

class Category(Base):
    __tablename__ = 'category'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    @property
    def serialize(self):
        """Return object data in serializeable format for JSON endpoints"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'user_id' : self.user_id,
        }


class Item(Base):
    __tablename__ = 'item'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=False)
    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship(Category, backref=backref('item', cascade='all,'
                                                                      'delete'))
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    @property
    def serialize(self):
        """Return object data in serializeable format fro JSON endpoints"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category_id': self.category_id,
            'user_id' : self.user_id,
        }


engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.create_all(engine)
