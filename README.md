# Ceilometer Publisher Driver for InfluxDB Time-series database #

This is a ceilometer publisher that collects data from an Openstack Cloud and writes back data into an InfluxDB time-series database.
This was written in 2016 for our OpenStack Kilo installation and maintained until the Mitaka release cycle, after which this was superseded by the Gnocchi Project.
Actual development is halted for now.

### INSTALLATION INSTRUCTIONS: ###
- Install and configure InfluxDB server, set admin password
- Install Grafana
- Copy directory dbdriver to /usr/lib/python2.7/site-packages/ceilometer/publisher/  (it's a clone of https://github.com/influxdata/influxdb-python with some fixes)
- Copy influxdb_sink.py to /usr/lib/python2.7/site-packages/ceilometer/publisher/
- Copy driver_utils.py to /usr/lib/python2.7/site-packages/ceilometer/publisher/
- Add entry_point in /usr/lib/python2.7/site-packages/ceilometer-6.1.3-py2.7.egg-info/entry_point.txt

                [ceilometer.publisher]
                influxdb = ceilometer.publisher.influxdb_sink:InfluxDBPublisher

- Add the new publisher to all sinks in /etc/ceilometer/pipeline.yaml as shown in pipeline.yaml
- Add a customized version of the configuration from ceilometer-influx.conf to /etc/ceilometer/ceilometer.conf:

                [influxdb]
                influxdb_addr=...
                influxdb_port=...
                ...
                
- Copy mappings.json to /etc/ceilometer/ and configure metering mappings between tags and meter names
- Restart openstack-ceilometer (sudo openstack-service restart openstack-ceilometer-*)



