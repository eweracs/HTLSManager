#
# HT Letterspacer, an auto-spacing tool
# Copyright (C) 2009 - 2018, The HT Letterspacer Project Authors
# Version 1.11
from __future__ import division, print_function, unicode_literals

# program dependencies
from GlyphsApp import *
import math
from Foundation import NSMinX, NSMaxX, NSMinY, NSMaxY, NSMakePoint

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


def find_exception(config, master_rules, layer):
	category = layer.parent.category
	subcategory = layer.parent.subCategory
	case = layer.parent.case
	name = layer.parent.name

	rule = None
	for rule_id in config[category]:
		if subcategory == config[category][rule_id]["subcategory"] \
				or config[category][rule_id]["subcategory"] == "Any":
			if case == config[category][rule_id]["case"] or config[category][rule_id]["case"] == "Any":
				if config[category][rule_id]["filter"] in name:
					rule = config[category][rule_id]
					if master_rules and rule_id in master_rules:
						rule["value"] = master_rules[rule_id]

	return rule


def max_points(points):
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


def diagonize(margins_l, margins_r):
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


class HTLSEngine:

	def __init__(self, parent, config, layer):
		self.parent = parent
		self.font = layer.parent.parent
		self.master = layer.master
		self.master_rules = self.master.userData["HTLSManagerMasterRules"]
		self.config = config
		self.layer = layer
		self.reference_layer = layer
		self.minYref = None
		self.maxYref = None
		self.minY = None
		self.maxY = None
		self.layerWidth = None
		self.newR = None
		self.newL = None
		self.tabVersion = False
		self.newWidth = False
		self.width = None
		self.LSB = None
		self.RSB = None
		self.paramArea = self.master.customParameters["paramArea"] or 400
		self.paramDepth = self.master.customParameters["paramDepth"] or 12
		self.paramOver = self.master.customParameters["paramOver"] or 0
		self.paramFreq = 5
		self.xHeight = int(self.master.xHeight)
		self.angle = layer.italicAngle
		self.upm = int(self.master.font.upm)
		self.factor = 1

		self.rule = find_exception(self.config, self.master_rules, self.layer)
		if self.rule:
			self.factor = float(self.rule["value"])
			reference_glyph = self.font.glyphs[self.rule["referenceGlyph"]]
			self.reference_layer = reference_glyph.layers[self.layer.associatedMasterId]

		if self.parent.leftGlyphView.glyph.name == self.layer.parent.name:
			self.parent.parametersTab.leftGlyphView.glyphInfo.factor.set("Factor: %s" % self.factor)
		if self.parent.rightGlyphView.glyph.name == self.layer.parent.name:
			self.parent.parametersTab.rightGlyphView.glyphInfo.factor.set("Factor: %s" % self.factor)

	def overshoot(self):
		return self.xHeight * self.paramOver / 100

	def process_margins(self, l_margin, r_margin, l_extreme, r_extreme):
		# set depth
		l_margin, r_margin = self.set_depth(l_margin, r_margin, l_extreme, r_extreme)

		# close open counterforms at 45 degrees
		l_margin, r_margin = diagonize(l_margin, r_margin)
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
		try:
			amplitude_y = self.maxYref - self.minYref

			# recalculates area based on UPM
			area_upm = self.paramArea * ((self.upm / 1000) ** 2)
			# calculates proportional area
			white_area = area_upm * self.factor * 100

			prop_area = (amplitude_y * white_area) / self.xHeight

			valor = prop_area - area(polygon)
			return valor / amplitude_y
		except:
			import traceback
			print(traceback.format_exc())

	def current_layer_sidebearings(self):
		if not self.layer.name \
				or len(self.layer.components) + len(self.layer.paths) == 0 \
				or self.layer.hasAlignedWidth() \
				or self.layer.parent.leftMetricsKey \
				or self.layer.parent.rightMetricsKey \
				or "fraction" in self.layer.parent.name:
			return

		# Decompose layer for analysis, as the deeper plumbing assumes to be looking at outlines.
		layer_decomposed = self.layer.copyDecomposedLayer()
		layer_decomposed.parent = self.layer.parent
		# get reference glyph maximum points
		overshoot = self.overshoot()

		# store min and max y
		self.minYref = NSMinY(self.reference_layer.bounds) - overshoot
		self.maxYref = NSMaxY(self.reference_layer.bounds) + overshoot

		self.minY = NSMinY(layer_decomposed.bounds)
		self.maxY = NSMaxY(layer_decomposed.bounds)

		# get the margins for the full outline
		# will take measure from minY to maxY. minYref and maxYref are passed to check reference match
		# totalMarginList(layer,minY,maxY,angle,minYref,maxYref)
		l_total_margins, r_total_margins = total_margin_list(layer_decomposed,
		                                                     self.minY,
		                                                     self.maxY,
		                                                     self.angle,
		                                                     self.minYref,
		                                                     self.maxYref
		                                                     )

		# margins will be False, False if there is no measure in the reference zone, and then function stops
		if not l_total_margins and not r_total_margins:
			return

		# filtes all the margins to the reference zone
		l_zone_margins, r_zone_margins = zone_margins(l_total_margins, r_total_margins, self.minYref, self.maxYref)

		# if the font has an angle, we need to deslant
		if self.angle:
			l_zone_margins = self.deslant(l_zone_margins)
			r_zone_margins = self.deslant(r_zone_margins)

			l_total_margins = self.deslant(l_total_margins)
			r_total_margins = self.deslant(r_total_margins)

		# full shape extreme points
		l_full_extreme, r_full_extreme = max_points([l_total_margins, r_total_margins])
		# get zone extreme points
		l_extreme, r_extreme = max_points([l_zone_margins, r_zone_margins])

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
		if ".tosf" in self.layer.parent.name or ".tf" in self.layer.parent.name or self.tabVersion:
			if self.width:
				self.layerWidth = self.width
			else:
				self.layerWidth = self.layer.width

			width_shape = r_full_extreme.x - l_full_extreme.x
			width_actual = width_shape + self.newL + self.newR
			width_diff = (self.layerWidth - width_actual) / 2

			self.newL += width_diff
			self.newR += width_diff
			self.newWidth = self.layerWidth

		# end tabVersion

		# if there is a metric rule
		else:
			if self.layer.parent.leftMetricsKey is not None or self.LSB is False:
				self.newL = self.layer.LSB

			if self.layer.parent.rightMetricsKey is not None or self.RSB is False:
				self.newR = self.layer.RSB

		return self.newL, self.newR
