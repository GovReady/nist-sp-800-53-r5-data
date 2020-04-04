NIST SP 800-53 Rev 5 as Data
============================

This repository contains data files of information automatically extracted
(scraped) from the [NIST Special Publication 800-53 Revision 5: Security and
Privacy Controls for Information Systems and Organizations, March 2020 draft](https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/draft).

There are three files in this repository:

1. `control-families.yaml` containing metadata about each control family.
2. `control-metadata.yaml` containing metadata about each control and control enhancement.
3. `control-text.yaml` containing a structured representation of each control and control enhancement's text and supplemental guidance.

## [control-families.yaml](control-families.yaml)

The data file [control-families.yaml](control-families.yaml) holds metadata on
the 20 control families, from Access Control to System and Information Integrity.

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

This data file was manually created.

## [control-metadata.yaml](control-metadata.yaml)

The generated data file [control-metadata.yaml](control-metadata.yaml) holds metadata for each control
and control enhancement, including the control's family, number, and name.

### Excerpt

```yaml
- control: AU-3(3)
  family: AU
  number: 3
  enhancement: 3
  name: Limit Personally Identifiable Information Elements
  references: ~
- control: AU-4
  family: AU
  number: 4
  enhancement: ~
  name: Audit Log Storage Capacity
  references: None.
```

### Data notes

* `enhancement` is null (a tilde) for regular controls.

## [control-text.yaml](control-text.yaml)

This file contains control text from Chapter 3. Assignments and Selections
within control text is represented structurally.

### Excerpt

```yaml
SC-7(5):
  text: |
    Deny network communications traffic by default and allow network communications
    traffic by exception <2>.
  discussion: |
    Denying by default and allowing by exception applies to inbound and outbound
    network communications traffic. A deny-all, permit-by-exception network communications
    traffic policy ensures that only those system connections that are essential and approved are
    allowed. Deny by default, allow by exception also applies to a system that is connected to an
    external system.
  parameters:
    1:
      type: Assignment
      text: '[Assignment: organization-defined systems]'
      description: systems
    2:
      type: Selection
      text: '[Selection (one or more); at managed interfaces; for <1>]'
      one-or-more: true
      choices:
      - at managed interfaces
      - for <1>
```

### Data notes

* Each entry in `parameters` occurs as `<#>` in the control text or a `Selection` choice. A parameter is either an `Assignment` or a `Selection`.
* `Assignment`'s have a `description` field. These occur in the original control text as `[Assignment: organization-defined {description}]`.
* `Selection`'s have a `choices` field. Choices can contain `<#>` parameter references. Each selection has a `one-or-more` field which can be `true` or `false`.  These occur in the original control text as `[Select (one-or-more): {choice 1}; {choice 2}; ...]`.