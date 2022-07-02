from GlyphsApp import Glyphs, Message
import uuid

case_dict = {
		"*": 0,
		"upper": 1,
		"lower": 2,
		"smallCaps": 3,
		"minor": 4,
		"Other": 5
}

categories = ["Letter", "Number", "Separator", "Punctuation", "Symbol", "Mark"]


def convert_config_to_dict(config_file_path, glyphs):
	"""
	Converts a config file to a dictionary.
	"""

	config_dict = {category: {} for category in categories}
	missing_references = []
	ignored_rules = 0

	try:
		with open(config_file_path) as config_file:
			for line in config_file:
				if line.startswith("#") or len(line) < 12:
					continue
				key = str(uuid.uuid4()).replace("-", "")
				category = line.split(",")[1]
				config_dict[category][key] = {}
				config_dict[category][key]["subcategory"] = line.split(",")[2].replace("*", "Any")
				config_dict[category][key]["case"] = case_dict[line.split(",")[3]]
				config_dict[category][key]["value"] = line.split(",")[4]
				config_dict[category][key]["referenceGlyph"] = line.split(",")[5].replace("*", "")
				config_dict[category][key]["filter"] = line.split(",")[6].replace("*", "")

				reference_glyph = config_dict[category][key]["referenceGlyph"]
				if len(reference_glyph) > 0 and reference_glyph not in glyphs:
					print("Ignoring rule with missing reference glyph: %s" % config_dict[category][key][
						"referenceGlyph"])
					if reference_glyph not in missing_references:
						missing_references.append(reference_glyph)
					del config_dict[category][key]
					ignored_rules += 1

		if len(missing_references) > 0:
			notification_message = "%s rules ignored. The following reference glyphs were not found " \
			                       "in the font: %s" % (ignored_rules, ", ".join(missing_references))
		else:
			notification_message = "No invalid rules detected."

		Glyphs.showNotification("Import successful", notification_message)

	except Exception as e:
		print(e)
		Message("The config file seems to be invalid", "Import failed")
		return None

	return config_dict


def convert_dict_to_config(config_dict, config_file_path):
	"""
	Converts a dictionary to a config file.
	"""

	inverted_case_dict = {index: value for value, index in interpreter_dict}

	try:
		with open(config_file_path, "w") as config_file:
			for category in categories:
				for key in config_dict[category]:
					config_file.write(
						"*,%s,%s,%s,%s,%s\n" % (config_dict[category][key]["subcategory"],
						                        inverted_case_dict[config_dict[category][key]["case"]],
						                        config_dict[category][key]["value"],
						                        config_dict[category][key]["referenceGlyph"] or "*",
						                        config_dict[category][key]["filter"] or "*"))

	except Exception as e:
		print(e)
		Message("There was an error converting the config. Check macro window for details.", "Export failed")
		return None

	return config_dict