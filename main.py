#!/usr/bin/env python
#
# Copyright 2014 Shaun Brandt <sbrandt@pdx.edu>, Neil Gebhard <gebhard@pdx.edu>,
#	Eddie Kelley <kelley@pdx.edu>, Eric Mumm <emumm@pdx.edu>, Tim Reilly <tfr@pdx.edu>.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import csv
import logging

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext.blobstore import BlobInfo
from google.appengine.ext import ndb
from google.appengine.runtime import apiproxy_errors

from BaseHandler import BaseHandler
from FileMetadata import FileMetadata
from FreewayData import Highway, Station, Detector, SpeedSum, DetectorEntry


def combine_stations():
	""" store Station entity keys in Highway records in datastore

	Append each Station entity's key to the corresponding Highway's list of stations.
	"""
	stn_q = Station.query()
	for stn in stn_q.fetch():
		hwy_q = Highway.query(Highway.highwayid == stn.highwayid)
		for hwy in hwy_q.fetch():
			if stn.key not in hwy.stations:
				logging.info("Appending station %s to highway %s", stn.stationid, hwy.highwayid)
				hwy.stations.append(stn.key)
				hwy.put()


def combine_detectors():
	""" combine Station and Detector data records in datastore

	Append each Detector record to the corresponding Station's list of detectors properties.
	Remove Detector entities after they have been imported.
	"""
	det_q = Detector.query()
	for det in det_q.fetch():
		stn_q = Station.query(Station.stationid == det.stationid)
		for stn in stn_q.fetch():
			if det not in stn.detectors:
				stn.detectors.append(det)
				stn.put()
				logging.info("Put detector:%s in station:%s", det.key, stn.stationid)
	deleteDetectors()

def deleteDetectors():
	""" delete all Detector entities from datastore """
	detector_keys = Detector.query().fetch(keys_only = True)
	detector_entities = ndb.get_multi(detector_keys)
	ndb.delete_multi([d.key for d in detector_entities])


def getHighways():
	""" get a list of highway entities

	Query the datastore for the list of highways
	
	Returns:
	  list of Highway entities
	"""

	hwy_q = Highway.query()
	results = hwy_q.fetch(12)
	hwys = [hwy for hwy in results]
	return hwys


def getStationsForHighway(hw, dir):
	""" get a list of station entities

	Query the datastore for a list of station entities located on a specific highway

	Args:
	  hw: highwayname that contains the desired stations
	  dir: direction of highway for stations that are requested
	Returns:
	  list of Station entities
	"""
	stations = []
	hwy_q = Highway.query(Highway.highwayname == hw, Highway.shortdirection == dir)
	for hwy in hwy_q.fetch():
		stations = [station.get() for station in hwy.stations]
	return stations


class MainHandler(BaseHandler):
	""" MainHandler class definition
	
	Provides a user interface
	"""
	def get(self):
		""" respond to HTTP GET requests
	
		Display a user interface for uploading files to Blobstore
		"""
		hwy = self.request.get('hwy', default_value = 'I-205')
		dir = self.request.get('dir', default_value = 'N')

		try:
			# get a list of files residing in Blobstore
			file_q = FileMetadata.query()
			results = file_q.fetch(10)
			files = [result for result in results]
			file_count = len(files)

			# get highways from Datastore
			hwys = getHighways()
			hwy_count = len(hwys)
			
			stns = getStationsForHighway(hwy, dir)
			stn_count = len(stns)
			
			hwy_list = set([hwy.highwayname for hwy in hwys])
			stn_list = set([stn.locationtext for stn in stns])
			
			upload_url = blobstore.create_upload_url('/upload')
					
			self.render_template("index.html",{
								 "file_count": file_count,
								 "files": files,
								 "highways": hwys,
								 "hwys_count": hwy_count,
								 "stations": stns,
								 "stns_count": stn_count,
								 "upload_url":upload_url})
		except apiproxy_errors.OverQuotaError, message:
			logging.error(message)
			self.response.out.write("<h3>Error</h3><br/><p>%s</p>", message)

class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
	""" UploadHandler class definition
	
	Handle uploads of data to Blobstore
	"""
	def post(self):
		""" respond to HTTP POST requests
	
		Create FileMetadata entity in Datastore to keep track of uploaded files
		"""
		blob_info = self.get_uploads()[0]
		
		file_metadata = FileMetadata(id = str(blob_info.key()),
									 content_type = blob_info.content_type,
									 creation = blob_info.creation,
									 filename = blob_info.filename,
									 size = blob_info.size,
									 md5_hash = blob_info.md5_hash,
									 blobkey = str(blob_info.key()))
									 
		file_metadata.put()
		self.redirect("/")


class ImportHandler(BaseHandler):
	""" ImportHandler class definition
	
	Handle import of data to Datastore
	"""
	def post(self):
		""" respond to HTTP POST requests
	
		Perform import of blob data referenced by blobkey
		"""
		# get the resource key
		resource = self.request.get('blobkey')
		# get BlobInfo from the blobstore using resource key
		blob_info = blobstore.BlobInfo.get(resource)
		# get the filename of the blob
		filename = blob_info.filename
		# get a BlobReader object for the resource
		blob_reader = blobstore.BlobReader(resource)
		# get a DictReader object to use for parsing the resource
		csv_reader = csv.DictReader(blob_reader)
		if filename == 'highways.csv':
			for line in csv_reader:
				h = Highway(id=line['highwayid'],
							highwayid=int(line['highwayid']),
							shortdirection=line['shortdirection'],
							direction=line['direction'],
							highwayname=line['highwayname'])
				h.put()
		elif filename == 'freeway_stations.csv':
			for line in csv_reader:
				s = Station(id=line['stationid'],
							stationid=int(line['stationid']),
							highwayid=int(line['highwayid']),
							milepost=float(line['milepost']),
							locationtext=line['locationtext'],
							upstream=int(line['upstream']),
							downstream=int(line['downstream']),
							stationclass=int(line['stationclass']),
							numberlanes=int(line['numberlanes']),
							latlon=ndb.GeoPt(line['latlon']),
							highway=ndb.Key(Highway, line['highwayid']))
				if '.' in line['length_mid']:
					setattr(s, 'length_mid', float(line['length_mid']))
				s.put()
			combine_stations()
		elif filename == 'freeway_detectors.csv':
			for line in csv_reader:
				d = Detector(id=line['detectorid'],
							 detectorid=int(line['detectorid']),
							 highwayid=int(line['highwayid']),
							 milepost=float(line['milepost']),
							 locationtext=line['locationtext'],
							 detectorclass=int(line['detectorclass']),
							 lanenumber=int(line['lanenumber']),
							 stationid=int(line['stationid']))
				d.put()
				self.response.out.write(d)
			combine_detectors()
		else:
			logging.info("Import not supported for file: "+blob_info.filename)
		self.redirect("/")

class Q1Handler(BaseHandler):
	""" Q1Handler class definition
	
	Handle running query 1 on over the datastore given user input
	"""
	def post(self):
		freeway = self.request.get('q1freeway')
		interval = self.request.get('q1interval')
		date = self.request.get('q1date')
		self.response.out.write('''
        	<html>
          		<body>
				Your input was freeway %s, interval %s, and date %s
            			<form action ="/">
              		 	  <input type="submit" name="Home" value="Home"/>
            			</form>
          		</body>
       	 	</html>
        	'''% (freeway, interval, date))


class Q2Handler(BaseHandler):
	""" Q2Handler class definition
	
	Handle running query 2 on over the datastore given user input
	"""
	def post(self):
		freeway = self.request.get('q2freeway')
		start = self.request.get('q2sdate')
		end = self.request.get('q2edate')
		self.response.out.write('''
        	<html>
          		<body>
            			<form action ="/">
              		 	  <input type="submit" name="Home" value="Home"/>
            			</form>
          		</body>
       	 	</html>
        	''')

class Q3Handler(BaseHandler):
	""" Q3Handler class definition
	
	Handle running query 3 on over the datastore given user input
	"""
	def post(self):
		freeway = self.request.get('q3freeway')
		start = self.request.get('q3sdate')
		end = self.request.get('q3edate')
		self.response.out.write('''
        	<html>
          		<body>
            			<form action ="/">
              		 	  <input type="submit" name="Home" value="Home"/>
            			</form>
          		</body>
       	 	</html>
        	''')

class Q4Handler(BaseHandler):
	""" Q4Handler class definition
	
	Handle running query 4 on over the datastore given user input
	"""
	def post(self):
		freeway = self.request.get('q4freeway')
		hour = self.request.get('q4hour')
		min = self.request.get('q4min')
		ampm = self.request.get('q4ampm')
		date = self.request.get('q4date')
		self.response.out.write('''
        	<html>
          		<body>
				
            			<form action ="/">
              		 	  <input type="submit" name="Home" value="Home"/>
            			</form>
          		</body>
       	 	</html>
        	''')

app = webapp2.WSGIApplication([
    ('/', MainHandler),
	('/upload', UploadHandler),
	('/import', ImportHandler),
	('/Queryone', Q1Handler),
	('/Querytwo', Q2Handler),
	('/Querythree', Q3Handler),
	('/Queryfour', Q4Handler)
], debug=True)
