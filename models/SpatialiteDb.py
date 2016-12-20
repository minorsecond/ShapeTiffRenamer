__author__ = 'td27097'

"""
Main db struct
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, create_engine, MetaData
from sqlalchemy.types import DateTime
from ShapeTiffRenamer import DatabaseIo
import geoalchemy

# Set the DB path
db_io = DatabaseIo()
db_path = db_io.get_db_path()

# init the db
engine = create_engine('sqlite:///.{}'.format(db_path))
metadata = MetaData(engine)
Base = declarative_base()

__all__ = ['imagery', 'shapedata']

class Imagery(Base):
    """
    Table for image locations/geodata
    """

    __tablename__ = "imagery"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)  # Store this for validation
    path = Column(String)
    matched_to = Column(Integer, ForeignKey('shapedata.id'))  # Store matches for later use
    geom = geoalchemy.GeometryColumn(geoalchemy.Polygon(2))  # We will store bounding boxes here

class Shapes(Base):
    """
    Table for image locations/geodata
    """

    __tablename__ = "shapedata"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)  # Store this for validation
    path = Column(String)
    geom = geoalchemy.GeometryColumn(geoalchemy.Polygon(2))  # Actual polygon from filesystem

geoalchemy.GeometryDDL(Imagery.__table__)
geoalchemy.GeometryDDL(Shapes.__table__)
