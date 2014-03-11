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
from google.appengine.ext import ndb

class LoopData (ndb.Model):
	""" LoopData ndb class definition """
	detectorid = ndb.IntegerProperty(indexed = True)
	starttime = ndb.DateTimeProperty(indexed = True)
	volume = ndb.IntegerProperty(default = 0)
	speed = ndb.IntegerProperty(default = 0)
	occupancy = ndb.IntegerProperty(default = 0)
	status = ndb.IntegerProperty()
	dqflags = ndb.IntegerProperty()
	minute	= ndb.ComputedProperty(lambda self: self.starttime.minute)
	hour = ndb.ComputedProperty(lambda self: self.starttime.hour)

class Detector (ndb.Model):
	""" Detector ndb class definition """
	detectorid = ndb.IntegerProperty(indexed = True)
	highwayid = ndb.IntegerProperty()
	milepost = ndb.FloatProperty()
	locationtext = ndb.StringProperty()
	detectorclass = ndb.IntegerProperty()
	lanenumber = ndb.IntegerProperty()
	stationid = ndb.IntegerProperty()

class Station (ndb.Model):
	""" Station ndb class definition """
	stationid = ndb.IntegerProperty(indexed = True)
	highwayid = ndb.IntegerProperty()
	milepost = ndb.FloatProperty()
	locationtext = ndb.StringProperty()
	upstream = ndb.IntegerProperty()
	downstream = ndb.IntegerProperty()
	stationclass = ndb.IntegerProperty()
	numberlanes = ndb.IntegerProperty()
	latlon = ndb.GeoPtProperty()
	length_mid = ndb.FloatProperty()
	detectors = ndb.StructuredProperty(Detector, repeated=True)
	highway = ndb.KeyProperty()

class Highway (ndb.Model):
	""" Highway ndb class definition """
	highwayid = ndb.IntegerProperty(indexed = True)
	shortdirection = ndb.StringProperty()
	direction = ndb.StringProperty()
	highwayname = ndb.StringProperty()
	stations = ndb.KeyProperty(repeated=True)

class SpeedSum(ndb.Model):
	""" A class used to store sum/count values for different intervals"""
	time = ndb.TimeProperty()
	sum = ndb.IntegerProperty()
	count = ndb.IntegerProperty()

class DetectorEntry(ndb.Model):
	"""A helper class that represents DetectoryEntry counter values
	
	Store processed information from mapreduce jobs into the Datastore as DetectoryEntry entities
	for easy retrieval. Each entity represents a single day/detector combo, and will contain a single
	*_speed_sum SpeedSum property (time, count, and sum of speed measurements) for each date that is contained in the dataset.
	Entities can optionally have any supported interval of SpeedSum properties.
	"""
	date = ndb.DateProperty(indexed=True)
	detector = ndb.KeyProperty(indexed=True)
	day_speed = SpeedSum()
	hour_speed = ndb.StructuredProperty(SpeedSum, repeated=True)
	fifteenmin_speed = ndb.StructuredProperty(SpeedSum, repeated=True)
	fivemin_speed = ndb.StructuredProperty(SpeedSum, repeated=True)
