# Python 3.5+ script to parse the NIST SP 800-53 r5 PDF.
#
# You must have "pdftotext" installed, which in Ubuntu Linux
# is in the "poppler-utils" package.
#
# You must also `pip install rtyaml`, which is a YAML wrapper
# library that produces nice looking output.

from collections import OrderedDict
import sys
import re
import rtyaml

nist_sp_800_53_pdf = "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-53r5-draft.pdf"

# Download the PDF and convert to text, and cache the result
# since this is an expensive step.
import os.path, subprocess, urllib.request
cache_fn = 'nist-sp-800-53-r5.txt'
if not os.path.exists(cache_fn):
  # Download and convert to text.
  print("Downloading and converting to text...")
  cp = subprocess.run(
    ["pdftotext", "-layout", "-", "-"],
    input=urllib.request.urlopen(nist_sp_800_53_pdf).read(),
    stdout=subprocess.PIPE)
  nist_sp_text = cp.stdout.decode("utf8") # in Py 3.6, set encoding="utf8" inside subprocess.run(...) instead

  # Save so that future runs are faster.
  with open(cache_fn, "w") as f:
    f.write(nist_sp_text)

else:
  # Load the text from the cache file.
  with open(cache_fn) as f:
    nist_sp_text = f.read()

print("Scraping PDF text...")

# Fix line wrapping in control family headers.
nist_sp_text = re.sub(r"(\n\d{3,4}.*AND)\n\d{3,4}\s+", r"\1 ", nist_sp_text)

# Split into lines.
lines = nist_sp_text.split("\n")

# Parse the Control Definitions
# =============================

# Fast-forward to the first page with control info.
control_texts = { }
families = rtyaml.load(open("control-families.yaml"))
family_start_lines = { (f["citation"] + " " + f["name"].upper()): f for f in families }
cur_family, cur_control, cur_controlname, cur_controlpart = None, None, None, None
while lines and not lines[0].endswith("PAGE 16"): lines.pop(0)
lines.pop(0)
lines.pop(0)
lines.pop(0)
while lines:
  line = lines.pop(0)

  if "CHAPTER THREE" in line:
  	# This is the start of the page header.
  	lines.pop(0)
  	lines.pop(0)
  	lines.pop(0)
  	continue

  # Remove line numbers.
  if not line: continue # not even a line number so it's not a real line
  m = re.match(r"^ ?(\d{3,5})\s*", line)
  if m:
    linenum = m.group(1)
    line = line[m.end():]

  if line.startswith("Quick link to"): lines.pop(0); continue
  if (not cur_family or not cur_control) and not line.strip(): continue
  if line.startswith("APPENDIX A"): break # end of control sections

  # start of a control family
  if line in family_start_lines:
    cur_family = family_start_lines[line]
    cur_control = None
    lines.pop(0) # empty line
    if linenum == "8608": # narrative
        while "8617" not in lines[0]: lines.pop(0)
    continue

  if cur_family:
    # start of a control
    m = re.match(r"(" + re.escape(cur_family["family"]) + r"-\d+)\s+(.*)", line)
    if m:
      cur_control, cur_controlname = m.groups()
      # Subequent all-caps lines are probably more of the control name.
      while lines and lines[0] == lines[0].upper():
        line = re.sub(r"^ ?\d{3,5}\s+", "", line) # remove line number
        cur_controlname += lines.pop(0)
      print(cur_control, cur_controlname)
      control_texts[cur_control] = OrderedDict()
      cur_controlpart = "Text"
      continue

    if cur_control:
      # new control section
      m = re.match(r"(Control|Control Enhancements|References|Related Controls):\s*", line)
      if m:
        # remember what section we're in
        if m.group(1) == "Related Controls" and cur_controlpart == "Control Enhancements":
            pass # don't break out here
        else:
            cur_controlpart = m.group(1)
            if cur_controlpart == "Control": cur_controlpart = "Text"
            print(" ", cur_controlpart)
            # remove the header from the line but keep initial whitespace so indentation in the section is consistent
            line = line[m.end():]

      # Missing "Control Enhancements" line in IA-12.
      if linenum == "6424":
        cur_controlpart = "Control Enhancements"

      # add text
      if cur_controlpart:
        if cur_controlpart not in control_texts[cur_control]:
          if not line.strip(): continue # don't start with an empty line
          control_texts[cur_control][cur_controlpart] = ""
        control_texts[cur_control][cur_controlpart] += line.rstrip() + "\n"
        continue

  raise ValueError(repr(line) + " at " + str((cur_family, cur_control, cur_controlname, cur_controlpart)))

# Split out the control enhancements.
control_enhancements = []
for controlnum, controldata in sorted(list(control_texts.items())):
  if controldata.get("Control Enhancements", "").strip() and not controldata["Control Enhancements"].lstrip().startswith("None."):
    cur_control_enh = None
    clines = controldata["Control Enhancements"].split("\n")
    while clines:
      line = clines.pop(0)
      if not cur_control_enh and not line.strip(): continue # ignore blank at start

      # Find the start of a new control enhancement.
      m = re.match("\s*\((\d+)\)\s+(.*)", line)
      if m:
        name = m.group(2).split(" | ", 1)[-1] # if there's a pipe, it separates the control name from the control enhancement name
        while clines and clines[0] == clines[0].upper():
          name += clines.pop(0)
        cur_control_enh = OrderedDict([
          ("Name", name),
          ("Text", ""),
        ])
        control_texts[controlnum + "(" + m.group(1) + ")"] = cur_control_enh
        control_enhancements.append(cur_control_enh)

      # Add text to the control enhancement.
      elif cur_control_enh:
        cur_control_enh["Text"] += line + "\n"

      else:
        raise ValueError(line)
    del controldata["Control Enhancements"]

    # Extract the 'Discussion' part of controls into a separate field.
    textparts = controldata["Text"].split("Discussion: ", 1)
    controldata["Text"] = textparts[0]
    if len(textparts) > 1:
        controldata["Discussion"] = textparts[1]

# Extract the parts of Control Enhancements sections into separate fields.
for control in control_enhancements:
  cur_controlpart = "Text"
  control_parts = OrderedDict()
  for line in control["Text"].split("\n"):
      m = re.match(r"(\s*)(Discussion|Related Controls|References):\s*", line)
      if m:
        cur_controlpart = m.group(2)
        # remove the header from the line but keep initial whitespace so indentation in the section is consistent
        line = m.group(1) + line[m.end():]
      if cur_controlpart not in control_parts:
        if line.strip() == "": continue
        control_parts[cur_controlpart] = ""
      control_parts[cur_controlpart] += line + "\n"
  control.update(control_parts)

# Clean up.
for control in control_texts.values():
  # In each control text section, remove consistent indent.
  for k, v in control.items():
    try:
      indent = min(re.search(r"\S", line+"!").start() for line in v.split("\n") if line.strip() != "")
      control[k] = "\n".join(line[indent:] for line in v.split("\n")).rstrip()
      if "\n" in control[k]: control[k] += "\n"
    except ValueError:
      pass # empty value, can't take min

  # Remove "Control Enhancements: None".
  if control.get("Control Enhancements", "").strip() == "None.":
    del control["Control Enhancements"]

  # Split.
  if control.get("Related Controls"):
    control["Related Controls"] = control["Related Controls"].rstrip(" ").rstrip(".").split(", ")

# Parse Appendix D
# ================

def clean_single_line(s):
  s = re.sub("-\n\s*", "-", s).strip() # kill newlines after hyphens
  s = re.sub("\s+", " ", s).strip() # replace whitespace with spaces
  return s

# Fast-forward to the appendix.
while lines and lines[0] != "15836   APPENDIX D": lines.pop(0)

# Start reading lines of the table.
control_metadata = []
low_mod_high_cols = None
while True:
  line = lines.pop(0)

  if "15895" in line:
    # End of table.
    break

  # Parse a table line.
  m = re.match(r" +(([A-Z]{2})-(\d+)(?:\((\d+)\))?)\s+(.*?)  (.*)", line)
  if m:
    control, family, controlnum, enhancement, name, attribs = m.groups()

    # Next line is a continuation of the control name?
    if lines[0].startswith("               "):
      name += "\n" + lines.pop(0).lstrip()
      name = clean_single_line(name)

    # Control enhancements have all-capital names, which is not very legible.
    if name == name.upper():
      # Turn into title case.
      name = name.title()

      # Now force some small words to lowercase.
      force_lower = ("at", "by", "in", "no", "of", "on", "or", "to", "and", "any", "for", "the")
      name = " ".join(
        word
         if word.lower() not in force_lower
         else
        word.lower()
        for word in name.split(" ")
      )

    # Omit withdrawn controls. The rest of the column says where the
    # control was incorporated into.
    if "W:" in attribs:
      continue

    control_metadata.append(OrderedDict([
      ("control", control),
      ("family", family),
      ("number", int(controlnum)),
      ("enhancement", int(enhancement) if enhancement is not None else None),
      ("name", name),
      # TODO: Related Controls isn't being parsed very well because pdftotext is placing
      # the Related Controls heading on the wrong line sometimes.
      # ("related-controls", control_texts[control].get("Related Controls")),
      ("references", control_texts[control].get("References")),
    ]))

with open("control-metadata.yaml", "w") as f:
  f.write("# NIST SP 800-53 Rev 5 March 2020 Draft Control Metadata\n")
  f.write("# extracted by GovReady PBC.\n")
  f.write("# =======================================================\n")
  rtyaml.dump(control_metadata, f)

# Parse selections and assignments in control text.
for control in control_texts.values():
  if "Text" not in control: continue
  parameters = OrderedDict()

  def extract_parameter(m):
    m1 = re.match(r"(list of )?(organization-|organized-|organizational )(defined|identified) (.*)", clean_single_line(m.group(1)))
    if not m1: raise ValueError(repr(clean_single_line(m.group(1))))
    parameter_id = len(parameters)+1
    parameters[parameter_id] = OrderedDict([
      ("type", "Assignment"),
      ("text", clean_single_line(m.group(0))),
      ("description", m1.group(4)),
    ])
    return "<{}>".format(parameter_id)
  control["Text"] = re.sub(r"\[Assignment[:;]?\s+([^\]]+)\]", extract_parameter, control["Text"])
  
  def extract_parameter(m):
    m1 = re.match(r"(\(one or more\))?:?(.*)", clean_single_line(m.group(2)))
    if not m1: raise ValueError(repr(clean_single_line(m.group(2))))
    parameter_id = len(parameters)+1
    parameters[parameter_id] = OrderedDict([
      ("type", "Selection"),
      ("text", clean_single_line(m.group(0))),
      ("one-or-more", bool(m1.group(1))),
      ("choices", [clean_single_line(x) for x in m1.group(2).split("; ") if clean_single_line(x)]),
    ])
    return "<{}>".format(parameter_id)
  control["Text"] = re.sub(r"\[Selection(:|\s+)([^\]]+)\]", extract_parameter, control["Text"])
  
  if parameters:
    control["parameters"] = parameters

# Write out control text and supplemental guidance.
with open("control-text.yaml", "w") as f:
  f.write("# NIST SP 800-53 Rev 5 March 2020 Draft Control Text\n")
  f.write("# extracted by GovReady PBC.\n")
  f.write("# =======================================================\n")
  f.write(rtyaml.dump(OrderedDict([
    (control["control"], OrderedDict([
      ("text", control_texts[control["control"]]["Text"]),
      ("discussion", control_texts[control["control"]].get("Discussion")),
      ("parameters", control_texts[control["control"]].get("parameters")),
    ]))
    for control in control_metadata if control["control"] in control_texts
  ])))

