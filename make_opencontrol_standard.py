# Convert the control YAML files to an OpenControl Standard file.

from collections import OrderedDict
import re

import rtyaml

# Load control data.

control_metadata = rtyaml.load(open("control-metadata.yaml"))
control_text = rtyaml.load(open("control-text.yaml"))
control_families = rtyaml.load(open("control-families.yaml"))

# Pre-process.

control_family_names = { f["family"]: f["name"] for f in control_families }

# Generate standard.

standard = OrderedDict()
standard["name"] = "NIST-800-53r5"
for control in control_metadata:
	text = control_text[control["control"]]["text"]

	# Put back parsed-out parameters.
	def parameter_replacer(m):
		print(control, control_text[control["control"]], m.group(1))
		return control_text[control["control"]]["parameters"][int(m.group(1))]["text"]
	text = re.sub(r"<(\d+)>", parameter_replacer, text)

	standard[control["control"]] = OrderedDict([
		("description", text),
		("family", control["family"] + " - " + control_family_names[control["family"]]),
		("name", control["name"]),
	])

# Write out.

with open("opencontrol-standard.yaml", "w") as f:
	rtyaml.dump(standard, f)