#
#       Ceilometer to InfluxDB publisher connector
#

import time
import json

# global logging facilities
from oslo_log import log
LOG = log.getLogger(__name__)

# configuration parsing libraries
try:
        from oslo_config import cfg
        from oslo_config import types
        from oslo_utils import netutils as network_utils
except ImportError as e:
        LOG.debug(e)

# openstack ceilometer libraries
try:
        from ceilometer import publisher
        from ceilometer.publisher import utils
except ImportError as e:
        LOG.debug(e)

# import keystone client
from ceilometer.keystone_client import get_client

PortType=types.Integer(1,65535)

# configuration parameters, see ceilometer.conf
config_opts = [
        cfg.StrOpt('influxdb_addr', default='127.0.0.1', help='IP address of the remote InfluxDB instance.', required=True),
        cfg.Opt('influxdb_port', type=PortType, default=8086, help='TCP port of the remote InfluxDB Instance', required=True),
        cfg.StrOpt('influxdb_instance', default='ceilometer_samples', help='Name of the database into which we store samples', required=True),
        cfg.StrOpt('influxdb_user', default='root', help='Username to authenticate with on InfluxDB', required=True),
        cfg.StrOpt('influxdb_pass', default='root', help='Password for the InfluxDB user', required=True),
        cfg.BoolOpt('append_hypervisor', default=False, help='Append hypervisor name to metric id'),
        cfg.StrOpt('metering_prefix', default='mycloud', help='Meter item name prefix'),
        cfg.StrOpt('retention_policy', default=None, help='Retention policy to use when writing points to the database'),
        cfg.StrOpt('mappings', default="/etc/ceilometer/mappings.json", help='File with mapping relationships between meters and influx tags.'),
        cfg.BoolOpt('verboselog', default=False, help='If enabled, print verbose log in ceilometer log files')
]
influxdb_group = cfg.OptGroup(name='influxdb', title='InfluxDB endpoint options')
cfg.CONF.register_group(influxdb_group)

# register global options
cfg.CONF.register_opts(config_opts, group=influxdb_group)

# import HTTP request interface library
try:
        import requests
        from requests.auth import HTTPBasicAuth
except ImportError as e:
        LOG.debug(e)

# for gethostname()
from socket import gethostname
# for match()
import re

# influxdb client
from driver_utils import dbclient
from driver_utils import InfluxDBPublisherUtils
from driver_utils import CeilometerSampleParser as sampleParser

# Publisher Adapter for InfluxDB
# Implements interface ceilometer.publisher.PublisherBase
class InfluxDBPublisher(publisher.PublisherBase):
        # constructor
        def __init__(self, parsed_url):
                self.driver_endpoint_from_pipeline=parsed_url
                # database connection parameters
                self.dbaddress = cfg.CONF.influxdb.influxdb_addr
                self.dbport = cfg.CONF.influxdb.influxdb_port
                self.dbname = cfg.CONF.influxdb.influxdb_instance
                self.dbuser = cfg.CONF.influxdb.influxdb_user
                self.dbpass = cfg.CONF.influxdb.influxdb_pass
                self.retention_policy = cfg.CONF.influxdb.retention_policy
                self.verboselog = cfg.CONF.influxdb.verboselog
                self.mappings = cfg.CONF.influxdb.mappings
                self.mapping_data = {}

                # open mapping file
                with open(self.mappings, "r") as mapping_descriptor:
                    self.mappingfile = json.loads(mapping_descriptor.read())
                    LOG.info("[*] InfluxDB Publisher: Loaded Meters and Tag Mappings from config file [%s]." % self.mappings)

                # parse json...
                for entry in self.mappingfile:
                    self.mapping_data[entry["name"]] = entry["values"]

                # this host
                self.hostname = gethostname()           
                
                # compile additional tags
                self.additional_tags={'hypervisor_hostname': self.hostname, 'retention_policy': self.retention_policy}
                
                # set meter prefix
                if cfg.CONF.influxdb.append_hypervisor:
                        self.meter_prefix=cfg.CONF.influxdb.metering_prefix + self.hostname
                else:
                        self.meter_prefix=cfg.CONF.influxdb.metering_prefix

                # get keystone client instance
                self.identity = get_client()
                
                # get initial tenant list
                self.tenants = self.identity.projects.list()
                
                # at startup, register available tenants in in-memory database
                # subsequent queries either hit the in memory cache or need a new query to keystone
                for t in self.tenants:
                        InfluxDBPublisherUtils.pushTenant(t.id, t.name)

                # create DB connection
                # sanity check on database parameters
                if not (network_utils.is_valid_ipv4(self.dbaddress) and network_utils.is_valid_port(self.dbport)):
                        raise Exception("dbaddr:dbport validation error %s:%s" %(self.dbaddress, self.dbport))
                        
                try:
                        self.dbconn = dbclient(self.dbaddress, self.dbport, self.dbuser, self.dbpass, self.dbname)
                except Exception as e:
                        LOG.info(e)

                # OK init done
                LOG.info("[+] InfluxDB Publisher [%s] registered to [%s]" % (self.driver_endpoint_from_pipeline, self.dbaddress))
        
        # publish samples to timeseries database
        def publish_samples(self, context, samples):
                # parse samples and send to influx
                for sample in samples:
                        # start feeding data into influxdb..
                        with sampleParser(sample, self.meter_prefix, LOG, self.identity, self.mapping_data, self.verboselog) as samplePoint:
                                point = samplePoint.emit()
                                if point is not None:
                                        self.dbconn.write_points([point,], retention_policy=self.retention_policy, tags=self.additional_tags)

        # publish event description to events database
        # Not implemented yet
        def publish_events(self, context, events):
                raise ceilometer.NotImplementedError

