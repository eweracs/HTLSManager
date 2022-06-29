from vanilla import *
from GlyphsApp.UI import GlyphView
from AppKit import NSColor


def HTLSGlyphView(parent, glyph_name, glyphs, current_master_id):

	def set_glyph(sender):
		if sender.get() in glyphs:
			viewGroup.glyphView.layer = glyphs[sender.get()].layers[current_master_id]

	# add a group with the following elements: a GlyphView, a ComboBox to select the glyph, one text bow each
	# to show the current left side bearing and right side bearing
	viewGroup = Group("auto")
	viewGroup.glyphView = GlyphView("auto",
	                                 layer=glyphs[glyph_name].layers[current_master_id],
	                                 backgroundColor=NSColor.clearColor())
	viewGroup.glyphSelector = ComboBox("auto", [glyph.name for glyph in glyphs], callback=set_glyph)
	viewGroup.leftSideBearing = TextBox("auto", "0")
	viewGroup.rightSideBearing = TextBox("auto", "0")
	viewGroup.padding1 = Group("auto")
	viewGroup.padding2 = Group("auto")

	# add rules to the glyph view groups
	view_group_rules = [
		"H:|-margin-[glyphView]-margin-|",
		"H:|-margin-[glyphSelector]-margin-|",
		"H:|-20-[leftSideBearing]-margin-[rightSideBearing]-20-|",
		"V:|-margin-[glyphView]-margin-[glyphSelector]-margin-|",
		"V:|-[padding1]-[leftSideBearing]-[padding2(==padding1)]-[glyphSelector]",
		"V:|-[padding1]-[rightSideBearing]-[padding2(==padding1)]-[glyphSelector]",
	]

	viewGroup.addAutoPosSizeRules(view_group_rules, parent.metrics)

	return viewGroup

def HTLSParameterSlider(parent, parameter, master_id, current_value, min_value, max_value):

	def set_master_parameters(sender):
		parent.set_master_parameter(master_id, parameter, int(sender.get()))
		# if the sender is the slider, update the value text field
		if sender == parent.master_parameters_sliders[parameter]:
			parent.master_parameters_fields[parameter].set(int(sender.get()))
		# if the sender is the value text field, update the slider
		elif sender == parent.master_parameters_fields[parameter]:
			parent.master_parameters_sliders[parameter].set(int(sender.get()))

	# add a group with the following elements: a Slider, a TextBox to show the current value of the parameter
	# to show the current left side bearing and right side bearing
	slider_group = Group("auto")
	slider_group.title = TextBox("auto",
	                             parameter.replace("param", "").title())
	slider_group.slider = Slider("auto",
	                             minValue=min_value,
	                             maxValue=max_value,
	                             value=current_value,
	                             callback=set_master_parameters)
	slider_group.field = EditText("auto",
	                              current_value,
	                              callback=set_master_parameters)

	# add rules to the slider group
	slider_group_rules = [
		"H:|-margin-[title]",
		"H:|-margin-[slider]-margin-[field(50)]-margin-|",
		"V:|-margin-[title]-margin-[slider]-margin-|",
		"V:[field]-margin-|",
	]

	slider_group.addAutoPosSizeRules(slider_group_rules, {"margin": 10})

	parent.master_parameters_sliders[parameter] = slider_group.slider
	parent.master_parameters_fields[parameter] = slider_group.field

	return slider_group

def HTLSFontSettingGroup(parent, category, setting):
	# return a group for the category group, using the key from the setting to find the group
	# the group contains a title, a dropdown for the subcategory, a dropdown for the case, an editable text field
	# for the value, a textfield for the reference glyph, a textfield for the filter
	# the group has a button to remove the settin

	# if the setting is empty, skip it
	if len(parent.font_settings[category][setting]) == 0:
		return False
	current_setting = parent.font_settings[category][setting]
	setting_group = Group("auto")
	setting_group.subcategory = PopUpButton("auto", parent.sub_categories, callback=parent.update_font_setting)
	setting_group.case = PopUpButton("auto", parent.cases, callback=parent.update_font_setting)
	setting_group.value = EditText("auto",
	                               continuous=False,
	                               text=current_setting["value"],
	                               callback=parent.update_font_setting)
	setting_group.referenceGlyph = ComboBox("auto",
	                                        [glyph.name for glyph in parent.font.glyphs],
	                                        callback=parent.update_font_setting)
	setting_group.filter = EditText("auto",
	                                continuous=False,
	                                placeholder="None",
	                                text=current_setting["filter"],
	                                callback=parent.update_font_setting)
	setting_group.removeButton = Button("auto", "Remove rule",
	                                    callback=parent.remove_font_setting)

	setting_group.subcategory.set(current_setting["subcategory"])
	setting_group.case.set(current_setting["case"])
	setting_group.referenceGlyph.set(current_setting["referenceGlyph"])

	group_rules = [
		"H:|-margin-[subcategory]-margin-[case]-margin-[referenceGlyph(>=90)]-margin-"
		"[filter(==value)]-margin-[value(60)]-margin-[removeButton]|",
		"V:|[value(22)]|",
		"V:|[subcategory(==value)]|",
		"V:|[case(==value)]|",
		"V:|[referenceGlyph(==value)]|",
		"V:|[filter(==value)]|",
		"V:|[removeButton(==value)]|",
	]

	setting_group.addAutoPosSizeRules(group_rules, parent.metrics)

	# add all group elements to the elements set
	parent.font_settings_elements.add(setting_group.subcategory)
	parent.font_settings_elements.add(setting_group.case)
	parent.font_settings_elements.add(setting_group.value)
	parent.font_settings_elements.add(setting_group.referenceGlyph)
	parent.font_settings_elements.add(setting_group.filter)
	parent.font_settings_elements.add(setting_group.removeButton)

	# add the group to the setting group dictionary with ID
	parent.font_settings_groups[setting] = setting_group

	return setting_group

def HTLSMasterSettingGroup(sender, category, setting):

	# if the setting is empty, skip it
	if len(sender.font_settings[category][setting]) == 0:
		return False
	current_setting = sender.font_settings[category][setting]
	setting_group = Group("auto")
	setting_group.subcategory = TextBox("auto", sender.sub_categories[current_setting["subcategory"]])
	setting_group.case = TextBox("auto", sender.cases[current_setting["case"]])
	setting_group.filter = TextBox("auto", str(current_setting["filter"] or "Any"))
	setting_group.value = EditText("auto",
	                               continuous=False,
	                               text="",
	                               placeholder=current_setting["value"],
	                               callback=sender.update_master_setting)
	setting_group.resetButton = Button("auto", "Reset", callback=sender.reset_master_setting)
	setting_group.resetButton.enable(False)


	# check if a value is stored in the mastr's user data for the current setting, if yes, use it
	if sender.font.selectedFontMaster.userData["HTLSManagerMasterSettings"]:
		if setting in sender.font.selectedFontMaster.userData["HTLSManagerMasterSettings"]:
			setting_group.value.set(sender.font.selectedFontMaster.userData["HTLSManagerMasterSettings"][setting])
			setting_group.resetButton.enable(True)

	group_rules = [
		"H:|-margin-[subcategory(90)]-margin-[case(==subcategory)]-margin-[filter(==subcategory)]-margin-"
		"[value(==subcategory)]-margin-[value(==subcategory)]-margin-[resetButton]|",
		"V:|[value(22)]|",
		"V:|[subcategory(==value)]|",
		"V:|[case(==value)]|",
		"V:|[filter(==value)]|",
		"V:|[resetButton(==value)]|",
	]

	setting_group.addAutoPosSizeRules(group_rules, sender.metrics)

	# add all group elements to the elements set
	sender.master_settings_elements.add(setting_group.subcategory)
	sender.master_settings_elements.add(setting_group.case)
	sender.master_settings_elements.add(setting_group.value)
	sender.master_settings_elements.add(setting_group.filter)
	sender.master_settings_elements.add(setting_group.resetButton)

	# add the group to the setting group dictionary with ID
	sender.master_settings_groups[setting] = setting_group

	return setting_group
