from sqlalchemy import *
import logging
from sqlalchemy.ext.declarative import *
from sqlalchemy.ext.hybrid import hybrid_method
from sqlalchemy.orm import *
from sqlalchemy.sql import and_, or_, not_
import os
import time
from helper_functions import *

# Get directory location for database
path = os.path.dirname(os.path.abspath(__file__))
delim = get_delim()
path = path.split(delim)
path[-2] = 'db'
del path[-1]
directory = delim.join(path) + delim

db_name = 'shakecast_test_db.db'

# logging from DB
#logging.basicConfig(level=logging.DEBUG)
#logging.getLogger('sqlalchemy.engine.base').setLevel(logging.DEBUG)

# SETUP DATABASE
engine = create_engine('sqlite:///%s%s' % (directory, db_name))
connection = engine.connect()


# create a metadata object
metadata = MetaData()

# create a bass class. All mapped class will derive from bass class
Base = declarative_base(metadata=metadata)

#######################################################################
########################## Facility Tables ############################
class Facility(Base):
    __tablename__ = 'facility'
    shakecast_id = Column(Integer, primary_key=True)
    facility_id = Column(Integer)
    facility_type = Column(String(25))
    component = Column(String(100))
    component_class = Column(String(100))
    name = Column(String(255))
    short_name = Column(String(20))
    description = Column(String(255))
    html = Column(String())
    geom_type = Column(String(15))
    lat_min = Column(Float)
    lat_max = Column(Float)
    lon_min = Column(Float)
    lon_max = Column(Float)
    model = Column(String(25))
    grey = Column(Float)
    green = Column(Float)
    yellow = Column(Float)
    orange = Column(Float)
    red = Column(Float)
    grey_beta = Column(Float)
    green_beta = Column(Float)
    yellow_beta = Column(Float)
    orange_beta = Column(Float)
    red_beta = Column(Float)
    grey_metric = Column(String(20))
    green_metric = Column(String(20))
    yellow_metric = Column(String(20))
    orange_metric = Column(String(20))
    red_metric = Column(String(20))
    metric = Column(String(20))
    
    shaking_history = relationship('Facility_Shaking',
                        backref='facility',
                        cascade='save-update, delete, delete-orphan')
    
    def __repr__(self):
        return '''Facility(facility_id=%s,
                           facility_type=%s,
                           name=%s,
                           short_name=%s,
                           description=%s,
                           lat_min=%s,
                           lat_max=%s,
                           lon_min=%s,
                           lon_max=%s,
                           grey=%s,
                           green=%s,
                           yellow=%s,
                           orange=%s,
                           red=%s,
                           grey_beta=%s,
                           green_beta=%s,
                           yellow_beta=%s,
                           orange_beta=%s,
                           red_beta=%s,
                           metric=%s)''' % (self.facility_id,
                                            self.facility_type,
                                            self.name,
                                            self.short_name,
                                            self.description,
                                            self.lat_min,
                                            self.lat_max,
                                            self.lon_min,
                                            self.lon_max,
                                            self.grey,
                                            self.green,
                                            self.yellow,
                                            self.orange,
                                            self.red,
                                            self.grey_beta,
                                            self.green_beta,
                                            self.yellow_beta,
                                            self.orange_beta,
                                            self.red_beta,
                                            self.metric)
    

    def make_alert_level_old(self, shaking_level=0, shakemap=None):
        session = Local_Session()
        
        # check if there is already shaking for this shakemap and facility
        fac_shake = (session.query(Facility_Shaking)
                            .filter(Facility_Shaking.facility == self)
                            .filter(Facility_Shaking.shakemap == shakemap)
                            .all())
        
        # if the query has results, assign them to shaking, otherwise,
        # create a new instance
        if fac_shake:
            fac_shake = fac_shake[0]
        else:
            fac_shake = Facility_Shaking()
            
        # get_exceedence green
        fragility = [{'med': self.red, 'spread': self.red_beta, 'level': 'red'},
                     {'med': self.orange, 'spread': self.orange_beta, 'level': 'orange'},
                     {'med': self.yellow, 'spread': self.yellow_beta, 'level': 'yellow'},
                     {'med': self.green, 'spread': self.green_beta, 'level': 'green'},
                     {'med': self.grey, 'spread': self.grey_beta, 'level': 'grey'}]
        
        prob_sum = 0
        large_prob = 0
        alert_level = 'None'
        for level in fragility:
            
            if level['med'] < 0 or level['spread'] < 0:
                continue
            
            p = lognorm_opt(med=level['med'],
                            spread=level['spread'],
                            shaking=shaking_level)
            
            p -= prob_sum
            prob_sum += p
            
            setattr(fac_shake, level['level'], p)
            
            if p > large_prob:
                large_prob = p
                alert_level = level['level']
            
        fac_shake.facility = self
        fac_shake.shakemap = shakemap
        fac_shake.metric = self.metric
        fac_shake.alert_level = alert_level
        #for notification in notifications:
        #   notification.facility_shaking.append(fac_shake)
        #session.add(fac_shake)
        
        return fac_shake
    
    def make_alert_level(self, shaking_level=0, shakemap=None, notifications=[]):
        db_conn = engine.connect()
        
        # check if there is already shaking for this shakemap and facility
        stmt = (select([Facility_Shaking.__table__.c.shakecast_id])
                        .where(and_(Facility_Shaking.__table__.c.facility_id == self.shakecast_id,
                                    Facility_Shaking.__table__.c.shakemap_id == shakemap.shakecast_id)))
        result = db_conn.execute(stmt)
        fac_shake_id = [row for row in result]
        
        
        fac_shake = {'grey': 0,
                     'green': 0,
                     'yellow': 0,
                     'orange': 0,
                     'red': 0,
                     'metric': None,
                     'facility_id': 0,
                     'shakemap_id': 0,
                     '_shakecast_id': 0,
                     'update': '',
                     'alert_level': '',
                     'notifications': [''] * len(notifications)}
        
        # if the query has results, assign them to shaking, otherwise,
        # create a new instance
        if fac_shake_id:
            #fac_shake = Facility_Shaking()
            fac_shake['update'] = True
            fac_shake['_shakecast_id'] = fac_shake_id[0][0]
        else:
            fac_shake['update'] = False
            fac_shake['_shakecast_id'] = 0
            
        # get_exceedence green
        fragility = [{'med': self.red, 'spread': self.red_beta, 'level': 'red'},
                     {'med': self.orange, 'spread': self.orange_beta, 'level': 'orange'},
                     {'med': self.yellow, 'spread': self.yellow_beta, 'level': 'yellow'},
                     {'med': self.green, 'spread': self.green_beta, 'level': 'green'},
                     {'med': self.grey, 'spread': self.grey_beta, 'level': 'grey'}]
        
        prob_sum = 0
        large_prob = 0
        alert_level = 'None'
        for level in fragility:
            
            if level['med'] < 0 or level['spread'] < 0:
                continue
            
            p = lognorm_opt(med=level['med'],
                            spread=level['spread'],
                            shaking=shaking_level)
            
            p -= prob_sum
            prob_sum += p
            fac_shake[level['level']] = p
            
            if p > large_prob:
                large_prob = p
                alert_level = level['level']
            
        fac_shake['facility_id'] = self.shakecast_id
        fac_shake['metric'] = self.metric
        fac_shake['shakemap_id'] = shakemap.shakecast_id
        fac_shake['alert_level'] = alert_level
        
        not_count = 0
        for notification in notifications:
            if notification.group in self.groups:
                fac_shake['notifications'][not_count] = notification
                not_count += 1
        
        return fac_shake

 
    @hybrid_method    
    def in_grid(self, grid):
        # check if a point is within the boundaries of the grid
        return ((self.lon_min > grid.lon_min and
                    self.lon_min < grid.lon_max and
                    self.lat_min > grid.lat_min and
                    self.lat_min < grid.lat_max) or
                (self.lon_min > grid.lon_min and
                    self.lon_min < grid.lon_max and
                    self.lat_max > grid.lat_min and
                    self.lat_max < grid.lat_max) or 
                (self.lon_max > grid.lon_min and
                    self.lon_max < grid.lon_max and
                    self.lat_min > grid.lat_min and
                    self.lat_min < grid.lat_max) or
                (self.lon_max > grid.lon_min and
                    self.lon_max < grid.lon_max and
                    self.lat_max > grid.lat_min and
                    self.lat_max < grid.lat_max) or
                (self.lon_min < grid.lon_min and
                    self.lon_max > grid.lon_min and
                    self.lat_min < grid.lat_min and
                    self.lat_max > grid.lat_min) or
                (self.lon_min < grid.lon_min and
                    self.lon_max > grid.lon_min and
                    self.lat_min < grid.lat_max and
                    self.lat_max > grid.lat_max) or 
                (self.lon_min < grid.lon_max and
                    self.lon_max > grid.lon_max and
                    self.lat_min < grid.lat_min and
                    self.lat_max > grid.lat_min) or
                (self.lon_min < grid.lon_min and
                    self.lon_max > grid.lon_max and
                    self.lat_min < grid.lat_min and
                    self.lat_max > grid.lat_max))
        
    @in_grid.expression   
    def in_grid(cls, grid):
        # check if a point is within the boundaries of the grid
        return  or_(and_(cls.lon_min > grid.lon_min,
                        cls.lon_min < grid.lon_max,
                        cls.lat_min > grid.lat_min,
                        cls.lat_min < grid.lat_max),
                    and_(cls.lon_min > grid.lon_min,
                        cls.lon_min < grid.lon_max,
                        cls.lat_max > grid.lat_min,
                        cls.lat_max < grid.lat_max),
                    and_(cls.lon_max > grid.lon_min,
                        cls.lon_max < grid.lon_max,
                        cls.lat_min > grid.lat_min,
                        cls.lat_min < grid.lat_max),
                    and_(cls.lon_max > grid.lon_min,
                        cls.lon_max < grid.lon_max,
                        cls.lat_max > grid.lat_min,
                        cls.lat_max < grid.lat_max),
                    and_(cls.lon_min < grid.lon_min,
                        cls.lon_max > grid.lon_min,
                        cls.lat_min < grid.lat_min,
                        cls.lat_max > grid.lat_min),
                    and_(cls.lon_min < grid.lon_min,
                        cls.lon_max > grid.lon_min,
                        cls.lat_min < grid.lat_max,
                        cls.lat_max > grid.lat_max),
                    and_(cls.lon_min < grid.lon_max,
                        cls.lon_max > grid.lon_max,
                        cls.lat_min < grid.lat_min,
                        cls.lat_max > grid.lat_min),
                    and_(cls.lon_min < grid.lon_max,
                        cls.lon_max > grid.lon_max,
                        cls.lat_min < grid.lat_max,
                        cls.lat_max > grid.lat_max))
    
class Facility_Shaking(Base):
    __tablename__ = 'facility_shaking'
    shakecast_id = Column(Integer, primary_key=True)
    shakemap_id = Column(Integer, ForeignKey('shakemap.shakecast_id'))
    facility_id = Column(Integer, ForeignKey('facility.shakecast_id'))
    notification_id = Column(Integer, ForeignKey('notification.shakecast_id'))
    metric = Column(String(20))
    alert_level = Column(String(20))
    weight = Column(Float)
    grey = Column(Float)
    green = Column(Float)
    yellow = Column(Float)
    orange = Column(Float)
    red = Column(Float)
    pga = Column(Float)
    pgv = Column(Float)
    mmi = Column(Float)
    psa03 = Column(Float)
    psa10 = Column(Float)
    psa30 = Column(Float)
    
    def __repr__(self):
        return '''Facility_Shaking(shakemap_id=%s,
                                   facility_id=%s,
                                   notification_id=%s,
                                   metric=%s,
                                   alert_level=%s,
                                   weight=%s,
                                   grey=%s,
                                   green=%s,
                                   yellow=%s,
                                   orange=%s,
                                   red=%s,
                                   pga=%s,
                                   pgv=%s,
                                   mmi=%s,
                                   psa03=%s,
                                   psa10=%s,
                                   psa30=%s)''' % (self.shakemap_id,
                                                   self.facility_id,
                                                   self.notification_id,
                                                   self.metric,
                                                   self.alert_level,
                                                   self.weight,
                                                   self.grey,
                                                   self.green,
                                                   self.yellow,
                                                   self.orange,
                                                   self.red,
                                                   self.pga,
                                                   self.pgv,
                                                   self.mmi,
                                                   self.psa03,
                                                   self.psa10,
                                                   self.psa30)
    
    
#######################################################################
######################## Notification Tables ##########################

class Notification(Base):
    __tablename__ = 'notification'
    shakecast_id = Column(Integer, primary_key=True)
    shakemap_id = Column(Integer, ForeignKey('shakemap.shakecast_id'))
    group_name = Column(String(25), ForeignKey('group.name'))
    notification_type = Column(String(25))
    status = Column(String(15))
    notification_file = Column(String(255))
    
    facility_shaking = relationship('Facility_Shaking',
                                    secondary='shaking_notification_connection',
                                    backref='notifications')
    
    def __rept__(self):
        return '''Notification(shakemap_id=%s,
                               self.group_name=%s,
                               self.notification_type=%s,
                               self.status=%s,
                               self.notification_file)''' % (self.shakemap_id,
                                                             self.group_name,
                                                             self.notification_type,
                                                             self.status,
                                                             self.notification_file)
    
    
    
class User(Base):
    __tablename__ = 'user'
    shakecast_id = Column(Integer, primary_key=True)
    username = Column(String(32))
    password = Column(String(64))
    email = Column(String(255))
    phone_number = Column(String(25))
    full_name = Column(String(32))
    user_type = Column(String(10))
    
    groups = relationship('Group',
                          secondary='user_group_connection',
                          backref='users')
    
    def __repr__(self):
        return '''User(username=%s,
                       password=%s,
                       email=%s,
                       phone_number=%s,
                       full_name=%s,
                       user_type=%s)''' % (self.username,
                                           self.password,
                                           self.email,
                                           self.phone_number,
                                           self.full_name,
                                           self.user_type)
    
  
    
class Group(Base):
    __tablename__ = 'group'
    shakecast_id = Column(Integer, primary_key=True)
    name = Column(String(25))
    facility_type = Column(String(25))
    lon_min = Column(Integer)
    lon_max = Column(Integer)
    lat_min = Column(Integer)
    lat_max = Column(Integer)
    
    facilities = relationship('Facility',
                              secondary='facility_group_connection',
                              backref='groups')
    
    past_notifications = relationship('Notification',
                                      backref='group',
                                      cascade='save-update, delete')
    
    specs = relationship('Group_Specification',
                                  backref='group',
                                  cascade='save-update, delete, delete-orphan')
    
    def __repr__(self):
        return '''Group(name=%s,
                        facility_type=%s,
                        lon_min=%s,
                        lon_max=%s,
                        lat_min=%s,
                        lat_max=%s)''' % (self.name,
                                          self.facility_type,
                                          self.lon_min,
                                          self.lon_max,
                                          self.lat_min,
                                          self.lat_max)
    
    @hybrid_method    
    def in_grid(self, grid):
        # check if a point is within the boundaries of the grid
        return ((self.lon_min > grid.lon_min and
                    self.lon_min < grid.lon_max and
                    self.lat_min > grid.lat_min and
                    self.lat_min < grid.lat_max) or
                (self.lon_min > grid.lon_min and
                    self.lon_min < grid.lon_max and
                    self.lat_max > grid.lat_min and
                    self.lat_max < grid.lat_max) or 
                (self.lon_max > grid.lon_min and
                    self.lon_max < grid.lon_max and
                    self.lat_min > grid.lat_min and
                    self.lat_min < grid.lat_max) or
                (self.lon_max > grid.lon_min and
                    self.lon_max < grid.lon_max and
                    self.lat_max > grid.lat_min and
                    self.lat_max < grid.lat_max) or
                (self.lon_min < grid.lon_min and
                    self.lon_max > grid.lon_min and
                    self.lat_min < grid.lat_min and
                    self.lat_max > grid.lat_min) or
                (self.lon_min < grid.lon_min and
                    self.lon_max > grid.lon_min and
                    self.lat_min < grid.lat_max and
                    self.lat_max > grid.lat_max) or 
                (self.lon_min < grid.lon_max and
                    self.lon_max > grid.lon_max and
                    self.lat_min < grid.lat_min and
                    self.lat_max > grid.lat_min) or
                (self.lon_min < grid.lon_min and
                    self.lon_max > grid.lon_max and
                    self.lat_min < grid.lat_min and
                    self.lat_max > grid.lat_max))
        
    @in_grid.expression   
    def in_grid(cls, grid):
        # check if a point is within the boundaries of the grid
        return  or_(and_(cls.lon_min > grid.lon_min,
                        cls.lon_min < grid.lon_max,
                        cls.lat_min > grid.lat_min,
                        cls.lat_min < grid.lat_max),
                    and_(cls.lon_min > grid.lon_min,
                        cls.lon_min < grid.lon_max,
                        cls.lat_max > grid.lat_min,
                        cls.lat_max < grid.lat_max),
                    and_(cls.lon_max > grid.lon_min,
                        cls.lon_max < grid.lon_max,
                        cls.lat_min > grid.lat_min,
                        cls.lat_min < grid.lat_max),
                    and_(cls.lon_max > grid.lon_min,
                        cls.lon_max < grid.lon_max,
                        cls.lat_max > grid.lat_min,
                        cls.lat_max < grid.lat_max),
                    and_(cls.lon_min < grid.lon_min,
                        cls.lon_max > grid.lon_min,
                        cls.lat_min < grid.lat_min,
                        cls.lat_max > grid.lat_min),
                    and_(cls.lon_min < grid.lon_min,
                        cls.lon_max > grid.lon_min,
                        cls.lat_min < grid.lat_max,
                        cls.lat_max > grid.lat_max),
                    and_(cls.lon_min < grid.lon_max,
                        cls.lon_max > grid.lon_max,
                        cls.lat_min < grid.lat_min,
                        cls.lat_max > grid.lat_min),
                    and_(cls.lon_min < grid.lon_max,
                        cls.lon_max > grid.lon_max,
                        cls.lat_min < grid.lat_max,
                        cls.lat_max > grid.lat_max))
    
    
    @hybrid_method    
    def has_spec(self, not_type='', min_mag=0):
        specs = [s.notification_type for s in self.specs]
        if not_type in specs:
            return True
        else:
            return False
        
    @has_spec.expression   
    def has_spec(cls, not_type='', min_mag=0):
        specs = [s.notification_type for s in cls.specs]
        if not_type in specs:
            return 1 == 1
        else:
            return 0 == 1
        
class Group_Specification(Base):
    __tablename__ = 'group_specification'
    shakecast_id = Column(Integer, primary_key=True)
    group_id = Column(String(25), ForeignKey('group.shakecast_id'))
    notification_type = Column(String(25))
    inspection_priority = Column(String(10))
    minimum_magnitude = Column(Integer)
    notification_format = Column(String(25))
    aggregate_name = Column(String(25))
    template = Column(String(255))
    
    def __repr__(self):
        return '''Group_Specification(group_id=%s,
                                      notification_type=%s,
                                      inspection_priority=%s,
                                      minimum_magnitude=%s,
                                      notification_format=%s,
                                      aggregate_name=%s,
                                      template=%s)''' % (self.group_id,
                                                         self.notification_type,
                                                         self.inspection_priority,
                                                         self.minimum_magnitude,
                                                         self.notification_format,
                                                         self.aggregate_name,
                                                         self.template)
    

# Connection tables
user_group_connection = Table('user_group_connection', Base.metadata,
    Column('user',
           Integer,
           ForeignKey('user.shakecast_id',
                      ondelete='cascade'),
           primary_key=True),
    Column('group',
           Integer,
           ForeignKey('group.shakecast_id',
                      ondelete='cascade'),
           primary_key=True)
)

facility_group_connection = Table('facility_group_connection', Base.metadata,
    Column('facility',
           Integer, ForeignKey('facility.shakecast_id',
                               ondelete='cascade'),
           primary_key=True),
    Column('group',
           Integer,
           ForeignKey('group.shakecast_id',
                      ondelete='cascade'),
           primary_key=True)
)

shaking_notification_connection = Table('shaking_notification_connection', Base.metadata,
    Column('facility_shaking',
           Integer,
           ForeignKey('facility_shaking.shakecast_id',
                      ondelete='cascade'),
           primary_key=True),
    Column('notification',
           Integer,
           ForeignKey('notification.shakecast_id',
                      ondelete='cascade'),
           primary_key=True)
)

user_notification_connection = Table('user_notification_connection', Base.metadata,
    Column('user',
           Integer,
           ForeignKey('user.shakecast_id',
                      ondelete='cascade'),
           primary_key=True),
    Column('notification',
           Integer,
           ForeignKey('notification.shakecast_id',
                      ondelete='cascade'),
           primary_key=True)
)

#######################################################################
########################## ShakeMap Tables ############################

class ShakeMap(Base):
    __tablename__ = 'shakemap'
    shakecast_id = Column(Integer, primary_key=True)
    shakemap_id = Column(String(80))
    shakemap_version = Column(Integer)
    status = Column(String(10))
    map_status = Column(String(10))
    event_id = Column(String(80))
    event_version = Column(Integer)
    generating_server = Column(Integer)
    region = Column(String(2))
    lat_min = Column(Float)
    lat_max = Column(Float)
    lon_min = Column(Float)
    lon_max = Column(Float)
    generation_timestamp = Column(String(32))
    recieve_timestamp = Column(String(32))
    begin_timestamp = Column(String(20))
    end_timestamp = Column(String(20))
    superceded_timestamp = Column(String(20))
    directory_name = Column(String(255))
    
    products = relationship('Product',
                        backref='shakemap',
                        cascade='save-update, delete')
    
    notifications = relationship('Notification',
                                 backref = 'shakemap')

    facility_shaking = relationship('Facility_Shaking',
                                    backref='shakemap',
                                    cascade='save-update, delete')
    
    def __repr__(self):
        return '''ShakeMap(shakemap_id=%s,
                           status=%s,
                           map_status=%s,
                           event_id=%s,
                           event_version=%s,
                           generating_server=%s,
                           region=%s,
                           lat_min=%s,
                           lat_max=%s,
                           lon_min=%s,
                           lon_max=%s,
                           generation_timestamp=%s,
                           recieve_timestamp=%s,
                           begin_timestamp=%s,
                           end_timestamp=%s,
                           superceded_timestamp=%s,
                           directory_name=%s)''' % (self.shakemap_id,
                                                 self.status,
                                                 self.map_status,
                                                 self.event_id,
                                                 self.event_version,
                                                 self.generating_server,
                                                 self.region,
                                                 self.lat_min,
                                                 self.lat_max,
                                                 self.lon_min,
                                                 self.lon_max,
                                                 self.generation_timestamp,
                                                 self.recieve_timestamp,
                                                 self.begin_timestamp,
                                                 self.end_timestamp,
                                                 self.superceded_timestamp,
                                                 self.directory_name)
    
    
    @hybrid_method    
    def is_new(self):
        db_conn = engine.connect()
        
        stmt = (select([ShakeMap.__table__.c.shakecast_id])
                    .where(and_(ShakeMap.__table__.c.shakemap_id == self.shakemap_id,
                                ShakeMap.__table__.c.shakemap_version == self.shakemap_version)))
        
        result = db_conn.execute(stmt)
        shakemaps = [row for row in result]
        
        if shakemaps:
            return False
        else:
            return True
        
    @hybrid_method    
    def has_products(self, req_prods):
        shakemap_prods = [prod.product_type for prod in self.products]
        for prod in req_prods:
            if prod not in shakemap_prods:
                return False
        return True
    
    
class Product(Base):
    __tablename__ = 'product'
    shakecast_id = Column(Integer, primary_key=True)
    shakemap_id = Column(Integer,
                         ForeignKey('shakemap.shakecast_id'))
    #shakemap_version = Column(Integer, ForeignKey('shakemap.version'), primary_key=True)
    product_type = Column(String(10))
    name = Column(String(32))
    description = Column(String(255))
    metric = Column(String(10))
    filename = Column(String(32))
    url = Column(String(255))
    display = Column(Integer)
    source = Column(String(64))
    update_username = Column(String(32))
    update_timestamp = Column(String(32))
    
    def __repr__(self):
        return '''Product(product_type=%s,
                          name=%s,
                          description=%s,
                          metric=%s,
                          url=%s,
                          display=%s,
                          source=%s,
                          update_username=%s,
                          update_timestamp=%s)''' % (self.product_type,
                                                     self.name,
                                                     self.description,
                                                     self.metric,
                                                     self.url,
                                                     self.display,
                                                     self.source,
                                                     self.update_username,
                                                     self.update_timestamp)
    
    
    
#######################################################################

# create database schema that doesn't exist
db_sql = metadata.create_all(engine)

#with open('db.txt', 'w') as f:
#    f.write(db_sql)

# In SQLalchemy we always work with RELATED objects
# all the objects we're working with are stored in a session
Session = sessionmaker(bind=engine)
    
