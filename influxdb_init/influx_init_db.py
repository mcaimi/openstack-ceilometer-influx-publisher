#!/usr/bin/env python
# initialize database

import sys
import requests
from requests.auth import HTTPBasicAuth
import argparse
import yaml
from CFileParser import CFileParser

ENDPOINT_URL_TEMPLATE="http://%s:%d/%s"

aparser = argparse.ArgumentParser(prog="InfluxDB Init Utility")
aparser.add_argument("--config", help="Configuration file in yaml format (see config.yaml in this directory")
aparser.add_argument("--db_name", help="Name of the database")
aparser.add_argument("--admin_user", help="Admin user to create on InfluxDB")
aparser.add_argument("--nuke_db", help="If True, delete ceilometer database from influx.")

if __name__=="__main__":
	
	# parse command line
	arguments = aparser.parse_args()
	if arguments.nuke_db is None:
		arguments.nuke_db = False
	
	# gather command line parameters
	if (arguments.db_name is None):
		aparser.print_help()
		sys.exit(0)
		
	# sanity check and go
	if arguments.config is not None:
		cfg = CFileParser(arguments.config)
		cfg.parse()

		# fill info...
		ENDPOINT_URL = ENDPOINT_URL_TEMPLATE % (cfg.influx_db_address, cfg.influx_db_port, cfg.influx_query_endpoint)
		DB_NAME = arguments.db_name
		
		if (arguments.admin_user is not None):
			ADMIN_USER=arguments.admin_user
			ADMIN_PASS=raw_input("ADMIN PASSWORD> ")
		else:
			aparser.print_help()
			sys.exit(0)

		if (arguments.nuke_db is False):
			print("[+] Connecting to %s..." % ENDPOINT_URL)
			credentials = HTTPBasicAuth(cfg.influx_admin_user, cfg.influx_admin_pass)
		
			try:
				# creating database...
				r = requests.get(ENDPOINT_URL, auth=credentials, params={'q':'CREATE DATABASE %s' % DB_NAME})
				print("[+] GET: %s" % r.url)
				
				if r.status_code != 200:
					print("[-] ERROR: status code %d: %s" %(r.status_code, r.content))
				else:
					print("[+] status code: %s" % r.status_code)
				
				# creating admin user...
				r = requests.get(ENDPOINT_URL, auth=credentials, params={'q':'CREATE USER %s WITH PASSWORD \'%s\' WITH ALL PRIVILEGES' % (ADMIN_USER, ADMIN_PASS)})
				print("[+] GET: %s" % r.url)
				
				if r.status_code != 200:
					print("[-] ERROR: status code %d: %s" %(r.status_code, r.content))
					print("	[-] Rolling back...")
					r = requests.get(ENDPOINT_URL, auth=credentials, params={'q':'DROP DATABASE %S' % DB_NAME})
					print("[+] GET: %s" % r.url)
				else:
					print("[+] status code: %s" % r.status_code)
				
				print("Now Log into your influx DB server and set authentication to True")
			except Exception as e:
				print("Caught exception: %s" % e)
		else:
			credentials = HTTPBasicAuth(cfg.influx_admin_user, cfg.influx_admin_pass)
			print("[+] NUKING DB.")
			r = requests.get(ENDPOINT_URL, auth=credentials, params={'q':'DROP DATABASE %s' % DB_NAME})
			print("[+] GET: %s" % r.url)
				
			if r.status_code != 200:
				print("[-] ERROR: status code %d: %s" %(r.status_code, r.content))
			else:
				print("[+] status code: %s" % r.status_code)
	
			r = requests.get(ENDPOINT_URL, auth=credentials, params={'q':'DROP USER %s' % ADMIN_USER})
			print("[+] GET: %s" % r.url)
				
			if r.status_code != 200:
				print("[-] ERROR: status code %d: %s" %(r.status_code, r.content))
			else:
				print("[+] status code: %s" % r.status_code)
	else:
		aparser.print_help()
