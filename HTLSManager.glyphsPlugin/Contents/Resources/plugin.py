# encoding: utf-8

from __future__ import division, print_function, unicode_literals
import objc
from GlyphsApp import *
from GlyphsApp.plugins import *
from vanilla import *
from vanilla import dialogs

from HTLSManagerUIElements import *
from HTLSConfigConverter import *


# TODO: Sync rules/parameters from master
# TODO: Custom profiles for font settings: resfresh view on change
# TODO: Write autospace.py file


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
			return

		self.currentMasterID = self.font.selectedFontMaster.id

		self.parameters_dict = {
			master.id: {
				"paramArea": master.customParameters["paramArea"] or 400,
				"paramDepth": master.customParameters["paramDepth"] or 10,
			} for master in self.font.masters
		}

		self.metricsDict = {
			glyph.name: {
				layer.associatedMasterId: [layer.LSB, layer.RSB] for layer in glyph.layers if layer.isMasterLayer
			} for glyph in self.font.glyphs
		}

		# Make a list of all categories of the glyphs in the font
		self.categories = ["Letter", "Number", "Punctuation", "Symbol", "Mark"]

		# Make a list of all subcategories of the glyphs in the font
		self.sub_categories = ["Any"]
		for glyph in self.font.glyphs:
			if glyph.subCategory and glyph.subCategory not in self.sub_categories:
				self.sub_categories.append(glyph.subCategory)
		self.sub_categories.append("Other")

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

		# add a default value for area and depth to every master if not present
		for master in self.font.masters:
			for parameter in self.parameters_dict[master.id]:
				if parameter not in master.customParameters:
					master.customParameters[parameter] = self.parameters_dict[master.id][parameter]

		self.default_profile = {
			"Letter": {
				str(uuid.uuid4()).replace("-", ""): {
					"subcategory": "Any",
					"case": 1,
					"value": 1.25,
					"reference glyph": "H",
					"filter": ""
				},
				str(uuid.uuid4()).replace("-", ""): {
					"subcategory": "Any",
					"case": 2,
					"value": 1,
					"reference glyph": "x",
					"filter": ""
				},
				str(uuid.uuid4()).replace("-", ""): {
					"subcategory": "Any",
					"case": 3,
					"value": 1.2,
					"reference glyph": "h.sc",
					"filter": ""
				}
			},
			"Number": {
				str(uuid.uuid4()).replace("-", ""): {
					"subcategory": "Decimal Digit",
					"case": 1,
					"value": 1.25,
					"reference glyph": "H",
					"filter": ""
				},
				str(uuid.uuid4()).replace("-", ""): {
					"subcategory": "Decimal Digit",
					"case": 2,
					"value": 1.25,
					"reference glyph": "x",
					"filter": ""
				},
				str(uuid.uuid4()).replace("-", ""): {
					"subcategory": "Decimal Digit",
					"case": 4,
					"value": 0.8,
					"reference glyph": "one.dnom",
					"filter": ".dnom"
				}
			},
			"Punctuation": {},
			"Symbol": {},
			"Mark": {}
		}

		self.user_profiles = dict(Glyphs.defaults["com.eweracs.HTLSManager.userProfiles"] or {
			"Default": self.default_profile
		})

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

		self.fontSettingsTab.profiles = Group("auto")
		self.fontSettingsTab.profiles.title = TextBox("auto", "Load profile:")
		self.fontSettingsTab.profiles.selector = PopUpButton("auto",
		                                                     ["Choose..."] + [profile for profile in
		                                                                      self.user_profiles],
		                                                     callback=self.load_profile)

		profiles_rules = [
			"H:|[title]-margin-[selector(160)]|",
			"V:|[title]",
			"V:|[selector]|",
		]

		self.fontSettingsTab.profiles.addAutoPosSizeRules(profiles_rules, self.metrics)

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
				stack_views.append(dict(view=HTLSFontSettingGroup(self, category, setting).setting_group))

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

		# add a button to import a file
		self.fontSettingsTab.importButton = Button("auto", "Import config file...", callback=self.import_config_file)

		# add a button to save the current settings as a profile
		self.fontSettingsTab.saveProfileButton = Button("auto", "Save profile...", callback=self.save_profile)

		font_tab_rules = [
			"H:|-margin-[title]-margin-|",
			"H:[saveProfileButton]-margin-[importButton]-margin-|",
			"H:[profiles]-margin-|",
			"V:|-margin-[profiles]",
			"V:[saveProfileButton]-margin-|",
		]

		# for each category group, add a rule to the font_tab_rules list
		for category in self.categories:
			font_tab_rules.append("H:|-margin-[%s]-margin-|" % category)
		# make a vertical rule combining all category groups
		font_tab_rules.append("V:|-margin-[title]-margin-[%s]-margin-[importButton]-margin-|" % "]-margin-[".join(
			self.categories))

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
				stack_views.append(dict(view=HTLSMasterSettingGroup(self, category, setting).setting_group))

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

		self.current_area_value = self.parameters_dict[self.font.selectedFontMaster.id]["paramArea"]

		self.master_parameters_sliders = {}
		self.master_parameters_fields = {}
		self.visualiser_glyph_views = {}

		self.areaSettings = HTLSParameterSlider(
			self,
			"paramArea",
			self.font.selectedFontMaster.id,
			int(self.parameters_dict[self.font.selectedFontMaster.id]["paramArea"]),
			1,
			int(self.parameters_dict[self.font.selectedFontMaster.id]["paramArea"] * 2)
		)

		self.depthSettings = HTLSParameterSlider(
			self,
			"paramDepth",
			self.font.selectedFontMaster.id,
			int(self.parameters_dict[self.font.selectedFontMaster.id]["paramDepth"]),
			1,
			20
		)

		self.visualiserTab.areaSettings = self.areaSettings.slider_group
		self.visualiserTab.depthSettings = self.depthSettings.slider_group

		# add one button on the left to reset the parameters to their former values
		self.visualiserTab.resetParameters = Button("auto", "Reset parameters", callback=self.reset_parameters)

		# add one button on the right to save the parameters
		self.visualiserTab.saveParameters = Button("auto", "Save parameters", callback=self.save_parameters)

		# add two HTLS glyph views to the visualiser tab
		self.leftGlyphView = HTLSGlyphView(self, "n", self.font.glyphs, self.font.selectedFontMaster.id)
		self.visualiserTab.leftGlyphView = self.leftGlyphView.view_group
		self.rightGlyphView = HTLSGlyphView(self, "o", self.font.glyphs, self.font.selectedFontMaster.id)
		self.visualiserTab.rightGlyphView = self.rightGlyphView.view_group

		self.toggle_reset_parameters_button()

		visualiser_tab_rules = [
			"H:|-margin-[title]",
			"H:[masterName]-margin-|",
			"H:|-margin-[areaSettings]-margin-|",
			"H:|-margin-[depthSettings]-margin-|",
			"H:|-margin-[resetParameters]",
			"H:[saveParameters]-margin-|",
			"H:|-margin-[leftGlyphView(200)]-margin-[rightGlyphView(200)]-margin-|",
			"V:|-margin-[masterName]",
			"V:|-margin-[title]-margin-[areaSettings]-margin-[depthSettings]-margin-[resetParameters]-margin-["
			"leftGlyphView(200)]-margin-|",
			"V:|-margin-[title]-margin-[areaSettings]-margin-[depthSettings]-margin-[saveParameters]-margin-["
			"rightGlyphView(200)]-margin-|"
		]

		self.visualiserTab.addAutoPosSizeRules(visualiser_tab_rules, self.metrics)

		rules = [
			"H:|-margin-[tabs]-margin-|",
			"V:|-margin-[tabs]-margin-|",
		]

		self.load_preferences()
		self.switch_tabs(None, self.w.tabs.get())

		self.w.setDefaultButton(self.visualiserTab.saveParameters)

		self.w.addAutoPosSizeRules(rules, self.metrics)
		self.w.open()
		self.w.makeKey()
		self.w.bind("close", self.close)

		Glyphs.addCallback(self.ui_update, UPDATEINTERFACE)

	@objc.python_method
	def add_font_setting(self, sender):
		setting_id = str(uuid.uuid4()).replace("-", "")
		for category in self.categories:
			if getattr(self.fontSettingsTab, category).addButton == sender:
				self.font_settings[category][setting_id] = {
					"subcategory": "Any",
					"case": 0,
					"value": 1,
					"referenceGlyph": "",
					"filter": ""
				}
				break

		# find the stack view for the category and add a font setting in the font view, and a master setting in the
		# master view
		for category in self.categories:
			if getattr(self.fontSettingsTab, category).addButton == sender:
				getattr(self.fontSettingsTab, category).stackView.appendView(
					HTLSFontSettingGroup(self, category, setting_id).setting_group
				)
				getattr(self.masterSettingsTab, category).stackView.appendView(
					HTLSMasterSettingGroup(self, category, setting_id).setting_group
				)
				break

		self.w.resize(632, 1)

		self.write_font_settings()

	@objc.python_method
	def remove_font_setting(self, sender):
		# remove the view that the remove button belongs to from the stack view in the font settings and master
		# settings tab
		for category in self.categories:
			for setting in self.font_settings[category]:
				if self.font_settings_groups[setting].removeButton == sender:
					getattr(self.fontSettingsTab, category).stackView.removeView(self.font_settings_groups[setting])
					getattr(self.masterSettingsTab, category).stackView.removeView(self.master_settings_groups[setting])

					if self.font.selectedFontMaster.userData["HTLSManagerMasterSettings"]:
						if setting in self.font.selectedFontMaster.userData["HTLSManagerMasterSettings"]:
							del self.font.selectedFontMaster.userData["HTLSManagerMasterSettings"][setting]
						if len(self.font.selectedFontMaster.userData["HTLSManagerMasterSettings"]) == 0:
							del self.font.selectedFontMaster.userData["HTLSManagerMasterSettings"]
					del self.font_settings[category][setting]
					break

		self.w.resize(632, 1)

		self.write_font_settings()

	@objc.python_method
	def update_font_setting(self, sender):
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
	def reset_parameters(self, sender):
		for master_id in self.parameters_dict:
			for parameter in self.parameters_dict[master_id]:
				self.font.masters[master_id].customParameters[parameter] = self.parameters_dict[master_id][parameter]

		self.update_parameter_ui()

	@objc.python_method
	def save_parameters(self, sender):
		self.parameters_dict = {
			master.id: {
				"paramArea": master.customParameters["paramArea"] or 400,
				"paramDepth": master.customParameters["paramDepth"] or 10,
			} for master in self.font.masters
		}
		self.update_parameter_ui()

	@objc.python_method
	def update_parameter_ui(self):
		self.areaSettings.ui_update(self.currentMasterID,
		                            int(self.font.selectedFontMaster.customParameters["paramArea"]),
		                            1,
		                            int(self.font.selectedFontMaster.customParameters["paramArea"]) * 2
		                            )
		self.depthSettings.ui_update(self.currentMasterID,
		                             int(self.font.selectedFontMaster.customParameters["paramDepth"]),
		                             1,
		                             20
		                             )

		self.toggle_reset_parameters_button()

		self.leftGlyphView.update_layer(self.currentMasterID)
		self.rightGlyphView.update_layer(self.currentMasterID)

	@objc.python_method
	def switch_tabs(self, sender, tab_index=None):
		if not tab_index and sender:
			tab_index = sender.get() or 0
		if tab_index == 0:
			self.w.resize(632, 1)
		if tab_index == 1:
			self.w.resize(522, 1)
		if tab_index == 2:
			self.w.resize(1, 1)

	@objc.python_method
	def ui_update(self, sender):
		# check if the master was switched
		if self.currentMasterID != self.font.selectedFontMaster.id:
			self.currentMasterID = self.font.selectedFontMaster.id

			# update the master name in the master settings and visualiser tab title
			self.masterSettingsTab.masterName.set("Master: %s" % self.font.selectedFontMaster.name)
			self.visualiserTab.masterName.set("Master: %s" % self.font.selectedFontMaster.name)

			self.update_parameter_ui()

			# read the current master's user data and update all fields in the master settings tab accordingly
			for category in self.categories:
				for setting in self.font_settings[category]:
					for key in self.font_settings[category][setting]:
						if key == "value":
							getattr(self.master_settings_groups[setting], key).set(
								self.font_settings[category][setting][key]
							)
					if self.font.selectedFontMaster.userData["HTLSManagerMasterSettings"]:
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
					else:
						getattr(self.master_settings_groups[setting], "value").set("")
						# disable the reset button
						self.master_settings_groups[setting].resetButton.enable(False)

	@objc.python_method
	def toggle_reset_parameters_button(self):
		# check whether the area and depth settings match the saved settings, only if not, enable the reset button
		for parameter in ["paramArea", "paramDepth"]:
			if self.font.selectedFontMaster.customParameters[parameter] != \
					self.parameters_dict[self.currentMasterID][parameter]:
				self.visualiserTab.resetParameters.enable(True)
				break
			else:
				self.visualiserTab.resetParameters.enable(False)

	@objc.python_method
	def reset_area_slider_position(self, value):
		self.areaSettings.reset_slider_position(value)

	@objc.python_method
	def load_profile(self, sender):
		if sender.getItem() in self.user_profiles:
			self.font_settings = self.user_profiles[sender.getItem()]

	@objc.python_method
	def save_profile(self, sender):
		proposed_name = "New profile"
		index = 2
		if proposed_name in self.user_profiles:
			while True:
				proposed_name = "New profile %s" % index
				if proposed_name not in self.user_profiles:
					break
				index += 1

		profile_name = AskString("Profile name:", proposed_name, "Save HTLS profile")

		if profile_name and len(profile_name) > 0:
			if profile_name in self.user_profiles:
				if not dialogs.askYesNo(messageText="Overwrite profile?",
				                        informativeText="Profile '%s' already exists." % profile_name):
					return
				else:
					self.user_profiles[profile_name] = self.font_settings

	@objc.python_method
	def import_config_file(self, sender):

		current_path = self.font.filepath
		config_file_path = GetOpenFile(message="Import autospace.py file", filetypes=["py"], path=current_path)
		if config_file_path is None:
			return

		self.font.userData["com.eweracs.HTLSManager.fontSettings"] = convert_config_to_dict(
			config_file_path, [glyph.name for glyph in self.font.glyphs])

	@objc.python_method
	def load_preferences(self):
		try:
			self.w.tabs.set(Glyphs.defaults["com.eweracs.HTLSManager.tab"])
		except:
			pass
		try:
			self.leftGlyphView.set_glyph(Glyphs.defaults["com.eweracs.HTLSManager.leftGlyph"])
			self.rightGlyphView.set_glyph(Glyphs.defaults["com.eweracs.HTLSManager.rightGlyph"])
		except:
			pass

	@objc.python_method
	def write_preferences(self):
		Glyphs.defaults["com.eweracs.HTLSManager.tab"] = self.w.tabs.get()
		Glyphs.defaults["com.eweracs.HTLSManager.leftGlyph"] = self.leftGlyphView.glyph_name
		Glyphs.defaults["com.eweracs.HTLSManager.rightGlyph"] = self.rightGlyphView.glyph_name
		Glyphs.defaults["com.eweracs.HTLSManager.userProfiles"] = self.user_profiles

	@objc.python_method
	def close(self, sender):
		Glyphs.removeCallback(self.ui_update)
		self.write_preferences()

	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
