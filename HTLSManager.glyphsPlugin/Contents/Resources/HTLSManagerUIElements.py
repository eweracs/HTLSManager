from vanilla import *
from GlyphsApp.UI import GlyphView
from GlyphsApp import Message
from AppKit import NSColor
from HTLSLibrary import *


class HTLSGlyphView:
	def __init__(self, parent, glyph_name, glyphs, master):
		self.parent = parent
		self.glyphs = glyphs
		self.glyph = glyphs[glyph_name]
		self.master = master
		self.layer = self.glyph.layers[master.id]
		# add a group with the following elements: a GlyphView, a ComboBox to select the glyph, one text bow each
		# to show the current left side bearing and right side bearing
		self.view_group = Group("auto")
		self.view_group.glyphView = GlyphView("auto",
		                                      layer=self.glyph.layers[self.master.id],
		                                      backgroundColor=NSColor.clearColor())
		self.view_group.glyphSelector = ComboBox("auto",
		                                         [glyph.name for glyph in self.glyphs],
		                                         callback=self.glyph_selector_callback)
		self.view_group.glyphSelector.set(self.glyph.name)

		self.view_group.originalLeftSideBearing = TextBox(
			"auto", "(%s)" % self.parent.metricsDict[self.glyph.name][self.master.id][0], alignment="left"
		)
		self.view_group.originalRightSideBearing = TextBox(
			"auto", "(%s)" % self.parent.metricsDict[self.glyph.name][self.master.id][1], alignment="right"
		)
		self.view_group.padding1 = Group("auto")
		self.view_group.padding2 = Group("auto")

		self.view_group.currentLeftSideBearing = TextBox("auto",
		                                                 self.glyph.layers[self.master.id].LSB,
		                                                 alignment="left"
		                                                 )
		self.view_group.currentRightSideBearing = TextBox("auto",
		                                                  self.glyph.layers[self.master.id].RSB,
		                                                  alignment="right"
		                                                  )

		self.glyphInfo = HTLSGlyphInfo(self.parent, glyph_name, self.glyphs, self.master)
		self.view_group.glyphInfo = self.glyphInfo.info_group

		# add rules to the glyph view groups
		view_group_rules = [
			"H:|-margin-[glyphView]-margin-|",
			"H:|-margin-[glyphSelector]-margin-|",
			"H:|-20-[originalLeftSideBearing]-margin-[originalRightSideBearing]-20-|",
			"H:|-20-[currentLeftSideBearing]-margin-[currentRightSideBearing]-20-|",
			"H:|-margin-[glyphInfo]-margin-|",
			"V:|-margin-[glyphView]-margin-[glyphSelector]-margin-[glyphInfo]-margin-|",
			"V:|-margin-[originalLeftSideBearing]",
			"V:|-margin-[originalRightSideBearing]",
			"V:|-[padding1]-[currentLeftSideBearing]-[padding2(==padding1)]-[glyphSelector]",
			"V:|-[padding1]-[currentRightSideBearing]-[padding2(==padding1)]-[glyphSelector]",
		]

		self.view_group.addAutoPosSizeRules(view_group_rules, self.parent.metrics)

	def glyph_selector_callback(self, sender):
		if sender.get() in self.glyphs:
			self.set_glyph(sender.get())

	def set_glyph(self, glyph_name):
		if glyph_name in self.glyphs:
			self.glyph = self.glyphs[glyph_name]
		self.view_group.glyphView.layer = self.glyph.layers[self.parent.font.selectedFontMaster.id]
		self.view_group.glyphSelector.set(self.glyph.name)
		self.view_group.originalLeftSideBearing.set("(%s)" % self.parent.metricsDict[self.glyph.name][
			self.master.id][0])
		self.view_group.originalRightSideBearing.set("(%s)" % self.parent.metricsDict[self.glyph.name][
			self.master.id][1])
		self.view_group.currentLeftSideBearing.set(self.glyph.layers[self.master.id].LSB)
		self.view_group.currentRightSideBearing.set(self.glyph.layers[self.master.id].RSB)

		# update case, category and subcategory
		self.view_group.glyphInfo.category.set("Category: %s" % self.glyph.category)
		self.view_group.glyphInfo.subCategory.set("Subcategory: %s" % self.glyph.subCategory)
		self.view_group.glyphInfo.case.set("Case: %s" % self.parent.cases[self.glyph.case])

		self.glyphInfo.layer = self.glyph.layers[self.master.id]
		self.glyphInfo.set_exception_factor()

	def update_layer(self, master):
		self.master = master
		self.view_group.glyphView.layer = self.glyph.layers[self.master.id]
		self.view_group.originalLeftSideBearing.set(
			"(%s)" % self.parent.metricsDict[self.glyph.name][self.master.id][0]
		)
		self.view_group.originalRightSideBearing.set(
			"(%s)" % self.parent.metricsDict[self.glyph.name][self.master.id][1]
		)

	def update_sidebearings(self, master):
		self.master = master
		self.view_group.currentLeftSideBearing.set(self.glyph.layers[self.master.id].LSB)
		self.view_group.currentRightSideBearing.set(self.glyph.layers[self.master.id].RSB)


class HTLSGlyphInfo:
	def __init__(self, parent, glyph_name, glyphs, master):
		self.parent = parent
		self.glyphs = glyphs
		self.glyph = glyphs[glyph_name]
		self.master = master
		self.layer = self.glyph.layers[master.id]

		self.info_group = Group("auto")
		self.info_group.category = TextBox("auto",
		                                   "Category: %s" % self.glyph.category,
		                                   sizeStyle="small")
		self.info_group.subCategory = TextBox("auto",
		                                      "Subcategory: %s" % self.glyph.subCategory,
		                                      sizeStyle="small")
		self.info_group.case = TextBox("auto",
		                               "Case: %s" % self.parent.cases[self.glyph.case],
		                               sizeStyle="small")
		self.info_group.factor = TextBox("auto", "Factor: 1.0", sizeStyle="small")

		self.set_exception_factor()

		info_rules = [
			"H:|-margin-[category]",
			"H:|-margin-[subCategory]",
			"H:|-margin-[case]",
			"H:|-margin-[factor]",
			"V:|-margin-[category]-[subCategory]-[case]-[factor]|",
		]

		self.info_group.addAutoPosSizeRules(info_rules, self.parent.metrics)

	def set_exception_factor(self):
		rule = HTLSEngine(self.layer).find_exception()
		if rule:
			self.info_group.factor.set("Factor: %s" % float(rule["value"]))
		else:
			self.info_group.factor.set("Factor: 1.0")


class HTLSParameterSlider:
	def __init__(self, parent, parameter, master_id, current_value, min_value, max_value):
		self.parent = parent
		self.parameter = parameter
		self.master_id = master_id
		self.current_value = current_value
		self.min_value = min_value
		self.max_value = max_value

		# add a group with the following elements: a Slider, a TextBox to show the current value of the parameter
		# to show the current left side bearing and right side bearing
		self.slider_group = Group("auto")
		self.slider_group.title = TextBox("auto",
		                                  "%s (%s)" % (parameter.replace("param", "").title(),
		                                               self.parent.parameters_dict[self.master_id][self.parameter])
		                                  )
		self.slider_group.slider = Slider("auto",
		                                  minValue=self.min_value,
		                                  maxValue=self.max_value,
		                                  callback=self.enter_parameter_callback)
		self.slider_group.field = EditText("auto",
		                                   text=self.current_value,
		                                   continuous=False,
		                                   callback=self.enter_parameter_callback)

		self.slider_group.slider.set(self.current_value)

		# add rules to the slider group
		slider_group_rules = [
			"H:|-margin-[title(70)]-margin-[slider]-margin-[field(50)]-margin-|",
			"V:|[slider]-margin-|",
			"V:|[title]",
			"V:|[field]",
		]

		self.parent.master_parameters_sliders[self.parameter] = self.slider_group.slider
		self.parent.master_parameters_fields[self.parameter] = self.slider_group.field

		self.slider_group.addAutoPosSizeRules(slider_group_rules, parent.metrics)

	def enter_parameter_callback(self, sender):
		# if the sender is the slider, update the value text field
		if sender == self.parent.master_parameters_sliders[self.parameter]:
			self.parent.master_parameters_fields[self.parameter].set(int(sender.get()))
		# if the sender is the value text field, update the slider
		elif sender == self.parent.master_parameters_fields[self.parameter]:
			if not sender.get().isnumeric():
				Message(title="Value must be a number", message="Please only enter whole number values.", )
				return
			self.parent.master_parameters_sliders[self.parameter].set(int(sender.get()))

		self.parent.set_master_parameter(self.master_id, self.parameter, int(sender.get()))
		self.parent.apply_parameters_to_selection()
		self.parent.toggle_reset_parameters_button()
		self.parent.reset_area_slider_position(sender.get())
		self.current_value = float(sender.get())

	def reset_slider_position(self, value):
		if value == self.current_value:  # check whether slider was released
			self.min_value = int(self.current_value) - 100
			self.max_value = int(self.current_value) + 100
			self.slider_group.slider.set(int(self.current_value))
			self.slider_group.slider.setMinValue(self.min_value)
			self.slider_group.slider.setMaxValue(self.max_value)

	def ui_update(self, master_id, current_value, min_value=0, max_value=20):
		self.master_id = master_id
		self.slider_group.slider.setMinValue(min_value)
		self.slider_group.slider.setMaxValue(max_value)
		self.slider_group.slider.set(current_value)
		self.slider_group.field.set(current_value)
		self.slider_group.title.set("%s (%s)" % (self.parameter.replace("param", "").title(),
		                                         self.parent.parameters_dict[self.master_id][self.parameter])
		                            )


class HTLSFontRuleGroup:
	def __init__(self, parent, font_rules, category, rule):
		self.font_rules = font_rules
		self.parent = parent
		self.category = category
		self.rule = rule

		if self.rule not in self.font_rules[self.category]:
			return

		self.current_rule = self.font_rules[self.category][self.rule]
		self.rule_group = Group("auto")
		self.rule_group.subcategory = PopUpButton("auto", self.parent.sub_categories[self.category],
		                                          callback=self.parent.update_font_rule)
		self.rule_group.case = PopUpButton("auto", self.parent.cases, callback=self.parent.update_font_rule)
		self.rule_group.value = EditText("auto",
		                                 continuous=False,
		                                 text=str(self.current_rule["value"]).replace(",", "."),
		                                 callback=self.parent.update_font_rule)
		self.rule_group.filter = EditText("auto",
		                                  continuous=False,
		                                  placeholder="None",
		                                  text=self.current_rule["filter"],
		                                  callback=self.parent.update_font_rule)
		self.rule_group.removeButton = Button("auto", "Remove rule",
		                                      callback=self.parent.remove_font_rule_callback)
		self.rule_group.referenceGlyph = ComboBox("auto",
		                                          [glyph.name for glyph in self.parent.font.glyphs],
		                                          callback=self.parent.update_font_rule)

		self.rule_group.subcategory.setItem(self.current_rule["subcategory"])
		self.rule_group.case.set(self.current_rule["case"])
		self.rule_group.referenceGlyph.set(self.current_rule["referenceGlyph"])

		group_rules = [
			"H:|-margin-[subcategory(116)]-margin-[case]-margin-[filter(==value)]-margin-[referenceGlyph(90)]-margin-"
			"[value(60)]-margin-[removeButton]|",
			"V:|[value(22)]|",
			"V:|[subcategory(==value)]|",
			"V:|[case(==value)]|",
			"V:|[referenceGlyph(==value)]|",
			"V:|[filter(==value)]|",
			"V:|[removeButton(==value)]|",
		]

		self.rule_group.addAutoPosSizeRules(group_rules, self.parent.metrics)

		# add all group elements to the elements set
		self.parent.font_rules_elements.add(self.rule_group.subcategory)
		self.parent.font_rules_elements.add(self.rule_group.case)
		self.parent.font_rules_elements.add(self.rule_group.value)
		self.parent.font_rules_elements.add(self.rule_group.referenceGlyph)
		self.parent.font_rules_elements.add(self.rule_group.filter)
		self.parent.font_rules_elements.add(self.rule_group.removeButton)

		# add the group to the rule group dictionary with ID
		self.parent.font_rules_groups[self.rule] = self.rule_group


class HTLSMasterRuleGroup:
	def __init__(self, parent, font_rules, category, rule):
		self.font_rules = font_rules
		self.parent = parent
		self.category = category
		self.rule = rule

		if len(self.font_rules[self.category][self.rule]) == 0:
			return

		self.current_rule = self.font_rules[self.category][self.rule]
		self.rule_group = Group("auto")
		self.rule_group.subcategory = TextBox("auto", self.current_rule["subcategory"])
		self.rule_group.case = TextBox("auto", self.parent.cases[self.current_rule["case"]])
		self.rule_group.filter = TextBox("auto", str(self.current_rule["filter"] or "Any"))
		self.rule_group.value = EditText("auto",
		                                 continuous=False,
		                                 text="",
		                                 placeholder=str(self.current_rule["value"]).replace(",", "."),
		                                 callback=self.parent.update_master_rule)
		self.rule_group.resetButton = Button("auto", "Reset", callback=self.parent.reset_master_rule)
		self.rule_group.resetButton.enable(False)

		# check if a value is stored in the master's user data for the current rule, if yes, use it
		master_rules = self.parent.font.selectedFontMaster.userData["HTLSManagerMasterRules"]
		if master_rules:
			if self.rule in master_rules:
				self.rule_group.value.set(str(master_rules[self.rule]).replace(",", "."))
				self.rule_group.resetButton.enable(True)

		group_rules = [
			"H:|-margin-[subcategory(90)]-margin-[case(==subcategory)]-margin-[filter(==subcategory)]-margin-"
			"[value(==subcategory)]-margin-[value(==subcategory)]-margin-[resetButton]|",
			"V:|[value(22)]|",
			"V:|[subcategory(==value)]|",
			"V:|[case(==value)]|",
			"V:|[filter(==value)]|",
			"V:|[resetButton(==value)]|",
		]

		self.rule_group.addAutoPosSizeRules(group_rules, self.parent.metrics)

		# add all group elements to the elements set
		self.parent.master_rules_elements.add(self.rule_group.subcategory)
		self.parent.master_rules_elements.add(self.rule_group.case)
		self.parent.master_rules_elements.add(self.rule_group.value)
		self.parent.master_rules_elements.add(self.rule_group.filter)
		self.parent.master_rules_elements.add(self.rule_group.resetButton)

		# add the group to the rule group dictionary with ID
		self.parent.master_rules_groups[self.rule] = self.rule_group
