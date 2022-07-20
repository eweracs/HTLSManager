# encoding: utf-8

from __future__ import division, print_function, unicode_literals
import objc
from GlyphsApp import *
from GlyphsApp.plugins import *
from vanilla import *
from vanilla import dialogs

from HTLSManagerUIElements import *
from HTLSConfigConverter import *
from HTLSLibrary import *


# TODO: Add a glyph inspector tab, with option to write new rules to font
# TODO: make rebuilding of UI faster
# TODO: Write autospace.py file
# TODO: detect conflicting rules


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
				"paramArea": int(master.customParameters["paramArea"] or 400),
				"paramDepth": int(master.customParameters["paramDepth"] or 10)
			} for master in self.font.masters
		}

		self.metricsDict = {
			glyph.name: {
				layer.associatedMasterId: [int(layer.LSB), int(layer.RSB)] for layer in glyph.layers if
				layer.isMasterLayer
			} for glyph in self.font.glyphs
		}

		# Make a list of all categories of the glyphs in the font
		self.categories = ["Letter", "Number", "Punctuation", "Symbol", "Mark"]

		# Make a list of all subcategories of the glyphs in the font
		self.sub_categories = {}
		for category in self.categories:
			self.sub_categories[category] = ["Any"]
			for glyph in self.font.glyphs:
				if glyph.category == category:
					if glyph.subCategory and glyph.subCategory not in self.sub_categories[category]:
						self.sub_categories[category].append(glyph.subCategory)

		# Make a list of all cases
		self.cases = ["Any", "Uppercase", "Lowercase", "Smallcaps", "Minor", "Other"]

		# dictionary of all font rules with key: category
		# for every category, dictionary with keys: subcategory, case, value, referenceGlyph, filter
		self.font_rules = read_config(self.font)

		# add a default value for area and depth to every master if not present
		for master in self.font.masters:
			for parameter in self.parameters_dict[master.id]:
				if parameter not in master.customParameters:
					master.customParameters[parameter] = self.parameters_dict[master.id][parameter]

		self.default_profile = {
			"Letter": {
				self.create_rule_id(): {
					"subcategory": "Any",
					"case": 1,
					"value": 1.25,
					"referenceGlyph": "H",
					"filter": ""
				},
				self.create_rule_id(): {
					"subcategory": "Any",
					"case": 2,
					"value": 1,
					"referenceGlyph": "x",
					"filter": ""
				},
				self.create_rule_id(): {
					"subcategory": "Any",
					"case": 3,
					"value": 1.2,
					"referenceGlyph": "h.sc",
					"filter": ""
				}
			},
			"Number": {
				self.create_rule_id(): {
					"subcategory": "Decimal Digit",
					"case": 1,
					"value": 1.25,
					"referenceGlyph": "H",
					"filter": ""
				},
				self.create_rule_id(): {
					"subcategory": "Decimal Digit",
					"case": 2,
					"value": 1.25,
					"referenceGlyph": "x",
					"filter": ""
				},
				self.create_rule_id(): {
					"subcategory": "Decimal Digit",
					"case": 4,
					"value": 0.8,
					"referenceGlyph": "one.dnom",
					"filter": ".dnom"
				}
			},
			"Punctuation": {},
			"Symbol": {},
			"Mark": {}
		}

		self.user_profiles = {"Default": self.default_profile}

		nsdict_userprofiles = Glyphs.defaults["com.eweracs.HTLSManager.userProfiles"]
		if nsdict_userprofiles:
			for profile_name in nsdict_userprofiles:
				if profile_name == "Default":
					continue
				self.user_profiles[profile_name] = {}
				for category in nsdict_userprofiles[profile_name]:
					self.user_profiles[profile_name][category] = {}
					for rule_id in nsdict_userprofiles[profile_name][category]:
						self.user_profiles[profile_name][category][rule_id] = dict(
							nsdict_userprofiles[profile_name][category][rule_id]
						)

		self.live_preview = True

		# make a vanilla window with two tabs: font rules and master rules
		self.w = FloatingWindow((1, 1), "HT LetterSpacer Manager")

		self.metrics = {
			"margin": 10
		}

		self.w.tabs = Tabs("auto",
		                   ["Font rules", "Master rules", "Parameters", "Glyph inspector"],
		                   callback=self.switch_tabs)

		self.fontRulesTab = self.w.tabs[0]
		self.masterRulesTab = self.w.tabs[1]
		self.parametersTab = self.w.tabs[2]
		self.glyphInspectorTab = self.w.tabs[3]

		#########################
		#                       #
		#   Font rules tab      #
		#                       #
		#########################

		self.fontRulesTab.title = TextBox("auto", "Spacing rules")

		self.fontRulesTab.profiles = Group("auto")
		self.fontRulesTab.profiles.title = TextBox("auto", "Load profile:")
		self.fontRulesTab.profiles.selector = PopUpButton("auto",
		                                                  ["Choose..."] + [profile for profile in
		                                                                   self.user_profiles],
		                                                  callback=self.load_profile)

		profiles_rules = [
			"H:|[title]-margin-[selector(160)]|",
			"V:|[title]",
			"V:|[selector]|",
		]

		self.fontRulesTab.profiles.addAutoPosSizeRules(profiles_rules, self.metrics)

		self.font_rules_groups = {}
		self.font_rules_elements = set()

		# add one vanilla group per category in self.categories
		# then add a vanilla group to self.w for each category
		for category in self.categories:
			category_group = Group("auto")
			category_group.title = TextBox("auto", category)
			# add a button to add a new rule for the category
			category_group.addButton = Button("auto", "Add rule", callback=self.add_font_rule_callback)

			stack_views = []
			for rule in self.font_rules[category]:
				stack_views.append(dict(view=HTLSFontRuleGroup(self,
				                                               self.font_rules,
				                                               category,
				                                               rule
				                                               ).rule_group))

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

			setattr(self.fontRulesTab, category, category_group)

		# add a button to import a file
		self.fontRulesTab.importButton = Button("auto", "Import config file...", callback=self.import_config_file)

		# add a button to save the current rules as a profile
		self.fontRulesTab.saveProfileButton = Button("auto", "Save profile...", callback=self.save_profile)

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

		self.fontRulesTab.addAutoPosSizeRules(font_tab_rules, self.metrics)

		#########################
		#                       #
		#  Master rules tab  #
		#                       #
		#########################

		self.masterRulesTab.title = TextBox("auto", "Rule exceptions")
		self.masterRulesTab.masterName = TextBox("auto",
		                                         "Master: %s" % self.font.selectedFontMaster.name,
		                                         alignment="right")

		self.master_rules_groups = {}
		self.master_rules_elements = set()

		# add one vanilla group per category in self.categories
		# then add a vanilla group to self.w for each category
		for category in self.categories:
			category_group = Group("auto")
			category_group.title = TextBox("auto", category)

			stack_views = []
			for rule in self.font_rules[category]:
				stack_views.append(dict(view=HTLSMasterRuleGroup(self,
				                                                 self.font_rules,
				                                                 category,
				                                                 rule).rule_group)
				                   )

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

			setattr(self.masterRulesTab, category, category_group)

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

		self.masterRulesTab.addAutoPosSizeRules(font_tab_rules, self.metrics)

		#########################
		#                       #
		#    Parameters tab     #
		#                       #
		#########################

		self.parametersTab.title = TextBox("auto", "Parameters")
		self.parametersTab.masterName = TextBox("auto",
		                                        "Master: %s" % self.font.selectedFontMaster.name,
		                                        alignment="right")

		# add an action button for options for the current master
		self.parametersTab.masterOptions = ActionButton("auto", self.action_button_items())

		self.current_area_value = self.parameters_dict[self.font.selectedFontMaster.id]["paramArea"]

		self.master_parameters_sliders = {}
		self.master_parameters_fields = {}
		self.parameters_glyph_views = {}

		self.areaSettings = HTLSParameterSlider(
			self,
			"paramArea",
			self.font.selectedFontMaster.id,
			int(self.parameters_dict[self.font.selectedFontMaster.id]["paramArea"]),
			int(self.parameters_dict[self.font.selectedFontMaster.id]["paramArea"]) - 100,
			int(self.parameters_dict[self.font.selectedFontMaster.id]["paramArea"]) + 100)

		self.depthSettings = HTLSParameterSlider(
			self,
			"paramDepth",
			self.font.selectedFontMaster.id,
			int(self.parameters_dict[self.font.selectedFontMaster.id]["paramDepth"]),
			1,
			20)

		self.parametersTab.areaSettings = self.areaSettings.slider_group
		self.parametersTab.depthSettings = self.depthSettings.slider_group

		# add one button on the left to reset the parameters to their former values
		self.parametersTab.resetParameters = Button("auto", "Reset parameters", callback=self.reset_parameters)

		# add one button on the right to save the parameters
		self.parametersTab.saveParameters = Button("auto", "Save parameters", callback=self.save_parameters)

		# add a divider
		self.parametersTab.divider = HorizontalLine("auto")

		# add two HTLS glyph views to the Parameters tab
		self.leftGlyphView = HTLSGlyphView(self, "n", self.font.glyphs, self.font.selectedFontMaster)
		self.parametersTab.leftGlyphView = self.leftGlyphView.view_group
		self.rightGlyphView = HTLSGlyphView(self, "o", self.font.glyphs, self.font.selectedFontMaster)
		self.parametersTab.rightGlyphView = self.rightGlyphView.view_group

		# add a checkbox at the botttom to toggle live preview in the current tab
		self.parametersTab.livePreview = CheckBox("auto", "Live preview", value=True, callback=self.toggle_live_preview)

		self.toggle_reset_parameters_button()

		parameters_tab_rules = [
			"H:|-margin-[title]",
			"H:[masterName]-margin-[masterOptions]-margin-|",
			"H:|-margin-[areaSettings]-margin-|",
			"H:|-margin-[depthSettings]-margin-|",
			"H:|-margin-[resetParameters]",
			"H:[saveParameters]-margin-|",
			"H:|-margin-[divider]-margin-|",
			"H:|-margin-[leftGlyphView(200)]-margin-[rightGlyphView(200)]-margin-|",
			"H:|-margin-[livePreview]",
			"V:|-margin-[masterName]",
			"V:|-margin-[masterOptions]",
			"V:|-margin-[title]-margin-[areaSettings]-margin-[depthSettings]-margin-[resetParameters]-margin-"
			"[divider]-margin-[leftGlyphView(300)]-margin-[livePreview]-margin-|",
			"V:|-margin-[title]-margin-[areaSettings]-margin-[depthSettings]-margin-[saveParameters]-margin-"
			"[divider]-margin-[rightGlyphView(==leftGlyphView)]-margin-[livePreview]-margin-|"
		]

		self.parametersTab.addAutoPosSizeRules(parameters_tab_rules, self.metrics)

		#########################
		#                       #
		#    Inspector tab      #
		#                       #
		#########################

		self.glyphInspectorTab.title = TextBox("auto", "Glyph Inspector")
		self.glyphInspectorTab.masterName = TextBox("auto",
		                                            "Master: %s" % self.font.selectedFontMaster.name,
		                                            alignment="right")

		# add a GlyphView to the Inspector tab, which always shows the currently selected glyph
		self.glyphInfo = HTLSGlyphInfo(self, "n", self.font.glyphs, self.font.selectedFontMaster)

		self.glyphInspectorTab.inspector = Group("auto")
		self.glyphInspectorTab.inspector.glyphView = GlyphView("auto",
		                                                       layer=None,
		                                                       backgroundColor=NSColor.clearColor())
		self.glyphInspectorTab.inspector.glyphName = TextBox("auto", "")
		self.glyphInspectorTab.inspector.glyphInfo = self.glyphInfo.info_group
		self.glyphInspectorTab.inspector.infoText = TextBox("auto", "", alignment="center")
		self.glyphInspectorTab.inspector.paddingTop = Group("auto")
		self.glyphInspectorTab.inspector.paddingBottom = Group("auto")

		inspector_group_rules = [
			"H:|[glyphView(200)]-margin-[glyphInfo(200)]|",
			"H:[glyphName(190)]|",
			"H:|[infoText(200)]",
			"V:|[glyphView(200)]|",
			"V:|[paddingTop]-[infoText]-[paddingBottom(==paddingTop)]|",
			"V:|[glyphName]-margin-[glyphInfo]"
		]

		self.glyphInspectorTab.inspector.addAutoPosSizeRules(inspector_group_rules, self.metrics)

		inspector_tab_rules = [
			"H:|-margin-[title]",
			"H:[masterName]-margin-|",
			"H:|-margin-[inspector]-margin-|",
			"V:|-margin-[title]-margin-[inspector]-margin-|",
			"V:|-margin-[masterName]"
		]

		self.glyphInspectorTab.addAutoPosSizeRules(inspector_tab_rules, self.metrics)
		self.update_inspector_view()

		################################################################################################################

		rules = [
			"H:|-margin-[tabs]-margin-|",
			"V:|-margin-[tabs]-margin-|",
		]

		self.load_preferences()
		self.switch_tabs(None, self.w.tabs.get())

		self.w.setDefaultButton(self.parametersTab.saveParameters)

		self.w.addAutoPosSizeRules(rules, self.metrics)
		self.w.open()
		self.w.makeKey()
		self.w.bind("close", self.close)

		Glyphs.addCallback(self.ui_update, UPDATEINTERFACE)

	@objc.python_method
	def add_font_rule_callback(self, sender):
		rule_id = self.create_rule_id()
		for category in self.categories:
			if getattr(self.fontRulesTab, category).addButton == sender:
				self.add_font_rule(category, rule_id)
				break

	@objc.python_method
	def add_font_rule(self, category, rule_id, font_rules=None):
		if font_rules:
			self.font_rules[category][rule_id] = font_rules[category][rule_id]
		else:
			self.font_rules[category][rule_id] = {
				"subcategory": "Any",
				"case": 0,
				"value": 1,
				"referenceGlyph": "",
				"filter": ""
			}

		# find the stack view for the category and add a font rule in the font view, and a master rule in the
		# master view
		getattr(self.fontRulesTab, category).stackView.appendView(
			HTLSFontRuleGroup(self, self.font_rules, category, rule_id).rule_group
		)
		getattr(self.masterRulesTab, category).stackView.appendView(
			HTLSMasterRuleGroup(self, self.font_rules, category, rule_id).rule_group
		)

		self.w.resize(632, 1)

		self.write_font_rules()

		self.fontRulesTab.profiles.selector.setItem("Choose...")

	@objc.python_method
	def remove_font_rule_callback(self, sender):
		for category in self.categories:
			for rule in list(self.font_rules[category]):
				if self.font_rules_groups[rule].removeButton == sender:
					self.remove_font_rule(category, rule)

	@objc.python_method
	def remove_font_rule(self, category, rule_id):
		getattr(self.fontRulesTab, category).stackView.removeView(self.font_rules_groups[rule_id])
		getattr(self.masterRulesTab, category).stackView.removeView(self.master_rules_groups[rule_id])

		if self.font.selectedFontMaster.userData["HTLSManagerMasterRules"]:
			if rule_id in self.font.selectedFontMaster.userData["HTLSManagerMasterRules"]:
				del self.font.selectedFontMaster.userData["HTLSManagerMasterRules"][rule_id]
			if len(self.font.selectedFontMaster.userData["HTLSManagerMasterRules"]) == 0:
				del self.font.selectedFontMaster.userData["HTLSManagerMasterRules"]
		del self.font_rules[category][rule_id]

		self.w.resize(632, 1)

		self.write_font_rules()

		self.leftGlyphView.glyphInfo.set_exception_factor()
		self.rightGlyphView.glyphInfo.set_exception_factor()
		self.fontRulesTab.profiles.selector.setItem("Choose...")

	@objc.python_method
	def update_font_rule(self, sender):
		for category in self.categories:
			for rule in self.font_rules[category]:
				for key in self.font_rules[category][rule]:
					if getattr(self.font_rules_groups[rule], key) == sender:

						self.font_rules[category][rule][key] = sender.get()

						# if the sender is the referenceGlyph, check if the glyph exists.
						if key == "referenceGlyph":
							if sender.get() not in self.font.glyphs and len(sender.get()) > 0:
								Message(title="Glyph not found",
								        message="The glyph %s does not exist in the font." % sender.get())
								sender.set("")
							self.font_rules[category][rule][key] = sender.get()

						# if the sender is for the value, make sure it is a number
						if key == "value":
							try:
								float(sender.get())
							except ValueError:
								Message(title="Value must be a number",
								        message="Please only use numbers, with periods for decimal points.")
								self.font_rules[category][rule][key] = 1
								sender.set("1")
							getattr(self.master_rules_groups[rule], key).setPlaceholder(sender.get())
							self.font_rules[category][rule][key] = float(sender.get())

						# update the text fields in the master tab
						if key == "subcategory":
							self.font_rules[category][rule][key] = self.sub_categories[category][sender.get()]
							self.master_rules_groups[rule].subcategory.set(self.sub_categories[category][sender.get()])
						elif key == "case":
							self.master_rules_groups[rule].case.set(self.cases[sender.get()])
						if key == "filter":
							getattr(self.master_rules_groups[rule], key).set(sender.get() or "Any")

						break

		self.write_font_rules()

		self.leftGlyphView.glyphInfo.set_exception_factor()
		self.rightGlyphView.glyphInfo.set_exception_factor()

	@objc.python_method
	def rebuild_font_rules(self, new_rules):
		for category in self.categories:
			for rule in list(self.font_rules[category]):
				self.remove_font_rule(category, rule)

		for category in self.categories:
			for rule_id in new_rules[category]:
				self.add_font_rule(category, rule_id, new_rules)

	@objc.python_method
	def update_master_rule(self, sender):
		if not self.font.selectedFontMaster.userData["HTLSManagerMasterRules"]:
			self.font.selectedFontMaster.userData["HTLSManagerMasterRules"] = {}
		for rule in self.master_rules_groups:
			if self.master_rules_groups[rule].value == sender:
				if sender.get() != "":
					try:
						float(sender.get())
					except ValueError:
						Message(title="Value must be a number",
						        message="Please only use numbers, with periods for decimal points.")
						sender.set("1")
					self.font.selectedFontMaster.userData["HTLSManagerMasterRules"][rule] = sender.get()
					# enable the reset button
					self.master_rules_groups[rule].resetButton.enable(True)
				else:
					del self.font.selectedFontMaster.userData["HTLSManagerMasterRules"][rule]
					# disable the reset button
					self.master_rules_groups[rule].resetButton.enable(False)
				break

		self.leftGlyphView.glyphInfo.set_exception_factor()
		self.rightGlyphView.glyphInfo.set_exception_factor()

	@objc.python_method
	def reset_master_rule(self, sender):
		for rule in self.master_rules_groups:
			if self.master_rules_groups[rule].resetButton == sender:
				self.master_rules_groups[rule].value.set("")
				self.master_rules_groups[rule].resetButton.enable(False)
				# remove the entry from the master's user data
				del self.font.selectedFontMaster.userData["HTLSManagerMasterRules"][rule]
				break

		self.leftGlyphView.glyphInfo.set_exception_factor()
		self.rightGlyphView.glyphInfo.set_exception_factor()

	@objc.python_method
	def write_font_rules(self):
		self.font.userData["com.eweracs.HTLSManager.fontRules"] = self.font_rules

	@objc.python_method
	def set_master_parameter(self, master_id, parameter, value):
		self.font.masters[master_id].customParameters[parameter] = value

	@objc.python_method
	def reset_parameters(self, sender):
		for master_id in self.parameters_dict:
			for parameter in self.parameters_dict[master_id]:
				self.font.masters[master_id].customParameters[parameter] = self.parameters_dict[master_id][parameter]

		self.apply_parameters_to_selection()
		self.update_parameter_ui()

	@objc.python_method
	def save_parameters(self, sender):
		self.parameters_dict = {
			master.id: {
				"paramArea": int(master.customParameters["paramArea"] or 400),
				"paramDepth": int(master.customParameters["paramDepth"] or 10),
			} for master in self.font.masters
		}
		self.update_parameter_ui()

	@objc.python_method
	def update_parameter_ui(self):
		self.areaSettings.ui_update(self.currentMasterID,
		                            int(self.font.selectedFontMaster.customParameters["paramArea"]),
		                            int(self.font.selectedFontMaster.customParameters["paramArea"]) - 100,
		                            int(self.font.selectedFontMaster.customParameters["paramArea"]) + 100)
		self.depthSettings.ui_update(self.currentMasterID,
		                             int(self.font.selectedFontMaster.customParameters["paramDepth"]))

		self.toggle_reset_parameters_button()

		self.leftGlyphView.update_layer(self.font.selectedFontMaster)
		self.rightGlyphView.update_layer(self.font.selectedFontMaster)

	@objc.python_method
	def link_master_callback(self, sender):
		master_to_link = None
		for master in self.font.masters:
			if master.name == sender.title():
				master_to_link = master
				break
		if master_to_link:
			self.link_master(master_to_link)

	@objc.python_method
	def link_master(self, master):
		self.font.selectedFontMaster.userData["HTLSManagerLinkedMaster"] = master.id
		self.areaSettings.ui_update(master.id, master.customParameters["paramArea"],
		                            int(master.customParameters["paramArea"]) - 100,
		                            int(master.customParameters["paramArea"]) + 100)
		self.depthSettings.ui_update(master.id, int(master.customParameters["paramDepth"]))
		self.depthSettings.master_id = self.currentMasterID

	@objc.python_method
	def interpolate_parameters_callback(self, sender):
		self.interpolation_masters = [master for master in self.font.masters if master is not
		                              self.font.selectedFontMaster]
		self.interpolation_sheet = Sheet((240, 220), self.w)

		self.interpolation_sheet.axis = Group("auto")
		# add a title and popup button to select the axis to interpolate on
		self.interpolation_sheet.axis.title = TextBox("auto", "Interpolation axis")
		self.interpolation_sheet.axis.select = PopUpButton("auto", [axis.name for axis in self.font.axes])

		# add two titles and popups to select the master to interpolate from and to
		self.interpolation_sheet.masterOne = Group("auto")
		self.interpolation_sheet.masterOne.title = TextBox("auto", "First master")
		self.interpolation_sheet.masterOne.select = PopUpButton("auto", [master.name for
		                                                                 master in self.interpolation_masters])
		self.interpolation_sheet.masterTwo = Group("auto")
		self.interpolation_sheet.masterTwo.title = TextBox("auto", "Second master")
		self.interpolation_sheet.masterTwo.select = PopUpButton("auto", [master.name for
		                                                                 master in self.interpolation_masters])

		# only enable the second master popup if there is more than one master
		self.interpolation_sheet.masterTwo.select.enable(len(self.interpolation_masters) > 1)
		# set the second master selection to the second master in the font
		if len(self.interpolation_masters) > 1:
			self.interpolation_sheet.masterTwo.select.set(1)

		# add a divider
		self.interpolation_sheet.divider = HorizontalLine("auto")

		# add a button to close the window
		self.interpolation_sheet.closeButton = Button("auto", "Close", callback=self.close_interpolation_sheet)
		self.interpolation_sheet.doneButton = Button("auto",
		                                             "Interpolate parameters",
		                                             callback=self.interpolate_parameters)

		self.interpolation_sheet.setDefaultButton(self.interpolation_sheet.doneButton)

		group_rules = [
			"H:|[title]-margin-[select(80)]|",
			"V:|[title]",
			"V:|[select]|",
		]

		sheet_rules = [
			"H:|-margin-[axis]-margin-|",
			"H:|-margin-[masterOne]-margin-|",
			"H:|-margin-[masterTwo]-margin-|",
			"H:|-margin-[divider]-margin-|",
			"H:|-margin-[closeButton]",
			"H:[doneButton]-margin-|",
			"V:|-margin-[axis]-margin-[masterOne]-margin-[masterTwo]-margin-[divider]-margin-[doneButton]-margin-|",
			"V:[closeButton]-margin-|",
		]
		try:
			self.interpolation_sheet.axis.addAutoPosSizeRules(group_rules, self.metrics)
			self.interpolation_sheet.masterOne.addAutoPosSizeRules(group_rules, self.metrics)
			self.interpolation_sheet.masterTwo.addAutoPosSizeRules(group_rules, self.metrics)
			self.interpolation_sheet.addAutoPosSizeRules(sheet_rules, self.metrics)
		except:
			import traceback
			print(traceback.format_exc())

		self.interpolation_sheet.open()

	@objc.python_method
	def interpolate_parameters(self, sender):
		axis_index = self.interpolation_sheet.axis.select.get()
		master_one = self.interpolation_masters[self.interpolation_sheet.masterOne.select.get()]
		master_two = self.interpolation_masters[self.interpolation_sheet.masterTwo.select.get()]

		if master_two == master_one:
			Message(title="Two masters needed", message="Please select two different masters.")
		else:
			# interpolate the parameters paramArea and paramDepth between the two masters using the master values of
			# the axis selected previously
			master_one_axis_value = master_one.axes[axis_index]
			master_two_axis_value = master_two.axes[axis_index]
			target_master_axis_value = self.font.selectedFontMaster.axes[axis_index]
			# get the interpolation factor
			factor = (target_master_axis_value - master_one_axis_value) / (
						master_two_axis_value - master_one_axis_value)

			for parameter in ["paramArea", "paramDepth"]:
				# get the master values of the axis
				master_one_value = int(master_one.customParameters[parameter])
				master_two_value = int(master_two.customParameters[parameter])
				# get the new value of the parameter
				new_value = master_one_value + (factor * (master_two_value - master_one_value))
				self.font.selectedFontMaster.customParameters[parameter] = int(new_value)

			self.areaSettings.ui_update(self.font.selectedFontMaster.id,
			                            int(self.font.selectedFontMaster.customParameters["paramArea"]),
			                            int(self.font.selectedFontMaster.customParameters["paramArea"]) - 100,
			                            int(self.font.selectedFontMaster.customParameters["paramArea"]) + 100)
			self.depthSettings.ui_update(self.font.selectedFontMaster.id,
			                             int(self.font.selectedFontMaster.customParameters["paramDepth"]))

		self.close_interpolation_sheet()

	@objc.python_method
	def close_interpolation_sheet(self, sender=None):
		self.interpolation_sheet.close()
		del self.interpolation_sheet

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

			# update the master name in the master rules and parameters tab title
			self.masterRulesTab.masterName.set("Master: %s" % self.font.selectedFontMaster.name)
			self.parametersTab.masterName.set("Master: %s" % self.font.selectedFontMaster.name)

			self.parametersTab.masterOptions.setItems(self.action_button_items())
			self.update_parameter_ui()
			self.leftGlyphView.glyphInfo.set_exception_factor()
			self.rightGlyphView.glyphInfo.set_exception_factor()

			# read the current master's user data and update all fields in the master rules tab accordingly
			for category in self.categories:
				for rule in self.font_rules[category]:
					for key in self.font_rules[category][rule]:
						if key == "value":
							getattr(self.master_rules_groups[rule], key).set(
								self.font_rules[category][rule][key]
							)
					if self.font.selectedFontMaster.userData["HTLSManagerMasterRules"]:
						if rule in self.font.selectedFontMaster.userData["HTLSManagerMasterRules"]:
							getattr(self.master_rules_groups[rule], "value").set(
								self.font.selectedFontMaster.userData["HTLSManagerMasterRules"][rule]
							)
							# enable the reset button
							self.master_rules_groups[rule].resetButton.enable(True)
						else:
							getattr(self.master_rules_groups[rule], "value").set("")
							# disable the reset button
							self.master_rules_groups[rule].resetButton.enable(False)
					else:
						getattr(self.master_rules_groups[rule], "value").set("")
						# disable the reset button
						self.master_rules_groups[rule].resetButton.enable(False)

		# if the parameters tab is open, update the LSB and RSB on the parameters
		if self.w.tabs.get() == 2:
			self.leftGlyphView.update_sidebearings(self.font.selectedFontMaster)
			self.rightGlyphView.update_sidebearings(self.font.selectedFontMaster)
		if self.w.tabs.get() == 3:
			self.update_inspector_view()

	@objc.python_method
	def update_inspector_view(self):
		if not self.font.selectedLayers:
			self.glyphInspectorTab.inspector.infoText.set("No layer selected")
			self.glyphInspectorTab.inspector.glyphView.layer = None
			# set all the descriptions in the glyph info to empty
			self.glyphInspectorTab.inspector.glyphName.set("(None)")
			self.glyphInspectorTab.inspector.glyphInfo.category.set("Category:")
			self.glyphInspectorTab.inspector.glyphInfo.subCategory.set("Subcategory:")
			self.glyphInspectorTab.inspector.glyphInfo.case.set("Case:")
			self.glyphInspectorTab.inspector.glyphInfo.factor.set("Factor:")
		else:
			if len(self.font.selectedLayers) > 1:
				self.glyphInspectorTab.inspector.infoText.set("Multiple layers selected")
				self.glyphInspectorTab.inspector.glyphView.layer = None
				self.glyphInspectorTab.inspector.glyphName.set("(Multiple)")
				self.glyphInspectorTab.inspector.glyphInfo.category.set("Category:")
				self.glyphInspectorTab.inspector.glyphInfo.subCategory.set("Subcategory:")
				self.glyphInspectorTab.inspector.glyphInfo.case.set("Case:")
				self.glyphInspectorTab.inspector.glyphInfo.factor.set("Factor:")
			if len(self.font.selectedLayers) == 1:
				layer = self.font.selectedLayers[0]
				self.glyphInspectorTab.inspector.infoText.set("")
				self.glyphInspectorTab.inspector.glyphView.layer = layer
				self.glyphInspectorTab.inspector.glyphName.set(layer.parent.name)
				self.glyphInspectorTab.inspector.glyphInfo.category.set("Category: %s" % layer.parent.category)
				self.glyphInspectorTab.inspector.glyphInfo.subCategory.set("Subcategory: %s" % layer.parent.subCategory)
				self.glyphInspectorTab.inspector.glyphInfo.case.set("Case: %s" % self.cases[layer.parent.case])
				self.glyphInfo.layer = layer
				self.glyphInfo.set_exception_factor()

	@objc.python_method
	def action_button_items(self):
		action_items = [
			dict(title="Copy parameters from...", items=[
				dict(title=master.name, callback=self.link_master_callback)
				for master in self.font.masters if master is not self.font.selectedFontMaster]
			     ),
			dict(title="Interpolate parameters...", callback=self.interpolate_parameters_callback)
		]

		return action_items

	@objc.python_method
	def toggle_reset_parameters_button(self):
		# check whether the area and depth rules match the saved settings, only if not, enable the reset button
		for parameter in ["paramArea", "paramDepth"]:
			if int(self.font.selectedFontMaster.customParameters[parameter]) != \
					self.parameters_dict[self.currentMasterID][parameter]:
				self.parametersTab.resetParameters.enable(True)
				break
			else:
				self.parametersTab.resetParameters.enable(False)

	@objc.python_method
	def reset_area_slider_position(self, value):
		self.areaSettings.reset_slider_position(value)

	@objc.python_method
	def toggle_live_preview(self, sender):
		self.live_preview = sender.get()

	@objc.python_method
	def apply_parameters_to_selection(self):
		# if live preview is enabled, run the HTLS engine for all glyphs in the current tab
		layers = [self.font.glyphs[self.leftGlyphView.glyph.name].layers[self.currentMasterID],
		          self.font.glyphs[self.rightGlyphView.glyph.name].layers[self.currentMasterID]]
		if not self.font.currentTab:
			self.font.newTab(layers)
		if self.live_preview:
			for layer in self.font.currentTab.layers:
				if layer not in layers:
					layers.append(layer)

		for layer in layers:
			layer_lsb, layer_rsb = HTLSEngine(layer, self).current_layer_sidebearings() or [None, None]
			if not layer_lsb or not layer_rsb:
				continue
			if self.live_preview:
				layer.LSB = layer_lsb
				layer.RSB = layer_rsb
				self.font.currentTab.forceRedraw()
			if layer.parent.name == self.leftGlyphView.glyph.name:
				self.parametersTab.leftGlyphView.currentLeftSideBearing.set(layer_lsb)
				self.parametersTab.leftGlyphView.currentRightSideBearing.set(layer_rsb)
			if layer.parent.name == self.rightGlyphView.glyph.name:
				self.parametersTab.rightGlyphView.currentLeftSideBearing.set(layer_lsb)
				self.parametersTab.rightGlyphView.currentRightSideBearing.set(layer_rsb)

	@objc.python_method
	def load_profile(self, sender):
		profile_name = sender.getItem()
		if profile_name in self.user_profiles:
			new_rules = self.user_profiles[profile_name]
			self.rebuild_font_rules(new_rules)
			self.fontRulesTab.profiles.selector.setItem(profile_name)
			self.font_rules = new_rules
			self.write_font_rules()

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
				                        informativeText="Profile \"%s\" already exists." % profile_name):
					return
				else:
					self.user_profiles[profile_name] = self.font_rules

	@objc.python_method
	def import_config_file(self, sender):

		current_path = self.font.filepath
		config_file_path = GetOpenFile(message="Import autospace.py file", filetypes=["py"], path=current_path)
		if config_file_path is None:
			return

		new_rules = convert_config_to_dict(config_file_path,
		                                   [glyph.name for glyph in self.font.glyphs],
		                                   self.sub_categories)

		self.rebuild_font_rules(new_rules)
		self.font_rules = new_rules
		self.write_font_rules()

	@objc.python_method
	def create_rule_id(self):
		return str(uuid.uuid4()).replace("-", "")

	@objc.python_method
	def load_preferences(self):
		try:
			self.w.tabs.set(Glyphs.defaults["com.eweracs.HTLSManager.tab"])
		except:
			pass
		try:
			self.leftGlyphView.set_glyph(Glyphs.defaults["com.eweracs.HTLSManager.leftGlyph"])
		except:
			pass
		try:
			self.rightGlyphView.set_glyph(Glyphs.defaults["com.eweracs.HTLSManager.rightGlyph"])
		except:
			pass

	@objc.python_method
	def write_preferences(self):
		Glyphs.defaults["com.eweracs.HTLSManager.tab"] = self.w.tabs.get()
		Glyphs.defaults["com.eweracs.HTLSManager.leftGlyph"] = self.leftGlyphView.glyph.name
		Glyphs.defaults["com.eweracs.HTLSManager.rightGlyph"] = self.rightGlyphView.glyph.name
		Glyphs.defaults["com.eweracs.HTLSManager.userProfiles"] = self.user_profiles

	@objc.python_method
	def close(self, sender):
		Glyphs.removeCallback(self.ui_update)
		self.write_preferences()

	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
