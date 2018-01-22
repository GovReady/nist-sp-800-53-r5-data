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

# Parse Appendix D: Control Summaries
# ===================================

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

