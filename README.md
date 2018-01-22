NIST SP 800-53 Rev 5 as Data
============================

This repository contains data files of information automatically extracted
(scraped) from the [NIST Special Publication 800-53 Revision 5: Security and
Privacy Controls for Information Systems and Organizations, August 2017 draft](https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/draft).

There are three files in this repository:

1. `control-families.yaml` containing metadata about each control family.
2. `control-metadata.yaml` containing metadata about each control and control enhancement.
3. `control-text.yaml` containing a structured representation of each control and control enhancement's text and supplemental guidance.

## [control-families.yaml](control-families.yaml)

The data file [control-families.yaml](control-families.yaml) holds metadata on
the 20 control families, from Access Control to System and Information Integrity.
The data file was manually created.

### Excerpt

```yaml
- family: AC
  name: Access Control
  citation: 3.1
- family: AT
  name: Awareness And Training
  citation: 3.2
```

`citation` is the chapter and sub-chapter number from the NIST SP 800-53 Rev 5 document.

### Data notes

## [control-metadata.yaml](control-metadata.yaml)

The generated data file [control-metadata.yaml](control-metadata.yaml) in this
repository holds metadata for each control
and control enhancement, including the control's family, number, and name, and
its baseline and other information from Appendix E, and references from Chapter 3.

### Excerpt

```yaml
- control: AU-3(3)
  family: AU
  number: 3
  enhancement: 3
  name: Limit Personally Identifiable Information Elements
  references: ~
  attributes:
    privacy-related: true
    implemented-by: organization
    assurance: false
  baseline: ~
- control: AU-4
  family: AU
  number: 4
  enhancement: ~
  name: Audit Storage Capacity
  references: None.
  attributes:
    privacy-related: false
    implemented-by: organization-and-system
    assurance: false
  baseline:
    low: true
    moderate: true
    high: true
```

### Data notes

* `enhancement` is null (a tilde) for regular controls.
* `baseline` is null for which a baseline is not applicable, such as privacy-related controls
  and the PM family of controls.
* `privacy-related`, `assurance`, and the `baseline` fields are boolean fields which are either `true` or `false`.
* `implemented-by` is either `organization`, `system`, or `organization-and-system`.

## [control-text.yaml](control-text.yaml)

This file contains control text and supplemental guidance from Chapter 3. Assignments and Selections
in control text is represented structurally.

### Excerpt

```yaml
SA-18(2):
  text: |
    Inspect <1> <4> to detect tampering.
  parameters:
    1:
      type: Assignment
      description: systems or system components
    2:
      type: Assignment
      description: frequency
    3:
      type: Assignment
      description: indications of need for inspection
    4:
      type: Selection
      one-or-more: true
      choices:
      - at random
      - at <2>, upon <3>
  supplemental-guidance: |
    This control enhancement addresses physical and logical tampering
    and is typically applied to mobile devices, notebook computers, or other system components
    taken out of organization-controlled areas. Indications of a need for inspection include, for
    example, when individuals return from travel to high-risk locations.
```

### Data notes

* Each entry in `parameters` occurs as `<#>` in the control text or a `Selection` choice. A parameter is either an `Assignment` or a `Selection`.
* `Assignment`'s have a `description` field. These occur in the original control text as `[Assignment: organization-defined {description}]`.
* `Selection`'s have a `choices` field. Choices can contain `<#>` parameter references. Each selection has a `one-or-more` field which can be `true` or `false`.  These occur in the original control text as `[Select (one-or-more): {choice 1}; {choice 2}; ...]`.