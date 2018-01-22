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

# Download the PDF and convert to text, and cache the result
# since this is an expensive step.
import os.path, subprocess, urllib.request
cache_fn = 'nist-sp-800-53-r5.txt'
if not os.path.exists(cache_fn):
  # Download and convert to text.
  print("Downloading and converting to text...")
  cp = subprocess.run(
    ["pdftotext", "-layout", "-", "-"],
    input=urllib.request.urlopen("https://csrc.nist.gov/CSRC/media//Publications/sp/800-53/rev-5/draft/documents/sp800-53r5-draft.pdf").read(),
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
while lines:
  line = lines.pop(0)
  if line.startswith("CHAPTER THREE "): continue
  if line.startswith("DRAFT NIST SP 800-53, REVISION 5"): lines.pop(0); lines.pop(0); continue
  if line.startswith("Quick link to"): lines.pop(0); continue
  if not cur_family and not line.strip(): continue
  if line.startswith("APPENDIX A"): break # end of control sections

  # start of a control family
  if line in family_start_lines:
    cur_family = family_start_lines[line]
    lines.pop(0) # empty line
    continue

  if cur_family:
    # start of a control
    m = re.match(r"(" + re.escape(cur_family["family"]) + r"-\d+)\s+(.*)", line)
    if m:
      cur_control, cur_controlname = m.groups()
      control_texts[cur_control] = OrderedDict()
      continue

    if cur_control:
      # new control section
      m = re.match(r"(\s{10})(Control|Supplemental Guidance|Related Controls|Control Enhancements|References):\s*", line)
      if m:
        # remember what section we're in
        cur_controlpart = m.group(2)
        if cur_controlpart == "Control": cur_controlpart = "Text"
        # remove the header from the line but keep initial whitespace so indentation in the section is consistent
        line = m.group(1) + line[m.end():]

      # DOC ERROR
      if cur_control == "IA-12" and "(1)" in line:
        cur_controlpart = "Control Enhancements"

      # add text
      if cur_controlpart:
        if cur_controlpart not in control_texts[cur_control]:
          if not line.strip(): continue # don't start with an empty line
          control_texts[cur_control][cur_controlpart] = ""
        control_texts[cur_control][cur_controlpart] += line.rstrip() + "\n"
        continue

  raise ValueError(line)

# Split out the control enhancements.
control_enhancements = []
for controlnum, controldata in sorted(list(control_texts.items())):
  if controldata.get("Control Enhancements", "").strip() and not controldata["Control Enhancements"].lstrip().startswith("None."):
    cur_control_enh = None
    for line in controldata["Control Enhancements"].split("\n"):
      if not cur_control_enh and not line.strip(): continue # ignore blank at start

      # Find the start of a new control enhancement.
      m = re.match("\s*\((\d+)\)\s+(.*)", line)
      if m:
        name = m.group(2).split(" | ", 1)[-1] # if there's a pipe, it separates the control name from the control enhancement name
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

# Extract the parts of Control Enhancements sections into separate fields.
for control in control_enhancements:
  cur_controlpart = "Text"
  control_parts = OrderedDict()
  for line in control["Text"].split("\n"):
      m = re.match(r"(\s*)(Supplemental Guidance|Related Controls|References):\s*", line)
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

# Parse Appendix E
# ================

# Fast-forward to the appendix.
while lines and lines[0] != "APPENDIX E": lines.pop(0)

# Start reading lines of the table.
control_metadata = []
low_mod_high_cols = None
while True:
  line = lines.pop(0)

  # Parse column header for fixed-width column indices of the columns.
  m = re.match(r".*(LOW)\s+(MOD)\s+(HIGH)$", line)
  if m:
    low_mod_high_cols = [m.span(i) for i in range(1,4)]
    continue

  # Parse a table line.
  m = re.match(r" +(([A-Z]{2})-(\d+)(?:\((\d+)\))?)\s+(.*?)  (.*)", line)
  if m:
    control, family, controlnum, enhancement, name, attribs = m.groups()

    # Next line is a continuation of the control name?
    if lines[0].startswith("               "):
      name += " " + lines.pop(0).lstrip()

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

    # The LOW/MOD/HIGH columns are all marked with x's. Since HIGH implies MOD
    # which implies LOW, just count the number of x's at the end and strip them
    # off.
    baseline_levels = set()
    while attribs.rstrip().endswith("x") and len(baseline_levels) < 3:
      baseline_levels.add( ["HIGH", "MOD", "LOW"][len(baseline_levels)] )
      attribs = attribs[:attribs.rstrip().rindex("x")]

    # Take the attributes span only up to the character column of the LOW column
    # since the LOW/MOD/HIGH columns are unparsable for the PL family.
    attribs = attribs[:(low_mod_high_cols[0][0] - m.start(6))]

    # CA-9 and CA-9(1) have a mistake: "X" is used in place of "A".
    if control in ("CA-9", "CA-9(1)"): attribs = attribs.replace("X", "A")

    # Find the single or multi-character flags in the attributes columns.
    attribs = set(re.split(r"\s+", attribs.strip()))

    # Add back in the baseline levels.
    attribs |= baseline_levels

    # Omit withdrawn controls. The rest of the column says where the
    # control was incorporated into.
    if "W" in attribs:
      continue

    # Validate the set of attributes.
    if len(attribs - { "P", "O", "O/S", "S", "A", "LOW", "MOD", "HIGH" }) > 0:
      print("Invalid attributes", attribs, "in", line)


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
      ("attributes", OrderedDict([
        ("privacy-related", "P" in attribs),
        ("implemented-by", "organization" if "O" in attribs else "system" if "S" in attribs else "organization-and-system" if "O/S" in attribs else None),
        ("assurance", "A" in attribs),
      ])),
      ("baseline", OrderedDict([
        ("low", "LOW" in attribs),
        ("moderate", "MOD" in attribs),
        ("high", "HIGH" in attribs),        
         # There is no baseline for privacy-related controls, but as a fail-safe include if there is a baseline.
         # But don't include 
      ]) if ((attribs&{"LOW", "MOD", "HIGH"}) or ("P" not in attribs and family != "PM")) else None),
    ]))

  if line == "APPENDIX F":
    # End of table.
    break

with open("control-metadata.yaml", "w") as f:
  f.write("# NIST SP 800-53 Rev 5 August 2017 Draft Control Metadata\n")
  f.write("# extracted by GovReady PBC.\n")
  f.write("# =======================================================\n")
  rtyaml.dump(control_metadata, f)

# Write out control text and supplemental guidance.
with open("control-text.yaml", "w") as f:
  f.write("# NIST SP 800-53 Rev 5 August 2017 Draft Control Text\n")
  f.write("# extracted by GovReady PBC.\n")
  f.write("# =======================================================\n")
  f.write(rtyaml.dump(OrderedDict([
    (control["control"], OrderedDict([
      ("text", control_texts[control["control"]]["Text"]),
      ("supplemental-guidance", control_texts[control["control"]].get("Supplemental Guidance")),
    ]))
    for control in control_metadata if control["control"] in control_texts
  ])))

