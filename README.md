# OSED - Open Standard Entity Description

Standard description of entities and inter-entity relations defined for a
system

# About

This document attempts to standardize machine-readable description of nouns
(entities) and, relations among nouns - applicable to function of a system - 
while maintaining high degree of human-readability. The rules specified in this
document collectively form the standard.

One obvious use case is the abstraction of database schema definitions. Single
OSED document can be used to generate schema definitions for multiple database
management systems (DBMS) using OSED-compliant parsers. This can be useful for
switching to different DBMS during initial development phase. Extra handling
may be required to attain complete inter-operability. OSED can also be used to
document nouns - with specific semantics within a system - without defining
workflows.

It can be helpful to draft OSED documents, prior to implementation of system
function. OSED documents should be versioned and tracked using version control.
Solutions Architects, Business or Technical Analysts or any individual involved
in translating business requirement into system design may choose to draft an
OSED document.

###### Version 0.1.0

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL
NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED",
"MAY", and "OPTIONAL" in this document are to be interpreted as
described in
[BCP 14](https://www.rfc-editor.org/bcp/bcp14)
[[RFC2119](https://www.rfc-editor.org/rfc/rfc2119)]
[[RFC8174](https://www.rfc-editor.org/rfc/rfc8174)]
when, and only when, they appear in all capitals, as shown here.

# Specification

All text in an OSED document MUST adhere to specifications defined in this
section. OSED documents are presented using [YAML](https://yaml.org/). A YAML
node containing the structure of an entity is a `Description`(`description`),
in the context of an OSED document.

## Semantic Node

A **semanticNode** is a recursive structure used in both
[`universals`](#universals) and [`particulars`](#particulars). Each
**semanticNode** MUST be one of:

- A string
- A dictionary (map) with **exactly one** key-value pair, where:
  - The key MUST be a string
  - The value MUST be a list of **semanticNode**s

This structure allows arbitrarily nested maps with meaningful names, but does
**not permit unnamed lists**, or maps with more than one key. This enables
forming named groups of nouns while ensuring semantic clarity and simplicity.

## Top level entry

A top level entry is an entry in OSED document that is not nested inside any
other entry. It can however be referenced from nested locations. Each top level
entry MUST either be an [`entityDescription`](#entity-description) or a
key-value pair with one of four reserved words as the key. The words
[`osed`](#osed), [`entities`](#entities), [`universals`](#universals) and
[`particulars`](#particulars) are reserved in OSED and have special meaning.
These SHOULD NOT be part any [`entityDescription`](#entity-description).

| Reserved word | Type    | Required | Notes                            |
|---------------|---------|----------|----------------------------------|
| `osed`        | string  | Yes      | Version of the schema (SemVer)   |
| `entities`    | list    | Yes      | List of entity names             |
| `universals`  | list    | No       | Common nouns, not described      |
| `particulars` | list    | No       | Specific nouns, not described    |

### `osed`

REQUIRED. `osed` field contains OSED version (string), the encompassing
document conforms to. It follows [SemVer](https://semver.org/). This field
ideally should be the first entry in an OSED document.

### `entities`

REQUIRED. MUST be a list of nouns/entities (strings) described in this document.
There
- MUST be a top level `description` in an OSED document or
- MUST be a leaf node with the same name in the `particulars` list or
- MUST be a leaf node with the same name in the `universals` list,

for each entry in `entities` list; checked in that order. An entry in this list
is an entity.

### `universals`

OPTIONAL. `universals` are nouns with valid semantics, both inside and outside
of a system. `universals` are listed but not described. If present,
`universals` MUST be a list. Each item in the list MUST be a
[**semanticNode**](#semantic-node). There MUST NOT be any top level entry with
one of the `universals` as key. e.g. password, email etc.

✅ Valid example:
```yaml
universals:
  - email
  - password
  - contact:
      - phone
      - email
  - identity:
      - aadhaar
      - pan
```

❌ Invalid examples:
```yaml
universals:
  - [email, password]  # ❌ Unnamed list (not a semanticNode)

  - auth:
      method: string    # ❌ Map value must be a list of semanticNodes

  - misc:
      - phone:          # ❌ Map inside a list with multiple keys is invalid
          - home
          - work
        email:
          - personal
          - work
```

### `particulars`

OPTIONAL. `particulars` are words with specific semantics within a system.
`particulars` are listed but not described. If present, `particulars` MUST be a
list. Each item in the list MUST be a [**semanticNode**](#semantic-node). There
MUST NOT be any top-level entry with one of the `particulars` as key. e.g.
`osed`, `entities`, `universals` in OSED etc. The structure is identical to
`universals`.

## Entity Description

REQUIRED, at least one in each OSED document. Each entityDescription defines
an entity in the system. It consists of a map with exactly one key-value pair,
where:

  - The key is the name of the entity (a string).
  - The value MUST be either:
    - a [`valueDescription`](#value-description), or
    - a flat list of strings, intended to represent categories, enumerated
    values, or labels.

## Value Description

A `valueDescription` is a map where:
  - Each key MUST be a string.
  - Each value MUST be one of:
    - a `particular`
    - a `universal`
    - an entity
    - another valueDescription

This recursive structure allows nesting and composition of values using
meaningful names.

❌ A valueDescription MUST NOT be a list, scalar, or dictionary with non-string
keys.

❌ Special constructs like type: list and type: map are not part of the core
spec and are instead handled by downstream metadata.

# Examples

```yaml
user:
  id: systemId
  email: email
  password: password
  profile:
    displayName: string
    xp: integer

taskLabel:
  - personalCare
  - career
  - shopping
  - custom
```

[osed.yaml](osed.yaml) is a minimal example of a YAML document conforming to
OSED version 0.1.0.

# Authors

- name: Jitendra Marndi
- email: quantumtunneler@duck.com
- github: [jitmar](https://github.com/jitmar)
