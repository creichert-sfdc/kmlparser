# Chris Reichert
# Salesforce.com
# September 29, 2017
# 
# KML Parser
# Tested in Python 3.6 on MacOSX
#
# This is a simple script for manipulating very detailed KML files of
# the type you are likely to find on OpenGIS and other public repos of
# geodata.  Sparse KML definitions are better suited for use as FSL
# polygon definitions as they vastly reduce the intensity of computation
# for geofence calculations
#
# Due to variations in KML input formats, you should expect to need to 
# tweak this code to fit your need.  The Git repo for this script includes
# the KML file it was written for so you can make comparisons
#
# The core of the script makes use of a python library called 'simplification'
# (https://pypi.python.org/pypi/simplification/)
# employing a Ramer–Douglas–Peucker algorithm
# (https://en.wikipedia.org/wiki/Ramer–Douglas–Peucker_algorithm) 
# to perform linestring reduction on a set of points
#
# Error checking in here is minimal, so watch for weird parse errors, I suggest trying 
# with a small sample of test data
#
# TO DO: Add a dataloader hook to directly map the parsed data into SF objects
# TO DO: Make the script interactive at the command line
#

import re  #standard python library
import numpy as np 	#must be installed for your python dist, is used by 'simplification'
from simplification.cutil import simplify_coords  #must install the 'simplification' package for your python dist


##### HELPER FUNCTIONS #####

# Perform the simplification on a given array of points
#
# Input:
#	inpoints -- a float array of lat/long points in the form [[lat1,long1],[lat2,long2]...]
#
# Output:
#	outpoints -- a string array of reduced points transformed as required for FSL KML
#			  	 in the form [["lat1,long1,0"]["lat2,long2,0"]...]
#
def Simplified(inpoints):
	outpoints = []

	# This controls the resolution of the simplification algorithm, for comparison
	# this is the rough scale of these factors in geodecimal notation:
	#
	# 0.01	= ~1 km
	# 0.001	= ~100 m
	# 0.0001= ~10 m
	#
	# I found that 0.001 reduced dense KML of county-size objects by a factor of 10 without any noticeable impact to the shape
	# 0.01 gave a factor of about 100 with still very little loss.  Smaller objects (e.g. zip code) will require
	# smaller reduction factors
	lineWidth = 0.001

	simplified = simplify_coords(inpoints, lineWidth)

	# Iterate through all the output points and transform them for FSL
	for x in simplified:
		x.append(0)
		y = [str(i) for i in x]
		outpoints.append(y)

	# Add the first point in the array to the end of the array to guarantee a closed loop
	outpoints.append(outpoints[0])

	# Final transform to a  normalized string
	outpoints = [','.join(x) for x in outpoints]

	# Returm the normalized array
	return outpoints


# Write out the transformed points into a new KML file
# This will perform the added step of breaking apart files that contain KML data for multiple objects
# into individual files for each object, making it easier to copy/paste into FSL.
#
# Contains the minimal KML headers required by FSL, and inserts the object name at the correct places
#
# Input:
#	name -- String containing the name of the object being parsed
#	points -- a string array of geodata in the form [["lat1,long1,0"]["lat2,long2,0"]...]
#
# Output:
#	n/a
#
def KmlOut(name, points):

	# Opening KML header string with the object name inserted
	kmlopen = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Style id="''' + name + '''Style"> 
<LineStyle> 
<width>1</width> 
</LineStyle> 
<PolyStyle> 
<color>8033CAC0</color> 
</PolyStyle> 
</Style> 
<Placemark> 
<name>''' + name + '''</name> 
<styleUrl>#''' + name + '''Style</styleUrl> 
<Polygon> 
<outerBoundaryIs> 
<LinearRing>
<coordinates>\n'''

	# Closing KML headers
	kmlclose = '''</coordinates> 
</LinearRing> 
</outerBoundaryIs> 
</Polygon> 
</Placemark> 
</kml>'''

	# Open an output file handle and loop through the points
	# write each one along with a \n character
	# wrap the write with the KML headers
	with open(name + '_points.kml','w') as f:
		f.write(kmlopen)
		for i in points:
			f.write(i + '\n')
		f.write(kmlclose)

	# Helpful to monitor progress and see the level of reduction
	print('wrote file for ' + name + ' -- length: ' + str(len(points)))


##### MAIN SCRIPT #####

# Init variables to track the polygon name and its contained points
name = ''
points = []
filename = 'County_Boundaries.kml'

# Open an input file handle and read in a line at a time, checking for lines with relevant data
# This expects each KML tag to be on it's own line, but most importantly, each geopoint will be on its own line
# and a set of geopoints will be on consecutive lines with nothing in between
# If this is not the case reformat your input file or the parser will miss points or prematurely cut out
#
# Change the filename to your file
with open(filename) as f:
	for l in f:
		# Use a Regular Expression to check the line for one of two salient details:
		# 1: a KML name tag  '<name>Example County</name>'
		# 2: a string of geodata  '-97.7678364872634,29.43458974957393'
		#
		# For case 2, we only keep 6 decimal places as the additional resolution is not useful
		# Watch out for cases where your geodata has fewer than 6 decimal places--this RE will
		# Need to be modified in that case
		# 
		m = re.search('<name>([\w\s]*)</name>|(-\d{2}.\d{6})\d*,(\d{2}.\d{6})\d*',l) 
		if m and m.group(1):
			#Found a name, set the name var, add underscore in place of any spaces
			name = m.group(1).replace(' ','_')
		elif m and m.group(2) and m.group(3):
			#Found some geo data, append it to the points array
			points.append(list([float(m.group(2)), float(m.group(3))]))
		elif len(points):
			# Didn't find anything but we found some points before
			# so we're at the end of a list of points
			# Write it out and reinit the points array
			KmlOut(name, Simplified(points))
			points = []
