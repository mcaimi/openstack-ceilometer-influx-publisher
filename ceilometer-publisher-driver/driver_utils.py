#!/bin/env python
#
#       Ceilometer to InfluxDB publisher utils and sample parsers
#

from ceilometer.publisher.dbdriver import InfluxDBClient as dbclient
from socket import gethostname

# global logging facilities
from oslo_log import log
LOG = log.getLogger(__name__)

# utility classes
class InfluxDBPublisherUtils():
    #static tenant in-memory dict
    all_tenants = {}

    @staticmethod
    def pushTenant(tenant_id, tenant_name):
        if not InfluxDBPublisherUtils.all_tenants.has_key(tenant_id):
            InfluxDBPublisherUtils.all_tenants[tenant_id]=tenant_name

    @staticmethod
    def getTenantName(tenant_id):
        if InfluxDBPublisherUtils.all_tenants.has_key(tenant_id):
            return InfluxDBPublisherUtils.all_tenants[tenant_id]
        else:
            return None

# parser class
class CeilometerSampleParser():
    # entry_point
    # context manager method
    def __enter__(self):
        #self.logger.info("[*] Parser Object Created")
        return self

    # constructor
    def __init__(self, sample, meter_prefix, log, keystone_client, mapping_data=None, logging=False):
        self.logger = log
        self.meter_prefix = meter_prefix
        # unpack sample data into a dictionary
        self.current_sample = sample
        self.sample_dict = self.current_sample.as_dict()
        self.hostname = gethostname()
        self.identity = keystone_client
        self.verboselog = logging
        self.mappings = mapping_data

        if self.verboselog:
            self.logger.info(self.sample_dict)

    # parse current sample.
    # since different samples have different attributes, this parser dynamically adds tags to sample
    # data based on the fields of the JSON payload retrieved from the ceilometer API
    def parseSample(self):
        # check if this sample belong to a meter we want to send to influx.
        if self.sample_dict['name'] in self.mappings['meters']:

            # dynamically add fields to sample dict
            self.converted_sample = {} # tags to add to sample data

            # parse JSON payload and fill inner tags dictionary
            for k in self.sample_dict.keys():
                if self.sample_dict[k].__class__ == dict: # handle nested dicts
                    for inner_k in self.sample_dict[k].keys():
                        self.converted_sample[inner_k] = self.sample_dict[k][inner_k]
                else:
                    self.converted_sample[k] = self.sample_dict[k]

            # check wether we already have a tenant-name/tenant-id relation resolved
            # otherwise ask keystone :)
            if self.converted_sample.has_key('project_id'):
                self.converted_sample['tenant_name'] = InfluxDBPublisherUtils.getTenantName(self.converted_sample['project_id'])
                # check...
                if self.converted_sample['tenant_name'] is None:
                    # unknown tenant. ask keystone
                    missing_tenant = self.identity.projects.get(self.converted_sample['project_id'])
                    # add tag
                    self.converted_sample['tenant_name'] = missing_tenant.name
                    # push tenant in in memory db
                    InfluxDBPublisherUtils.pushTenant(missing_tenant.id, missing_tenant.name)

            # build sample dictionary
            self.tags = {}
            self.fields = {}

            # check if we have a sample coming from an allowed tenant
            if (("*" in self.mappings['tenants']) or (self.converted_sample['tenant_name'] in self.mappings['tenants'])):
                # common tags...
                for ctag in self.mappings['common_tags']:
                    self.tags[ctag] = self.converted_sample[ctag]

                # special tags..
                for stag in self.mappings['special_tags']:
                    if self.converted_sample.has_key(stag):
                        self.tags[stag] = self.converted_sample[stag]

                # fill fields..
                for field in self.converted_sample.keys():
                    if not(field in (['flavor', 'image'] + self.mappings['common_tags'] + self.mappings['special_tags'])):
                        # we do not want to lose data. serialize dictionaries and store them in a field key
                        self.fields[field] = str(self.converted_sample[field])

                # add value...
                self.fields['value'] = float(self.converted_sample['volume'])

                if self.verboselog:
                    LOG.info("[*] self.fields=%s" % self.fields)

                self.timestamp = str(self.converted_sample['timestamp']).strip()

                self.samplePoint = {
                                "time": self.timestamp,
                                "measurement": self.meter_prefix + self.sample_dict['name'],
                                "fields": self.fields,
                                "tags": self.tags,
                }
            else:
                if self.verboselog:
                    LOG.info("[*] Sample [%s] for tenant [%s] discarded as per tenant filter in mappings.json." % (self.sample_dict['name'], self.converted_sample['tenant_name']))
        else:
            if self.verboselog:
                LOG.info("[*] Sample [%s] discarded as per meter filter in mappings.json." % self.sample_dict['name'])

    # emit parsed sample.
    def emit(self):
        # call parseSample method....
        self.parseSample()
        # if something has arrived, return it to caller
        if hasattr(self, "samplePoint"):
            return self.samplePoint
        else:
            # bummer.
            return None

    # exit point
    # context manager method
    def __exit__(self, exception_type, exception_val, trace):
        #self.logger.info("[+] Parser Object Destroyed")
        pass
