# Copyright (C) 2006  Kipp Cannon
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


#
# =============================================================================
#
#                                   Preamble
#
# =============================================================================
#


"""
This module provides class definitions corresponding to the elements that
can be found in a LIGO Light Weight XML file.  It also provides a class
representing an entire LIGO Light Weight XML document, a ContentHandler
class for use with SAX2 parsers, and a convenience function for
constructing a parser.
"""


import re
import sys
from xml import sax
from xml.sax.saxutils import escape as xmlescape
from xml.sax.saxutils import unescape as xmlunescape


from glue import git_version
from glue.ligolw import types as ligolwtypes


__author__ = "Kipp Cannon <kipp.cannon@ligo.org>"
__version__ = "git id %s" % git_version.id
__date__ = git_version.date


#
# =============================================================================
#
#                         Document Header, and Indent
#
# =============================================================================
#


Header = u"""<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE LIGO_LW SYSTEM "http://ldas-sw.ligo.caltech.edu/doc/ligolwAPI/html/ligolw_dtd.txt">"""


Indent = u"\t"


#
# =============================================================================
#
#                                Element Class
#
# =============================================================================
#


class ElementError(Exception):
	"""
	Base class for exceptions generated by elements.
	"""
	pass


class Element(object):
	"""
	Base class for all element types.  This class is inspired by the
	class of the same name in the Python standard library's xml.dom
	package.  One important distinction is that the standard DOM
	element is used to represent the structure of a document at a much
	finer level of detail than here.  For example, in the case of the
	standard DOM element, each XML attribute is its own element being a
	child node of its tag, while here they are simply stored in a class
	attribute of the tag element itself.  This simplification is
	possible due to our knowledge of the DTD for the documents we will
	be parsing.  The standard xml.dom package is designed to represent
	any arbitrary XML document exactly, while we can only deal with
	LIGO Light Weight XML documents.

	Despite the differences, the documentation for the xml.dom package,
	particularly that of the Element class and it's parent, the Node
	class, is useful as supplementary material in understanding how to
	use this class.
	"""
	# XML tag names are case sensitive:  compare with ==, !=, etc.
	tagName = None
	validattributes = []
	validchildren = []

	def __init__(self, attrs = sax.xmlreader.AttributesImpl({})):
		"""
		Construct an element.  The argument is a
		sax.xmlreader.AttributesImpl object (see the xml.sax
		documentation, but it's basically a dictionary-like thing)
		used to set the element attributes.
		"""
		for key in attrs.keys():
			if key not in self.validattributes:
				raise ElementError, "%s does not have attribute %s" % (self.tagName, key)
		self.parentNode = None
		self.attributes = attrs
		self.childNodes = []
		self.pcdata = None

	def start_tag(self, indent):
		"""
		Generate the string for the element's start tag.
		"""
		s = indent + u"<" + self.tagName
		for keyvalue in self.attributes.items():
			s += u" %s=\"%s\"" % keyvalue
		s += u">"
		return s

	def end_tag(self, indent):
		"""
		Generate the string for the element's end tag.
		"""
		return indent + u"</" + self.tagName + u">"

	def appendChild(self, child):
		"""
		Add a child to this element.  The child's parentNode
		attribute is updated, too.
		"""
		self.childNodes.append(child)
		child.parentNode = self
		self._verifyChildren(len(self.childNodes) - 1)
		return child

	def insertBefore(self, newchild, refchild):
		"""
		Insert a new child node before an existing child. It must
		be the case that refchild is a child of this node; if not,
		ValueError is raised. newchild is returned.
		"""
		for i, childNode in enumerate(self.childNodes):
			if childNode is refchild:
				break
		else:
			raise ValueError, refchild
		self.childNodes.insert(i, newchild)
		newchild.parentNode = self
		self._verifyChildren(i)
		return newchild

	def removeChild(self, child):
		"""
		Remove a child from this element.  The child element is
		returned, and it's parentNode element is reset.  If the
		child will not be used any more, you should call its
		unlink() method to promote garbage collection.
		"""
		for i, childNode in enumerate(self.childNodes):
			if childNode is child:
				self.childNodes.pop(i)
				break
		child.parentNode = None
		return child

	def unlink(self):
		"""
		Break internal references within the document tree rooted
		on this element to promote garbage collection.
		"""
		self.parentNode = None
		for child in self.childNodes:
			child.unlink()
		self.childNodes = []

	def replaceChild(self, newchild, oldchild):
		"""
		Replace an existing node with a new node. It must be the
		case that oldchild is a child of this node; if not,
		ValueError is raised. newchild is returned.
		"""
		for i, childNode in enumerate(self.childNodes):
			if childNode is oldchild:
				break
		else:
			raise ValueError, oldchild
		self.childNodes[i].parentNode = None
		self.childNodes[i] = newchild
		newchild.parentNode = self
		self._verifyChildren(i)
		return newchild

	def getElements(self, filter):
		"""
		Return a list of elements below elem for which filter(element)
		returns True.
		"""
		l = reduce(lambda l, e: l + e.getElements(filter), self.childNodes, [])
		if filter(self):
			l.append(self)
		return l

	def getElementsByTagName(self, tagName):
		return self.getElements(lambda e: e.tagName == tagName)

	def getChildrenByAttributes(self, attrs):
		l = []
		for c in self.childNodes:
			try:
				if reduce(lambda t, (k, v): t and (c.getAttribute(k) == v), attrs.iteritems(), True):
					l.append(c)
			except KeyError:
				pass
		return l

	def hasAttribute(self, attrname):
		return self.attributes.has_key(attrname)

	def getAttribute(self, attrname):
		return self.attributes[attrname]

	def setAttribute(self, attrname, value):
		# cafeful:  this digs inside an AttributesImpl object and
		# modifies its internal data.  probably not a good idea,
		# but I don't know how else to edit an attribute because
		# the stupid things don't export a method to do it.
		self.attributes._attrs[attrname] = str(value)

	def appendData(self, content):
		"""
		Add characters to the element's pcdata.
		"""
		if self.pcdata:
			self.pcdata += content
		else:
			self.pcdata = content

	def _verifyChildren(self, i):
		"""
		Method used internally by some elements to verify that
		their children are from the allowed set and in the correct
		order following modifications to their child list.  i is
		the index of the child that has just changed.
		"""
		pass

	def write(self, file = sys.stdout, indent = u""):
		"""
		Recursively write an element and it's children to a file.
		"""
		file.write(self.start_tag(indent) + u"\n")
		for c in self.childNodes:
			if c.tagName not in self.validchildren:
				raise ElementError, "invalid child %s for %s" % (c.tagName, self.tagName)
			c.write(file, indent + Indent)
		if self.pcdata:
			file.write(xmlescape(self.pcdata))
			file.write(u"\n")
		file.write(self.end_tag(indent) + u"\n")


def WalkChildren(elem):
	"""
	Walk the XML tree of children below elem, returning each in order.
	"""
	for child in elem.childNodes:
		yield child
		for elem in WalkChildren(child):
			yield elem


#
# =============================================================================
#
#                        LIGO Light Weight XML Elements
#
# =============================================================================
#


class LIGO_LW(Element):
	"""
	LIGO_LW element.
	"""
	tagName = u"LIGO_LW"
	validchildren = [u"LIGO_LW", u"Comment", u"Param", u"Table", u"Array", u"Stream", u"IGWDFrame", u"AdcData", u"AdcInterval", u"Time", u"Detector"]
	validattributes = [u"Name", u"Type"]


class Comment(Element):
	"""
	Comment element.
	"""
	tagName = u"Comment"

	def write(self, file = sys.stdout, indent = u""):
		if self.pcdata:
			file.write(self.start_tag(indent))
			file.write(xmlescape(self.pcdata))
			file.write(self.end_tag(u"") + u"\n")
		else:
			file.write(self.start_tag(indent) + self.end_tag(u"") + u"\n")


class Param(Element):
	"""
	Param element.
	"""
	tagName = u"Param"
	validchildren = [u"Comment"]
	validattributes = [u"Name", u"Type", u"Start", u"Scale", u"Unit", u"DataUnit"]


class Table(Element):
	"""
	Table element.
	"""
	tagName = u"Table"
	validchildren = [u"Comment", u"Column", u"Stream"]
	validattributes = [u"Name", u"Type"]

	def _verifyChildren(self, i):
		ncomment = 0
		ncolumn = 0
		nstream = 0
		for child in self.childNodes:
			if child.tagName == Comment.tagName:
				if ncomment:
					raise ElementError, "only one Comment allowed in Table"
				if ncolumn or nstream:
					raise ElementError, "Comment must come before Column(s) and Stream in Table"
				ncomment += 1
			elif child.tagName == Column.tagName:
				if nstream:
					raise ElementError, "Column(s) must come before Stream in Table"
				ncolumn += 1
			else:
				if nstream:
					raise ElementError, "only one Stream allowed in Table"
				nstream += 1


class Column(Element):
	"""
	Column element.
	"""
	tagName = u"Column"
	validattributes = [u"Name", u"Type", u"Unit"]

	def start_tag(self, indent):
		"""
		Generate the string for the element's start tag.
		"""
		s = indent + u"<" + self.tagName
		for keyvalue in self.attributes.items():
			s += u" %s=\"%s\"" % keyvalue
		s += u"/>"
		return s

	def end_tag(self, indent):
		"""
		Generate the string for the element's end tag.
		"""
		return u""

	def write(self, file = sys.stdout, indent = u""):
		"""
		Recursively write an element and it's children to a file.
		"""
		file.write(self.start_tag(indent) + u"\n")


class Array(Element):
	"""
	Array element.
	"""
	tagName = u"Array"
	validchildren = [u"Dim", u"Stream"]
	validattributes = [u"Name", u"Type", u"Unit"]

	def _verifyChildren(self, i):
		nstream = 0
		for child in self.childNodes:
			if child.tagName == Dim.tagName:
				if nstream:
					raise ElementError, "Dim(s) must come before Stream in Array"
			else:
				if nstream:
					raise ElementError, "only one Stream allowed in Array"
				nstream += 1


class Dim(Element):
	"""
	Dim element.
	"""
	tagName = u"Dim"
	validattributes = [u"Name", u"Unit", u"Start", u"Scale"]

	def write(self, file = sys.stdout, indent = u""):
		if self.pcdata:
			file.write(self.start_tag(indent))
			file.write(xmlescape(self.pcdata))
			file.write(self.end_tag(u"") + u"\n")
		else:
			file.write(self.start_tag(indent) + self.end_tag(u"") + u"\n")


class Stream(Element):
	"""
	Stream element.
	"""
	tagName = u"Stream"
	validattributes = [u"Name", u"Type", u"Delimiter", u"Encoding", u"Content"]

	def __init__(self, attrs = sax.xmlreader.AttributesImpl({})):
		if not attrs.has_key(u"Type"):
			attrs._attrs[u"Type"] = u"Local"
		if not attrs.has_key(u"Delimiter"):
			attrs._attrs[u"Delimiter"] = u","
		if attrs[u"Type"] not in [u"Remote", u"Local"]:
			raise ElementError, "invalid Type for Stream: %s" % attrs[u"Type"]
		Element.__init__(self, attrs)


class IGWDFrame(Element):
	"""
	IGWDFrame element.
	"""
	tagName = u"IGWDFrame"
	validchildren = [u"Comment", u"Param", u"Time", u"Detector", u"AdcData", u"LIGO_LW", u"Stream", u"Array", u"IGWDFrame"]
	validattributes = [u"Name"]


class Detector(Element):
	"""
	Detector element.
	"""
	tagName = u"Detector"
	validchildren = [u"Comment", u"Param", u"LIGO_LW"]
	validattributes = [u"Name"]


class AdcData(Element):
	"""
	AdcData element.
	"""
	tagName = u"AdcData"
	validchildren = [u"AdcData", u"Comment", u"Param", u"Time", u"LIGO_LW", u"Array"]
	validattributes = [u"Name"]


class AdcInterval(Element):
	"""
	AdcInterval element.
	"""
	tagName = u"AdcInterval"
	validchildren = [u"AdcData", u"Comment", u"Time"]
	validattributes = [u"Name", u"StartTime", u"DeltaT"]


class Time(Element):
	"""
	Time element.
	"""
	tagName = u"Time"
	validattributes = [u"Name", u"Type"]

	def __init__(self, attrs = sax.xmlreader.AttributesImpl({})):
		if not attrs.has_key(u"Type"):
			attrs._attrs[u"Type"] = u"ISO-8601"
		if attrs[u"Type"] not in ligolwtypes.TimeTypes:
			raise ElementError, "invalid Type for Time: %s" % attrs[u"Type"]
		Element.__init__(self, attrs)


class Document(Element):
	"""
	Description of a LIGO LW file.
	"""
	tagName = u"Document"
	validchildren = [u"LIGO_LW"]

	def write(self, file = sys.stdout):
		"""
		Write the document.
		"""
		file.write(Header + u"\n")
		for c in self.childNodes:
			if c.tagName not in self.validchildren:
				raise ElementError, "invalid child %s for %s" % (c.tagName, self.tagName)
			c.write(file)


#
# =============================================================================
#
#                             SAX Content Handler
#
# =============================================================================
#


class LIGOLWContentHandler(sax.handler.ContentHandler):
	"""
	ContentHandler class for parsing LIGO Light Weight documents with a
	SAX2-compliant parser.

	Example:

	>>> import ligolw
	>>> doc = ligolw.Document()
	>>> handler = ligolw.LIGOLWContentHandler(doc)
	>>> parser = ligolw.make_parser(handler)
	>>> parser.parse(file("H2-POWER_S5-816526720-34.xml"))
	>>> doc.write()
	"""
	def __init__(self, document):
		"""
		Initialize the handler by pointing it to the Document object
		into which the parsed file will be loaded.
		"""
		self.document = document
		self.current = self.document

	def startAdcData(self, attrs):
		return AdcData(attrs)

	def endAdcData(self):
		pass

	def startAdcInterval(self, attrs):
		return AdcInterval(attrs)

	def endAdcInterval(self):
		pass

	def startArray(self, attrs):
		return Array(attrs)

	def endArray(self):
		pass

	def startColumn(self, attrs):
		return Column(attrs)

	def endColumn(self):
		pass

	def startComment(self, attrs):
		return Comment(attrs)

	def endComment(self):
		pass

	def startDetector(self, attrs):
		return Detector(attrs)

	def endDetector(self):
		pass

	def startDim(self, attrs):
		return Dim(attrs)

	def endDim(self):
		pass

	def startIGWDFrame(self, attrs):
		return IGWDFrame(attrs)

	def endIGWDFrame(self):
		pass

	def startLIGO_LW(self, attrs):
		return LIGO_LW(attrs)

	def endLIGO_LW(self):
		pass

	def startParam(self, attrs):
		return Param(attrs)

	def endParam(self):
		pass

	def startStream(self, attrs):
		return Stream(attrs)

	def endStream(self):
		pass

	def startTable(self, attrs):
		return Table(attrs)

	def endTable(self):
		pass

	def startTime(self, attrs):
		return Time(attrs)

	def endTime(self):
		pass

	def startElement(self, name, attrs):
		if name == AdcData.tagName:
			child = self.startAdcData(attrs)
		elif name == AdcInterval.tagName:
			child = self.startAdcInterval(attrs)
		elif name == Array.tagName:
			child = self.startArray(attrs)
		elif name == Column.tagName:
			child = self.startColumn(attrs)
		elif name == Comment.tagName:
			child = self.startComment(attrs)
		elif name == Detector.tagName:
			child = self.startDetector(attrs)
		elif name == Dim.tagName:
			child = self.startDim(attrs)
		elif name == IGWDFrame.tagName:
			child = self.startIGWDFrame(attrs)
		elif name == LIGO_LW.tagName:
			child = self.startLIGO_LW(attrs)
		elif name == Param.tagName:
			child = self.startParam(attrs)
		elif name == Stream.tagName:
			child = self.startStream(attrs)
		elif name == Table.tagName:
			child = self.startTable(attrs)
		elif name == Time.tagName:
			child = self.startTime(attrs)
		else:
			raise ElementError, "unknown element %s" % name
		self.current.appendChild(child)
		self.current = child

	def endElement(self, name):
		if name == AdcData.tagName:
			self.endAdcData()
		elif name == AdcInterval.tagName:
			self.endAdcInterval()
		elif name == Array.tagName:
			self.endArray()
		elif name == Column.tagName:
			self.endColumn()
		elif name == Comment.tagName:
			self.endComment()
		elif name == Detector.tagName:
			self.endDetector()
		elif name == Dim.tagName:
			self.endDim()
		elif name == IGWDFrame.tagName:
			self.endIGWDFrame()
		elif name == LIGO_LW.tagName:
			self.endLIGO_LW()
		elif name == Param.tagName:
			self.endParam()
		elif name == Stream.tagName:
			self.endStream()
		elif name == Table.tagName:
			self.endTable()
		elif name == Time.tagName:
			self.endTime()
		else:
			raise ElementError, "unknown element %s" % name
		self.current = self.current.parentNode

	def characters(self, content):
		# Discard character data for all elements except those for
		# which it is meaningful.
		if self.current.tagName in (Comment.tagName, Dim.tagName, Param.tagName, Stream.tagName, Time.tagName):
			self.current.appendData(xmlunescape(content))


class PartialLIGOLWContentHandler(LIGOLWContentHandler):
	"""
	LIGO LW content handler object that loads only those parts of the
	document matching some criteria.  Useful, for example, when one
	wishes to read only a single table from a file.
	"""
	def __init__(self, document, element_filter):
		"""
		Only those elements for which element_filter(name, attrs)
		evaluates to True, and the children of those elements, will
		be loaded.
		"""
		LIGOLWContentHandler.__init__(self, document)
		self.element_filter = element_filter
		self.depth = 0

	def startElement(self, name, attrs):
		if self.depth > 0 or self.element_filter(name, attrs):
			LIGOLWContentHandler.startElement(self, name, attrs)
			self.depth += 1

	def endElement(self, name):
		if self.depth > 0:
			self.depth -= 1
			LIGOLWContentHandler.endElement(self, name)


class FilteringLIGOLWContentHandler(LIGOLWContentHandler):
	"""
	LIGO LW content handler that loads everything but those parts of a
	document that match some criteria.  Useful, for example, when one
	wishes to read everything except a single table from a file.
	"""
	def __init__(self, document, element_filter):
		"""
		Those elements for which element_filter(name, attrs)
		evaluates to False, and the children of those elements,
		will not be loaded.
		"""
		LIGOLWContentHandler.__init__(self, document)
		self.element_filter = element_filter
		self.depth = 0

	def startElement(self, name, attrs):
		if self.depth > 0 or not self.element_filter(name, attrs):
			self.depth += 1
		else:
			LIGOLWContentHandler.startElement(self, name, attrs)

	def endElement(self, name):
		if self.depth > 0:
			self.depth -= 1
		else:
			LIGOLWContentHandler.endElement(self, name)


#
# =============================================================================
#
#                            Convenience Functions
#
# =============================================================================
#


def make_parser(handler):
	"""
	Convenience function to construct a document parser with validation
	disabled.  Document validation is a nice feature, but enabling
	validation can require the LIGO LW DTD to be downloaded from the
	LDAS document server if the DTD is not included inline in the XML.
	This requires a working connection to the internet, which would
	preclude the use of this library on slave nodes in LSC computer
	clusters.
	"""
	parser = sax.make_parser()
	parser.setContentHandler(handler)
	parser.setFeature(sax.handler.feature_validation, False)
	parser.setFeature(sax.handler.feature_external_ges, False)
	return parser
