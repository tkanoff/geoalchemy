from unittest import TestCase
from sqlalchemy import (create_engine, MetaData, Column, Integer, String,
        func, literal, select)
from sqlalchemy.orm import sessionmaker, column_property
from sqlalchemy.ext.declarative import declarative_base

from geoalchemy.postgis import (Geometry, GeometryColumn, GeometryDDL,
	WKTSpatialElement)

engine = create_engine('postgres://gis:gis@localhost/gis', echo=True)
metadata = MetaData(engine)
session = sessionmaker(bind=engine)()
Base = declarative_base(metadata=metadata)

class Road(Base):
    __tablename__ = 'roads'

    road_id = Column(Integer, primary_key=True)
    road_name = Column(String)
    road_geom = GeometryColumn(Geometry(2))

class Lake(Base):
    __tablename__ = 'lakes'

    lake_id = Column(Integer, primary_key=True)
    lake_name = Column(String)
    lake_geom = GeometryColumn(Geometry(2))

# enable the DDL extension, which allows CREATE/DROP operations
# to work correctly.  This is not needed if working with externally
# defined tables.    
GeometryDDL(Road.__table__)
GeometryDDL(Lake.__table__)

class TestGeometry(TestCase):

    def setUp(self):

        metadata.drop_all()
        metadata.create_all()

        # Add objects.  We can use strings...
        session.add_all([
            Road(road_name='Jeff Rd', road_geom='SRID=-1;LINESTRING(191232 243118,191108 243242)'),
            Road(road_name='Geordie Rd', road_geom='SRID=-1;LINESTRING(189141 244158,189265 244817)'),
            Road(road_name='Paul St', road_geom='SRID=-1;LINESTRING(192783 228138,192612 229814)'),
            Road(road_name='Graeme Ave', road_geom='SRID=-1;LINESTRING(189412 252431,189631 259122)'),
            Road(road_name='Phil Tce', road_geom='SRID=-1;LINESTRING(190131 224148,190871 228134)'),
            Lake(lake_name='My Lake', lake_geom='SRID=-1;POLYGON((0 0,4 0,4 4,0 4,0 0))'),
        ])

        # or use an explicit WKTSpatialElement (similar to saying func.GeomFromText())
        self.r = Road(road_name='Dave Cres', road_geom=WKTSpatialElement('SRID=-1;LINESTRING(198231 263418,198213 268322)', -1))
        session.add(self.r)

    def tearDown(self):
        session.rollback()
        metadata.drop_all()

    def test_geom(self):
        assert str(self.r.road_geom) == 'SRID=-1;LINESTRING(198231 263418,198213 268322)'

    def test_wkt_element(self):
        assert session.scalar(self.r.road_geom.wkt) == 'LINESTRING(198231 263418,198213 268322)'

    def test_persistent_element(self):
        session.commit()
        assert str(self.r.road_geom) == "01020000000200000000000000B832084100000000E813104100000000283208410000000088601041"

    def test_eq(self):
        r1 = session.query(Road).filter(Road.road_name=='Graeme Ave').one()
        r2 = session.query(Road).filter(Road.road_geom == 'LINESTRING(189412 252431,189631 259122)').one()
        r3 = session.query(Road).filter(Road.road_geom == r1.road_geom).one()
        assert r1 is r2 is r3

    def test_intersects(self):
        r1 = session.query(Road).filter(Road.road_name=='Graeme Ave').one()
        assert [(r.road_name, session.scalar(r.road_geom.wkt)) for r in session.query(Road).filter(Road.road_geom.intersects(r1.road_geom)).all()] == [('Graeme Ave', 'LINESTRING(189412 252431,189631 259122)')]

    def test_wkt(self):
        r = session.query(Road).filter(Road.road_name=='Graeme Ave').one()
        assert session.scalar(r.road_geom.wkt) == 'LINESTRING(189412 252431,189631 259122)'

    def test_length(self):
        r = session.query(Road).filter(Road.road_name=='Graeme Ave').one()
        assert session.scalar(r.road_geom.length) == 6694.5830340656803

    def test_area(self):
        l = session.query(Lake).filter(Lake.lake_name=='My Lake').one()
        assert session.scalar(l.lake_geom.area) == 16

    def test_centroid(self):
        r = session.query(Road).filter(Road.road_name=='Graeme Ave').one()
        l = session.query(Lake).filter(Lake.lake_name=='My Lake').one()
        assert session.scalar(r.road_geom.centroid) == '0101000000000000008C2207410000000004390F41'
        assert session.scalar(l.lake_geom.centroid) == '010100000000000000000000400000000000000040'

    def test_boundary(self):
        r = session.query(Road).filter(Road.road_name=='Graeme Ave').one()
        assert session.scalar(r.road_geom.boundary) == '010400000002000000010100000000000000201F07410000000078D00E41010100000000000000F82507410000000090A10F41'
