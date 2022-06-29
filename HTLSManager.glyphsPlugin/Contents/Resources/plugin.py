# encoding: utf-8

from __future__ import division, print_function, unicode_literals
import objc
from GlyphsApp import *
from GlyphsApp.plugins import *
from vanilla import *
import uuid
from HTLSManagerUIElements import *


class HTLSManager(GeneralPlugin):

	@objc.python_method
	def settings(self):
		self.name = Glyphs.localize({
			"en": "HT Letterspacer Manager",
			"de": "HT-Letterspacer-Manager",
			"es": "HT Letterspacer Manager",
			"fr": "Manager HT Letterspacer",
			"it": "HT Letterspacer Manager",
			})

	@objc.python_method
	def start(self):
		plugin_item = NSMenuItem(self.name, self.showWindow_)
		Glyphs.menu[GLYPH_MENU].append(plugin_item)

	def showWindow_(self, sender):
		self.font = Glyphs.font

		if self.font is None:
			Message("Select a font project!", "No font selected")
		# return

		self.currentMasterID = self.font.selectedFontMaster.id

		# Make a list of all categories of the glyphs in the font
		self.categories = []
		for glyph in self.font.glyphs:
			if glyph.category and glyph.category not in self.categories:
				self.categories.append(glyph.category)

		# Make a list of all subcategories of the glyphs in the font
		self.sub_categories = ["Any"]
		for glyph in self.font.glyphs:
			if glyph.subCategory and glyph.subCategory not in self.sub_categories:
				self.sub_categories.append(glyph.subCategory)

		# Make a list of all cases
		self.cases = ["Any", "Uppercase", "Lowercase", "Smallcaps", "Minor", "Other"]

		# dictionary of all font settings with key: category
		# for every category, dictionary with keys: subcategory, case, value, reference glyph, filter
		if self.font.userData["com.eweracs.HTLSManager.fontSettings"]:
			self.font_settings = dict(self.font.userData["com.eweracs.HTLSManager.fontSettings"])
		else:
			self.font_settings = {}

		# if the category is not in the dictionary, add it
		for category in self.categories:
			if category not in self.font_settings:
				self.font_settings[category] = {}

		# make a vanilla window with two tabs: font settings and master settings
		self.w = FloatingWindow((1, 1), "HT LetterSpacer Manager")

		self.metrics = {
			"margin": 10
		}

		self.w.tabs = Tabs("auto", ["Font settings", "Master settings", "Visualiser"], callback=self.switch_tabs)

		self.fontSettingsTab = self.w.tabs[0]
		self.masterSettingsTab = self.w.tabs[1]
		self.visualiserTab = self.w.tabs[2]

		#########################
		#                       #
		#   Font settings tab   #
		#                       #
		#########################

		self.fontSettingsTab.title = TextBox("auto", "Spacing rules")

		self.font_settings_groups = {}
		self.font_settings_elements = set()

		# add one vanilla group per category in self.categories
		# then add a vanilla group to self.w for each category
		for category in self.categories:
			category_group = Group("auto")
			category_group.title = TextBox("auto", category)
			# add a button to add a new setting for the category
			category_group.addButton = Button("auto", "Add rule", callback=self.add_font_setting)

			stack_views = []
			for setting in self.font_settings[category]:
				stack_views.append(dict(view=HTLSFontSettingGroup(self, category, setting)))

			category_group.stackView = VerticalStackView("auto",
			                                             views=stack_views,
			                                             spacing=10,
			                                             edgeInsets=(10, 10, 10, 10))

			group_rules = [
				"H:|-margin-[title]-margin-|",
				"H:|-margin-[stackView]|",
				"H:|-20-[addButton]",
				"V:|[title][stackView][addButton]-margin-|"

			]

			category_group.addAutoPosSizeRules(group_rules, self.metrics)

			setattr(self.fontSettingsTab, category, category_group)

		font_tab_rules = [
			"H:|-margin-[title]-margin-|",
		]

		# for each category group, add a rule to the font_tab_rules list
		for category in self.categories:
			font_tab_rules.append("H:|-margin-[%s]-margin-|" % category)
		# make a vertical rule combining all category groups
		font_tab_rules.append("V:|-margin-[title]-margin-[%s]-margin-|" % "]-margin-[".join(self.categories))

		self.fontSettingsTab.addAutoPosSizeRules(font_tab_rules, self.metrics)

		#########################
		#                       #
		#  Master settings tab  #
		#                       #
		#########################

		self.masterSettingsTab.title = TextBox("auto", "Rule exceptions")
		self.masterSettingsTab.masterName = TextBox("auto",
		                                            "Master: %s" % self.font.selectedFontMaster.name,
		                                            alignment="right")

		self.master_settings_groups = {}
		self.master_settings_elements = set()

		# add one vanilla group per category in self.categories
		# then add a vanilla group to self.w for each category
		for category in self.categories:
			category_group = Group("auto")
			category_group.title = TextBox("auto", category)

			stack_views = []
			for setting in self.font_settings[category]:
				stack_views.append(dict(view=HTLSMasterSettingGroup(self, category, setting)))

			category_group.stackView = VerticalStackView("auto",
			                                             views=stack_views,
			                                             spacing=10,
			                                             edgeInsets=(10, 10, 10, 10))

			group_rules = [
				"H:|-margin-[title]-margin-|",
				"H:|-margin-[stackView]|",
				"V:|[title][stackView]-margin-|"

			]

			category_group.addAutoPosSizeRules(group_rules, self.metrics)

			setattr(self.masterSettingsTab, category, category_group)

		font_tab_rules = [
			"H:|-margin-[title]",
			"H:[masterName]-margin-|",
			"V:|-margin-[masterName]"
		]

		# for each category group, add a rule to the font_tab_rules list
		for category in self.categories:
			font_tab_rules.append("H:|-margin-[%s]-margin-|" % category)

		# make a vertical rule combining all category groups
		font_tab_rules.append(
			"V:|-margin-[title]-margin-[%s]-margin-|" % "]-margin-[".join(self.categories)
		)

		self.masterSettingsTab.addAutoPosSizeRules(font_tab_rules, self.metrics)

		#########################
		#                       #
		#    Visualiser tab     #
		#                       #
		#########################

		self.visualiserTab.title = TextBox("auto", "Visualiser")
		self.visualiserTab.masterName = TextBox("auto",
		                                            "Master: %s" % self.font.selectedFontMaster.name,
		                                            alignment="right")

		self.master_parameters_sliders = {}
		self.master_parameters_fields = {}

		self.visualiserTab.areaSettings = HTLSParameterSlider(self, "paramArea", self.font.selectedFontMaster.id,
		                                                      1, 1, 100)

		self.visualiserTab.depthSettings = HTLSParameterSlider(self, "paramDepth", self.font.selectedFontMaster.id,
		                                                       1, 1, 20)

		# add two HTLS glyph views to the visualiser tab
		self.visualiserTab.leftGlyphView = HTLSGlyphView(self, "n",  self.font.glyphs, self.font.selectedFontMaster.id)
		self.visualiserTab.rightGlyphView = HTLSGlyphView(self, "o", self.font.glyphs, self.font.selectedFontMaster.id)

		visualiser_tab_rules = [
			"H:|-margin-[title]",
			"H:[masterName]-margin-|",
			"H:|-margin-[areaSettings]-margin-|",
			"H:|-margin-[depthSettings]-margin-|",
			"H:|-margin-[leftGlyphView(200)]-margin-[rightGlyphView(200)]-margin-|",
			"V:|-margin-[masterName]",
			"V:|-margin-[title]-margin-[areaSettings]-margin-[depthSettings]-margin-[leftGlyphView(200)]-margin-|",
			"V:|-margin-[title]-margin-[areaSettings]-margin-[depthSettings]-margin-[rightGlyphView(200)]-margin-|"
		]

		self.visualiserTab.addAutoPosSizeRules(visualiser_tab_rules, self.metrics)

		rules = [
			"H:|-margin-[tabs]-margin-|",
			"V:|-margin-[tabs]-margin-|",
		]

		self.w.addAutoPosSizeRules(rules, self.metrics)

		self.w.addAutoPosSizeRules(rules, self.metrics)
		self.w.open()
		self.w.makeKey()
		self.w.bind("close", self.close)

		Glyphs.addCallback(self.ui_update, UPDATEINTERFACE)

	@objc.python_method
	def add_font_setting(self, sender):
		setting_id = str(uuid.uuid4()).replace("-", "")
		try:
			for category in self.categories:
				if getattr(self.fontSettingsTab, category).addButton == sender:
					self.font_settings[category][setting_id] = {
						"subcategory": 0,
						"case": 0,
						"value": 1,
						"referenceGlyph": "",
						"filter": ""
					}
					break

		except Exception as e:
			print(e)

		# find the stack view for the category and add a font setting in the font view, and a master setting in the
		# master view
		for category in self.categories:
			if getattr(self.fontSettingsTab, category).addButton == sender:
				getattr(self.fontSettingsTab, category).stackView.appendView(
					HTLSFontSettingGroup(self, category, setting_id)
				)
				getattr(self.masterSettingsTab, category).stackView.appendView(
					HTLSMasterSettingGroup(self, category, setting_id)
				)
				break

		self.w.resize(632, 1)

		self.write_font_settings()

	@objc.python_method
	def remove_font_setting(self, sender):
		# remove the view that the remove button belongs to from the stack view in the font settings and master
		# settings tab
		try:
			for category in self.categories:
				for setting in self.font_settings[category]:
					if self.font_settings_groups[setting].removeButton == sender:
						getattr(self.fontSettingsTab, category).stackView.removeView(self.font_settings_groups[setting])
						getattr(self.masterSettingsTab, category).stackView.removeView(self.master_settings_groups[setting])

						del self.font_settings[category][setting]
						if setting in self.font.selectedFontMaster.userData["HTLSManagerMasterSettings"]:
							del self.font.selectedFontMaster.userData["HTLSManagerMasterSettings"][setting]

		except Exception as e:
			print(e)

		self.w.resize(632, 1)

		self.write_font_settings()

	@objc.python_method
	def update_font_setting(self, sender):
		try:
			for category in self.categories:
				for setting in self.font_settings[category]:
					for key in self.font_settings[category][setting]:
						if getattr(self.font_settings_groups[setting], key) == sender:

							self.font_settings[category][setting][key] = sender.get()

							# if the sender is the reference glyph, check if the glyph exists.
							if key == "referenceGlyph":
								if sender.get() not in self.font.glyphs and sender.get() is not "":
									Message(title="Error",
									        message="The glyph %s does not exist in the font." % sender.get())
									sender.set(self.font.glyphs[0].name)
								self.font_settings[category][setting][key] = sender.get()

							# if the sender is for the value, make sure it is a number
							if key == "value":
								try:
									float(sender.get())
								except ValueError:
									Message(title="Value must be a number",
									        message="Please only use numbers, with periods for decimal points.")
									self.font_settings[category][setting][key] = 1
									sender.set("1")
								getattr(self.master_settings_groups[setting], key).setPlaceholder(sender.get())

							# update the text fields in the master tab
							if key == "subcategory":
								self.master_settings_groups[setting].subcategory.set(self.sub_categories[sender.get()])
							elif key == "case":
								self.master_settings_groups[setting].case.set(self.cases[sender.get()])
							if key == "filter":
								getattr(self.master_settings_groups[setting], key).set(sender.get() or "Any")

							break
		except Exception as e:
			print(e)

		self.write_font_settings()

	@objc.python_method
	def update_master_setting(self, sender):
		if not self.font.selectedFontMaster.userData["HTLSManagerMasterSettings"]:
			self.font.selectedFontMaster.userData["HTLSManagerMasterSettings"] = {}
		for setting in self.master_settings_groups:
			if self.master_settings_groups[setting].value == sender:
				if sender.get() != "":
					try:
						float(sender.get())
					except ValueError:
						Message(title="Value must be a number",
						        message="Please only use numbers, with periods for decimal points.")
						sender.set("1")
					self.font.selectedFontMaster.userData["HTLSManagerMasterSettings"][setting] = sender.get()
					# enable the reset button
					self.master_settings_groups[setting].resetButton.enable(True)
				else:
					del self.font.selectedFontMaster.userData["HTLSManagerMasterSettings"][setting]
					# disable the reset button
					self.master_settings_groups[setting].resetButton.enable(False)
				break

	@objc.python_method
	def reset_master_setting(self, sender):
		for setting in self.master_settings_groups:
			if self.master_settings_groups[setting].resetButton == sender:
				self.master_settings_groups[setting].value.set("")
				self.master_settings_groups[setting].resetButton.enable(False)
				# remove the entry from the master's user data
				del self.font.selectedFontMaster.userData["HTLSManagerMasterSettings"][setting]
				break

	@objc.python_method
	def write_font_settings(self):
		self.font.userData["com.eweracs.HTLSManager.fontSettings"] = self.font_settings

	@objc.python_method
	def set_master_parameter(self, master_id, parameter, value):
		self.font.masters[master_id].customParameters[parameter] = value

	@objc.python_method
	def switch_tabs(self, sender):
		self.w.resize(1, 1)

	@objc.python_method
	def ui_update(self, sender):
		# check if the master was switched
		if self.currentMasterID != self.font.selectedFontMaster.id:
			self.currentMasterID = self.font.selectedFontMaster.id
			# update the master name in the master settings and visualiser tab title
			self.masterSettingsTab.masterName.set("Master: %s" % self.font.selectedFontMaster.name)
			self.visualiserTab.masterName.set("Master: %s" % self.font.selectedFontMaster.name)
			# read the current master's user data and update all fields in the master settings tab accordingly
			if self.font.selectedFontMaster.userData["HTLSManagerMasterSettings"]:
				for category in self.categories:
					for setting in self.font_settings[category]:
						for key in self.font_settings[category][setting]:
							if key == "value":
								getattr(self.master_settings_groups[setting], key).set(
									self.font_settings[category][setting][key]
								)
						if setting in self.font.selectedFontMaster.userData["HTLSManagerMasterSettings"]:
							getattr(self.master_settings_groups[setting], "value").set(
								self.font.selectedFontMaster.userData["HTLSManagerMasterSettings"][setting]
							)
							# enable the reset button
							self.master_settings_groups[setting].resetButton.enable(True)
						else:
							getattr(self.master_settings_groups[setting], "value").set("")
							# disable the reset button
							self.master_settings_groups[setting].resetButton.enable(False)

	@objc.python_method
	def close(self, sender):
		Glyphs.removeCallback(self.ui_update)

	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
