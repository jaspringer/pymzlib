"""
Copyright: 2010 Thomas McGrew

License: MIT license.

	Permission is hereby granted, free of charge, to any person
	obtaining a copy of this software and associated documentation
	files (the "Software"), to deal in the Software without
	restriction, including without limitation the rights to use,
	copy, modify, merge, publish, distribute, sublicense, and/or sell
	copies of the Software, and to permit persons to whom the
	Software is furnished to do so, subject to the following
	conditions:

	The above copyright notice and this permission notice shall be
	included in all copies or substantial portions of the Software.

	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
	EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
	OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
	NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
	HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
	WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
	FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
	OTHER DEALINGS IN THE SOFTWARE.


	Version alpha 2010.11.17

"""
import sys
import os
from xml.dom.minidom import parse
import struct
from base64 import b64decode
import types
import re
import zlib

class Parser( object ):

	def __init__( self, options=None ):
		"""
		Initializes a MzData object.

		:Parameters:
			options : None
				This argument is deprecated and not used. Only here for compatibility.

		"""
		object.__init__( self )

	def read( self, filename ):
		"""
		Load a file into this reference. This method will automatically detect the
		file type based on the file extension.

		:Parameters:
			filename : str
				The name of the file to load.

		"""

		if not os.path.exists( filename ):
			raise IOError( "The file %s does not exist or is not readable" % filename )

		try:
			fileExt = filename[ filename.rindex( '.' )+1: ]
		except ValueError:
			return False

		if ( fileExt.lower( ) == "csv" ):
			return self.readCsv( filename )

		elif ( fileExt.lower( ) == "mzdata" ):
			return self.readMzData( filename )

		elif ( fileExt.lower( ) == "mzxml" ):
			return self.readMzXml( filename )
		else:
			sys.stderr.write( "Unrecognized file type for %s\n" % filename )
			return False

	def readCsv( self, filename ):
		"""
		Read a file in Agilent csv format. You should only use this method if you
		know the data is in this format and does not have the .csv extension.

		:Parameters:
			filename : str
				The name of the file to load.

		"""
		returnValue = { "metadata" : {}, "scans" : [] }
		try:
			f = open( filename )
			lines = f.readlines( )
			f.close
		except IOError:
			sys.stderr.write( "Error: unable to read file '%s'\n" % filename )
			return False
	
		i = 0
		while( i < len( lines ) and lines[ i ][ :10 ] != "file name," ):
			i+= 1
		sourceFile = lines[ i ].split( ',' )[ 1 ]
		while ( i < len( lines ) and lines[ i ][ :9 ] != "[spectra]" ):
			i+=1
		i+=1
	
		if ( i > len( lines ) ):
			sys.stderr.write( "Unable to parse the reference file '%s'\n" % filename ) 
			return False
	
		msLevel = 1
		for line in lines[ i: ]:
			values = line.split( ',' )
			if values[ 4 ] == '-':
				polarity = -1
			else:
				polarity = 1
			rt = float( values[ 0 ])
			count = float( values[ 6 ])
			intensityValues = [  float( x )  for x in values[ 8:-1:2 ] ]
			massValues = [ float( y ) for y in values[ 7:-1:2 ] ]

			returnValue[ "scans" ].append({ 
				"retentionTime" : rt,
				"polarity" : polarity, 
				"msLevel" : msLevel, 
				"id" : scanId,
				"lowMz" : lowMz,
				"highMz" : highMz,
				"parentScan" : None,
				"precursorMz" : None,
				"collisionEnergy" : None,
				"data" : zip( massValues, intensityValues )
			})

		returnValue[ 'metadata' ] = {
			"sourceFile" : sourceFile
		}

		return returnValue

	def readMzData( self, filename ):
		"""
		Read a file in mzData format. You should only use this method if you
		know the data is in this format and does not have the .mzdata extension.

		:Parameters:
			filename : str
				The name of the file to load.

		"""
		returnValue = { "metadata" : {}, "scans" : [] }
		dataFile = parse( filename )
		sourceFileNode = dataFile.getElementsByTagName( 'sourceFile' )[ 0 ].\
			getElementsByTagName( 'nameOfFile' )[ 0 ]
		sourceFile = re.sub( "<.*?>", "", sourceFileNode.toxml( ))
		scans = dataFile.getElementsByTagName( 'spectrum' )

		for scan in scans:
			parentScan = None
			precursorMz = None
			collisionEnergy = None
			scanId = int( scan.getAttribute( 'id' ))
			spectrumInstrument = scan.getElementsByTagName( 'spectrumInstrument' )[ 0 ]
			msLevel = int( spectrumInstrument.getAttribute( 'msLevel' ))
			lowMz = float( spectrumInstrument.getAttribute( 'mzRangeStart' ))
			highMz = float( spectrumInstrument.getAttribute( 'mzRangeStop' ))
			params = spectrumInstrument.getElementsByTagName( 'cvParam' )
			for param in params:
				if param.getAttribute( 'name' ) == 'Polarity':
					if param.getAttribute( 'value' ) == 'positive':
						polarity = 1
					else:
						polarity = -1
				if param.getAttribute( 'name' ) == 'TimeInMinutes':
					rt = float( param.getAttribute( 'value' ))

			
			massValues = self._unpackMzData( 
				scan.getElementsByTagName( 'mzArrayBinary' )[ 0 ].getElementsByTagName( 'data' )[ 0 ])
			intensityValues = self._unpackMzData( 
				scan.getElementsByTagName( 'intenArrayBinary' )[ 0 ].getElementsByTagName( 'data' )[ 0 ])

			precursors = scan.getElementsByTagName( 'precursor' )
			for precursor in precursors[ 0:1 ]:
				parentScan = int( precursor.getAttribute( 'spectrumRef' ))
				cvParams = precursor.getElementsByTagName( 'cvParam' )
				for param in cvParams:
					if param.getAttribute( 'name' ) == 'MassToChargeRatio':
						precursorMz = float( param.getAttribute( 'value' ))
#					if param.getAttribute( 'name' ) == 'ChargeState':
#						chargeState = int( param.getAttribute( 'value' ))
					if param.getAttribute( 'name' ) == 'CollisionEnergy':
						collisionEnergy = float( param.getAttribute( 'value' ))



			returnValue[ "scans" ].append({ 
				"retentionTime" : rt,
				"polarity" : polarity, 
				"msLevel" : msLevel, 
				"id" : scanId,
				"lowMz" : lowMz,
				"highMz" : highMz,
				"parentScan" : parentScan,
				"precursorMz" : precursorMz,
				"collisionEnergy" : collisionEnergy,
				"data" : zip( massValues, intensityValues )
			})

		returnValue[ 'metadata' ] = {
			"sourceFile" : sourceFile
		}

		return returnValue

	def _unpackMzData( self, dataNode ):
		"""
		Internal function. Unpacks the scan data contained in a <data> node in mzdata 
		format.
	
		:Parameters:
			dataNode : xmlNode
				The xml node containing the scan data to be unpacked.

		"""
		scanSize = int( dataNode.getAttribute( 'length' ))
		if dataNode.getAttribute( 'endian' ) == 'little':
			byteOrder = '<'
		else:
			byteOrder = '>'
		if dataNode.getAttribute( 'precision' ) == '64':
			dataType = 'd'
		else: 
			dataType = 'f'

		return struct.unpack( byteOrder + ( dataType * scanSize ), 
			b64decode( re.sub( "<.*?>", "", dataNode.toxml( ))))

	def readMzXml( self, filename ):
		"""
		Read a file in mzXML format. You should only use this method if you
		know the data is in this format and does not have the .mzxml extension.

		:Parameters:
			filename : str
				The name of the file to load.

		"""
		returnValue = { "metadata" : {}, "scans" : [] }
		dataFile = parse( filename )
		scans = dataFile.getElementsByTagName( 'scan' )
		for scan in scans:
			collisionEnergy = None
			precursorMz = None
			msLevel = int( scan.getAttribute( "msLevel" ))
			scanSize = int( scan.getAttribute( 'peaksCount' ))
			rt = float( scan.getAttribute( 'retentionTime' )[ 2:-1 ] ) / 60
			scanId = int( scan.getAttribute( 'num' ))
			lowMz = float( scan.getAttribute( 'lowMz' ))
			highMz = float( scan.getAttribute( 'highMz' ))
			if ( scan.getAttribute( 'polarity' ) == '+' ):
				polarity = 1
			else:
				polarity = -1
			if msLevel == 1:
				parentScan = None
			else:
				parentScan = int( scan.parentNode.getAttribute( 'num' ))
				if ( scan.getAttribute( 'collisionEnergy' )):
					collisionEnergy = float( scan.getAttribute( 'collisionEnergy' ))
				precursorTags = scan.getElementsByTagName( 'precursorMz' )
				if ( len( precursorTags )):
					precursorMz = float( re.sub( r"<.*?>", "", precursorTags[ 0 ].toxml( )).strip( ))
			

			peaks = scan.firstChild
			while not ( peaks.nodeType == peaks.ELEMENT_NODE and peaks.tagName == 'peaks' ):
				peaks = peaks.nextSibling

			if peaks.getAttribute( 'precision' ) == '64':
				type = 'd'
			else: 
				type='f'
			byteOrder = '>'

			# get all of the text (non-tag) content of peaks
			packedData = re.sub( r"<.*?>", "", peaks.toxml( )).strip( )
			if ( peaks.getAttribute( 'compressionType' ) == 'zlib' ):
				data = struct.unpack( byteOrder + ( type * scanSize * 2 ), zlib.decompress( b64decode( packedData )))
			else:
				data = struct.unpack( byteOrder + ( type * scanSize * 2 ), b64decode( packedData ))
			massValues = data[ 0::2 ]
			intensityValues = data[ 1::2 ] 

			returnValue[ "scans" ].append({ 
				"retentionTime" : rt,
				"polarity" : polarity, 
				"msLevel" : msLevel, 
				"id" : scanId,
				"lowMz" : lowMz,
				"highMz" : highMz,
				"parentScan" : parentScan,
				"precursorMz" : precursorMz,
				"collisionEnergy" : collisionEnergy,
				"data" : zip( massValues, intensityValues )
			})

		return returnValue

	def readMzml( self, filename ):
		pass
		

	def _getChildNode( self, node, child ):
		returnValue = node.firstChild
		while returnValue and not ( 
			returnValue.nodeType == returnValue.ELEMENT_NODE and 
			returnValue.tagName == child ):

			returnValue = returnValue.nextSibling
		return returnValue

class RawData( object ):
	"""
	A class for reading and obtaining data from a mass spectrometry data file

	"""
	def __init__( self ):
		object.__init__( self, metadata=None )
		self.metadata = dict( )
		self.scans = [[],[]]

	def addScan( self, scan ):
		self.scans[ scan.level-1 ].append( scan )

	def getScans( self, level=None ):
		if not level:
			return sorted( scans[ 0 ] + scans[ 1 ] )
		return scans[ level-1 ]

#	def filterByTime( self, minTime=0, maxTime=0 ):
#		"""
#		Filters the data by retention time, removing any unwanted data
#
#		:Parameters:
#			minTime : float
#				The minimum retention time to keep in this Object.
#			maxTime : float
#				The maximum retention time to keep in this Object.
#		"""
#		if ( minTime or maxTime ):
#			minIndex, maxIndex = ( 0, len( self.rt ) + 1 )			
#			for i in xrange( len( self.rt )): 
#				if ( self.rt[ i ] < minTime ):
#					minIndex = i
#				if ( maxTime and self.rt[ i ] > maxTime ):
#					maxIndex = i
#					break
#			minIndex += 1
#			self.rt = self.rt[ minIndex:maxIndex ]
#			self.mass =  self.mass[ minIndex:maxIndex ]
#			self.intensity = self.intensity[ minIndex:maxIndex ]
#			self.firstIndex = i
#
#	def filterByMass( minMass=0, maxMass=0 ):
#		"""
#		Filters the data to keep only a certain mass range
#		The data size is not changed, data which is not retained is zeroed.
#
#		:Parameters:
#			minMass : float
#				The minimum mass to retain.
#			maxMass : float
#				The maximum mass to retain.
#		"""
#		for i in xrange( len( self.rt )): 
#			for j in xrange( len( self.mass[ i ])):
#				if ( self.mass[ i ][ j ] < minMass or self.mass[ i ][ j ] > maxMass ):
#					self.mass[ i ][ j ] = 0
#					self.intensity[ i ][ j ] = 0
#
#		return True 

class Scan( object ):
	
	"""
	A class for holding data related to a single scan.
	"""
	def __init__( self, id=0, retentionTime=0, msLevel=1, polarity=1, lowMz=0, highMz=2200, data=list( ), metadata=dict( ), parentScan=None, precursorMa=None, collisionEnergy=None):
		self.retentionTime = retentionTime
		self.level = msLevel
		self.metadata = metadata
		self.points = list( )

	def __iter__( self ):
		return self.points

	def __lt__( self, scan ):
		return self.retentionTime < scan.retentionTime
	
	def __gt__( self, scan ):
		return self.retentionTime > scan.retentionTime

	def __eq__( self, scan ):
		return self.retentionTime == scan.retentionTime
	
	def __le__( self, scan ):
		return self.retentionTime <= scan.retentionTime

	def __ge__( self, scan ):
		return self.retentionTime >= scan.retentionTime

	def __ne__( self, scan ):
		return self.retentionTime != scan.retentionTime

	def addDataPoint( mz, intensity ):
		self.points.append(( mz, intensity ))

	def filterByMass( minMass=0, maxMass=1048576 ):
		returnValue = Scan( self._metadata )
		for point in [ (mz,intensity) for (mz,intensity) in self.points if ( mz > minMass and mz < maxMass ) ]:
			returnValue.add( *point )
		return returnValue
	

