NIST SP 800-53 Rev 5 as Data
============================

This repository contains data files of information automatically extracted
(scraped) from the [NIST Special Publication 800-53 Revision 5: Security and
Privacy Controls for Information Systems and Organizations, August 2017 draft](https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/draft).

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
its baseline and other information from Appendix E.

### Excerpt

```yaml
- control: AU-3(3)
  family: AU
  number: 3
  enhancement: 3
  name: Limit Personally Identifiable Information Elements
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
