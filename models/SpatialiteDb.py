__author__ = 'td27097'

"""
Main db struct
"""

from base import Base
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.types import DateTime

__all__ = ['imagery', 'shapedata']

class Imagery(Base):
    """
    Table for image locations/geodata
    """

    __tablename__ = "imagery"
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, index=True)
    last_access = Column(DateTime)  # Store this for validation
    original_path = Column(String)
    output_path = Column(String)
    matched_to = Column(Integer, ForeignKey('shapedata.id'))  # Store matches for later use
    centroid = Column(String)  # We will store bounding boxes here

class Shapes(Base):
    """
    Table for image locations/geodata
    """

    __tablename__ = "shapedata"
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, index=True)
    last_access = Column(DateTime)  # Store this for validation
    original_path = Column(String)
    output_path = Column(String)
    centroid = Column(String)  # Actual polygon from filesystem

