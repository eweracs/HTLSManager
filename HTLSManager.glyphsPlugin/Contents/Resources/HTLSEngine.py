#
# HT Letterspacer, an auto-spacing tool
# Copyright (C) 2009 - 2018, The HT Letterspacer Project Authors
# Version 1.11
from __future__ import division, print_function, unicode_literals

# program dependencies
from GlyphsApp import *
import math
import objc
from Foundation import NSMinX, NSMaxX, NSMinY, NSMaxY, NSMakePoint
from vanilla import dialogs


paramFreq = 5


# Functions
def set_sidebearings(layer, new_l, new_r, width):
	layer.LSB = new_l
	layer.RSB = new_r

	# adjusts the tabular miscalculation
	if width:
		layer.width = width


# point list area
def area(points):
	s = 0
	for ii in range(-1, len(points) - 1):
		s = s + (points[ii].x * points[ii + 1].y - points[ii + 1].x * points[ii].y)
	return abs(s) * 0.5


# get margins in Glyphs
def get_margins(layer, y):
	start_point = NSMakePoint(NSMinX(layer.bounds) - 1, y)
	end_point = NSMakePoint(NSMaxX(layer.bounds) + 1, y)

	result = layer.calculateIntersectionsStartPoint_endPoint_(start_point, end_point)
	count = len(result)
	if count <= 2:
		return None, None

	left = 1
	right = count - 2
	return result[left].pointValue().x, result[right].pointValue().x


def triangle(angle, y):
	angle = math.radians(angle)
	result = y * (math.tan(angle))
	# result = round(result)
	return result


def total_margin_list(layer, min_y, max_y, angle, min_y_ref, max_y_ref):
	# totalMarginList(layer,minY,maxY,angle,minYref,maxYref)
	# the list of margins
	y = min_y
	list_l = []
	list_r = []

	# calculate default depth, otherwise measurement is None
	# calculate paralelogram extremes
	origin = NSMinX(layer.bounds)
	endpointx = NSMaxX(layer.bounds)
	endpointy = NSMaxY(layer.bounds)

	# calculate paralelogram top left
	xpos = triangle(angle, endpointy) + origin
	# paralelogram top side width
	slant_width = (endpointx - xpos)
	# default depth
	dflt_depth = slant_width

	# result will be false if all the measured margins are emtpy (no outlines in reference zone)
	result = False

	while y <= max_y:
		lpos, rpos = get_margins(layer, y)

		# get the default margin measure at a given y position
		slant_pos_l = origin + triangle(angle, y) + dflt_depth
		slant_pos_r = origin + triangle(angle, y)

		if lpos is not None:
			list_l.append(NSMakePoint(lpos, y))
			if min_y_ref <= y <= max_y_ref:
				result = True
		else:
			list_l.append(NSMakePoint(slant_pos_l, y))

		if rpos is not None:
			list_r.append(NSMakePoint(rpos, y))
			if min_y_ref <= y <= max_y_ref:
				result = True
		else:
			list_r.append(NSMakePoint(slant_pos_r, y))

		y += paramFreq

	# if no measurements are taken, returns false and will abort in main function
	if result:
		return list_l, list_r
	else:
		return False, False


def zone_margins(l_margins, r_margins, min_y, max_y):
	# filter those outside the range
	points_filtered_l = [x for x in l_margins if min_y <= x.y <= max_y]
	points_filtered_r = [x for x in r_margins if min_y <= x.y <= max_y]

	return points_filtered_l, points_filtered_r


def width_avg(selection):
	width = 0
	for g in selection:
		width += g.width
	width = width / len(selection)
	width = int(round(width, 0))
	return width


class HTLetterspacerLib:

	def __init__(self, master, param_area=400, param_depth=12, param_over=0):
		self.xHeight = master.x_height
		self.paramArea = param_area
		self.paramDepth = param_depth
		self.paramOver = param_over
		self.paramFreq = 5
		self.tabVersion = False
		self.width = None
		self.angle = master.italicAngle
		self.LSB = None
		self.RSB = None
		self.upm = master.font.upm
		self.factor = 1

	def overshoot(self):
		return self.xHeight * self.paramOver / 100

	def max_points(self, points, min_y, max_y):
		# this function returns the extremes for a given set of points in a given zone

		# filter those outside the range
		# pointsFilteredL = [ x for x in points[0] if x.y>=minY and x.y<=maxY]
		# pointsFilteredR = [ x for x in points[0] if x.y>=minY and x.y<=maxY]

		# sort all given points by x
		sort_points_by_xl = sorted(points[0], key=lambda tup: tup[0])
		sort_points_by_xr = sorted(points[1], key=lambda tup: tup[0])

		# get the extremes position, first and last in the list
		left, lefty = sort_points_by_xl[0]
		right, righty = sort_points_by_xr[-1]

		return NSMakePoint(left, lefty), NSMakePoint(right, righty)

	def process_margins(self, l_margin, r_margin, l_extreme, r_extreme):
		# set depth
		l_margin, r_margin = self.set_depth(l_margin, r_margin, l_extreme, r_extreme)

		# close open counterforms at 45 degrees
		l_margin, r_margin = self.diagonize(l_margin, r_margin)
		l_margin = self.close_open_counters(l_margin, l_extreme)
		r_margin = self.close_open_counters(r_margin, r_extreme)

		return l_margin, r_margin

	# process lists with depth, proportional to xheight
	def set_depth(self, margins_l, margins_r, l_extreme, r_extreme):
		depth = self.xHeight * self.paramDepth / 100
		maxdepth = l_extreme.x + depth
		mindepth = r_extreme.x - depth
		margins_l = [NSMakePoint(min(p.x, maxdepth), p.y) for p in margins_l]
		margins_r = [NSMakePoint(max(p.x, mindepth), p.y) for p in margins_r]

		# add all the points at maximum depth if glyph is shorter than overshoot
		y = margins_l[0].y - self.paramFreq
		while y > self.minYref:
			margins_l.insert(0, NSMakePoint(maxdepth, y))
			margins_r.insert(0, NSMakePoint(mindepth, y))
			y -= self.paramFreq

		y = margins_l[-1].y + self.paramFreq
		while y < self.maxYref:
			margins_l.append(NSMakePoint(maxdepth, y))
			margins_r.append(NSMakePoint(mindepth, y))
			y += self.paramFreq

		# if marginsL[-1].y<(self.maxYref-paramFreq):
		# 	marginsL.append(NSMakePoint(min(p.x, maxdepth), self.maxYref))
		# 	marginsR.append(NSMakePoint(max(p.x, mindepth), self.maxYref))
		# if marginsL[0].y>(self.minYref):
		# 	marginsL.insert(0,NSMakePoint(min(p.x, maxdepth), self.minYref))
		# 	marginsR.insert(0,NSMakePoint(max(p.x, mindepth), self.minYref))

		return margins_l, margins_r

	# close counters at 45 degrees
	def diagonize(self, margins_l, margins_r):
		ystep = abs(margins_l[0].y - margins_l[1].y)
		for i in range(len(margins_l) - 1):
			if margins_l[i + 1].x - margins_l[i].x > ystep:
				margins_l[i + 1].x = margins_l[i].x + ystep
			if margins_r[i + 1].x - margins_r[i].x < -ystep:
				margins_r[i + 1].x = margins_r[i].x - ystep

		for i in reversed(range(len(margins_l) - 1)):
			if margins_l[i].x - margins_l[i + 1].x > ystep:
				margins_l[i].x = margins_l[i + 1].x + ystep
			if margins_r[i].x - margins_r[i + 1].x < -ystep:
				margins_r[i].x = margins_r[i + 1].x - ystep

		return margins_l, margins_r

	# close counterforms, creating a polygon
	def close_open_counters(self, margin, extreme):
		init_point = NSMakePoint(extreme.x, self.minYref)
		end_point = NSMakePoint(extreme.x, self.maxYref)
		margin.insert(0, init_point)
		margin.append(end_point)
		return margin

	def deslant(self, margin):
		"""De-slant a list of points (contour) at angle with the point of origin
		at half the xheight."""
		mline = self.xHeight / 2
		return [
			NSMakePoint(p.x - (p.y - mline) * math.tan(math.radians(self.angle)), p.y)
			for p in margin
		]

	def calculate_sb_value(self, polygon):
		amplitude_y = self.maxYref - self.minYref

		# recalculates area based on UPM
		area_upm = self.paramArea * ((self.upm / 1000) ** 2)
		# calculates proportional area
		white_area = area_upm * self.factor * 100

		prop_area = (amplitude_y * white_area) / self.xHeight

		valor = prop_area - area(polygon)
		return valor / amplitude_y

	def set_space(self, layer, reference_layer):
		# get reference glyph maximum points
		overshoot = self.overshoot()

		# store min and max y
		self.minYref = NSMinY(reference_layer.bounds) - overshoot
		self.maxYref = NSMaxY(reference_layer.bounds) + overshoot

		self.minY = NSMinY(layer.bounds)
		self.maxY = NSMaxY(layer.bounds)

		self.output += "Glyph: " + str(layer.parent.name) + "\n"
		self.output += "Reference layer: " + reference_layer.parent.name + " | Factor: " + str(self.factor) + "\n"

		# get the margins for the full outline
		# will take measure from minY to maxY. minYref and maxYref are passed to check reference match
		# totalMarginList(layer,minY,maxY,angle,minYref,maxYref)
		l_total_margins, r_total_margins = total_margin_list(layer, self.minY, self.maxY, self.angle, self.minYref,
		                                                     self.maxYref)

		# margins will be False, False if there is no measure in the reference zone, and then function stops
		if not l_total_margins and not r_total_margins:
			self.output += "The glyph outlines are outside the reference layer zone/height. No match with " \
			               + reference_layer.parent.name + "\n"
			return

		# filtes all the margins to the reference zone
		l_zone_margins, r_zone_margins = zone_margins(l_total_margins, r_total_margins, self.minYref, self.maxYref)

		# if the font has an angle, we need to deslant
		if self.angle:
			self.output += "Using angle: " + str(self.angle) + "\n"
			l_zone_margins = self.deslant(l_zone_margins)
			r_zone_margins = self.deslant(r_zone_margins)

			l_total_margins = self.deslant(l_total_margins)
			r_total_margins = self.deslant(r_total_margins)

		# full shape extreme points
		l_full_extreme, r_full_extreme = self.max_points([l_total_margins, r_total_margins], self.minY, self.maxY)
		# get zone extreme points
		l_extreme, r_extreme = self.max_points([l_zone_margins, r_zone_margins], self.minYref, self.maxYref)

		# create a closed polygon
		l_polygon, r_polygon = self.process_margins(l_zone_margins, r_zone_margins, l_extreme, r_extreme)

		# return

		# dif between extremes full and zone
		distance_l = math.ceil(l_extreme.x - l_full_extreme.x)
		distance_r = math.ceil(r_full_extreme.x - r_extreme.x)

		# set new sidebearings
		self.newL = math.ceil(0 - distance_l + self.calculate_sb_value(l_polygon))
		self.newR = math.ceil(0 - distance_r + self.calculate_sb_value(r_polygon))

		# tabVersion
		if ".tosf" in layer.parent.name or ".tf" in layer.parent.name or self.tabVersion:
			if self.width:
				self.layerWidth = self.width
			else:
				self.layerWidth = layer.width

			width_shape = r_full_extreme.x - l_full_extreme.x
			width_actual = width_shape + self.newL + self.newR
			width_diff = (self.layerWidth - width_actual) / 2

			self.newL += width_diff
			self.newR += width_diff
			self.newWidth = self.layerWidth

			self.output += layer.parent.name + " is tabular and adjusted at width = " + str(self.layerWidth)
		# end tabVersion

		# if there is a metric rule
		else:
			if layer.parent.leftMetricsKey is not None or self.LSB is False:
				self.newL = layer.LSB

			if layer.parent.rightMetricsKey is not None or self.RSB is False:
				self.newR = layer.RSB
		return l_polygon, r_polygon

	def space_main(self, layer, reference_layer):
		lp, rp = None, None
		try:
			self.output = ""
			if not layer.name:
				self.output += "Something went wrong!"
			elif len(layer.paths) < 1 and len(layer.components) < 1:
				self.output += "No paths in glyph " + layer.parent.name + "\n"
			# both sidebearings with metric keys
			elif layer.hasAlignedWidth():
				self.output += "Glyph (%s) has automatic alignment. Spacing not set.\n" % layer.parent.name
			elif layer.parent.leftMetricsKey is not None and layer.parent.rightMetricsKey is not None:
				self.output += "Glyph (%s) has metric keys. Spacing not set.\n" % layer.parent.name
			# if it is tabular
			# elif ".tosf" in layer.parent.name or ".tf" in layer.parent.name:
			# self.output+="Glyph "+layer.parent.name +" se supone tabular.."+"\n"
			# if it is fraction / silly condition
			elif "fraction" in layer.parent.name:
				self.output += "Glyph (%s) should be checked and done manually.\n" % layer.parent.name
			# if not...
			else:
				# Decompose layer for analysis, as the deeper plumbing assumes to be looking at outlines.
				layer_decomposed = layer.copyDecomposedLayer()
				layer_decomposed.parent = layer.parent

				# run the spacing
				space = self.set_space(layer_decomposed, reference_layer)

				# if it worked
				if space:
					lp, rp = space
					del layer_decomposed
					# store values in a list
					set_sidebearings(layer, self.newL, self.newR, self.newWidth)

			print(self.output)
			self.output = ""
		# traceback
		except Exception:
			import traceback
			print(traceback.format_exc())
		return lp, rp


class HTLetterspacerScript:

	def __init__(self, all_masters):

		self.engine = HTLetterspacerLib(0)

		self.font = Glyphs.font

		self.allMasters = all_masters

		for master in self.font.masters:
			if self.allMasters is False and self.font.selectedFontMaster is not master:
				continue

			selected_layers = set(layer.parent.layers[master.id] for layer in
			                      self.font.selectedLayers if layer.isSpecialLayer is False)

			if selected_layers is None or len(selected_layers) < 1:
				Message("Error :(", "Nothing selected", OKButton="OK")
				return

			self.mySelection = list(selected_layers)

			self.output = ""
			self.layerID = self.mySelection[0].associatedMasterId
			self.master = master
			self.config = self.font.userData["com.eweracs.HTLSManager.fontRules"]

			self.engine.upm = self.font.upm
			self.engine.angle = self.master.italicAngle
			self.engine.xHeight = self.master.xHeight

			if self.config:
				self.get_params()

				self.engine.tabVersion = False
				self.engine.LSB = True
				self.engine.RSB = True

			self.space_main()

	def get_params(self):
		for param in ["paramArea", "paramDepth", "paramOver"]:
			custom_param = self.master.customParameters[param]
			if custom_param:
				setattr(self.engine, param, float(custom_param))
				self.output += "Using master custom parameter, %s: %s\n" % (param, float(custom_param))
			else:
				self.output += "Using default parameter %s: %i\n" % (param, getattr(self.engine, param))

	def find_exception(self, category, subcategory, case):
		rule = None
		for rule_id in self.config[category]:
			if subcategory == self.config[category][rule_id]["subcategory"]:
				if case == self.config[category][rule_id]["case"]:
					if self.config[category][rule_id]["filter"] in self.glyph.name:
						rule = self.config[category][rule_id]

		return rule

	def set_g(self, layer):
		if layer.isKindOfClass_(objc.lookUpClass("GSControlLayer")):
			return
		self.output = "\\" + layer.parent.name + "\\\n" + self.output

		self.layerID = layer.associatedMasterId
		self.glyph = layer.parent
		self.category = self.glyph.category
		self.subCategory = self.glyph.subCategory
		self.case = GSGlyphInfo.stringFromCase_(self.glyph.case)
		self.script = self.glyph.script
		self.engine.reference = self.glyph.name
		self.engine.factor = 1
		self.engine.newWidth = False

		rule = self.find_exception(self.category, self.subCategory, self.case)
		if rule:
			self.engine.factor = rule["value"]
			reference_glyph = rule["referenceGlyph"]
			if reference_glyph != "":
				self.engine.reference = reference_glyph

		# check existence and contours of reference layer
		if self.font.glyphs[self.engine.reference]:
			self.referenceLayer = self.font.glyphs[self.engine.reference].layers[self.layerID]
			if len(self.referenceLayer.paths) < 1 and len(self.referenceLayer.components) < 1:
				self.output += "WARNING: The reference glyph declared (%s) doesn't have contours. Glyph (%s) was " \
				               "spaced based on its own vertical range.\n" % (self.engine.reference, self.glyph.name)
				self.referenceLayer = layer
		else:
			self.referenceLayer = layer
			self.output += "WARNING: The reference glyph declared (%s) doesn't exist. Glyph %s was spaced based on " \
			               "its own vertical range.\n" % (self.engine.reference, self.glyph.name)

	def space_main(self):
		for layer in self.mySelection:
			self.set_g(layer)
			lpolygon, rpolygon = self.engine.space_main(layer, self.referenceLayer)
		print(self.output)
		if self.font.currentTab:
			self.font.currentTab.forceRedraw()
