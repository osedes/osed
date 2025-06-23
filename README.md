# OSED - Open Standard Entity Description

Standard description of entities and inter-entity relations defined for a
system

# Description

This document attempts to standardize machine-readable description of nouns
(entities) and, relations among nouns; applicable to business logic of a
system. The rules specified in this document collectively form the standard.

One obvious use case is the abstraction of database schema definitions.
Single OSED document can be used to generate schema definitions for multiple
database management systems (DBMS) using OSED-compliant parsers. OSED can also
be used to document business level nouns without defining workflows.

It's helpful to draft OSED documents prior to any implementation of business
logic. OSED documents should be versioned and tracked using version control
system. Solutions Architects, Business or Technical Analysts or any individual
involved in translating business requirement into system design may choose to
draft an OSED document.

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
section.

## Top level entry

Following fields are allowed as top level entries in an OSED document:

### `osed`

REQUIRED. `osed` field contains OSED version (string), the encompassing
document conforms to. It follows [SemVer](https://semver.org/). This field
ideally should be the first entry in an OSED document.

### `entities`

REQUIRED. MUST be a list of nouns/entities (strings) described in this document.
There
- MUST be a top level description in an OSED document or
- MUST be a leaf node with the same name in the `particulars` list or
- MUST be a leaf node with the same name in the `universals` list,

for each entry in `entities` list;
checked in that order.

### `universals`

OPTIONAL. If exists, MUST be a [nested ]list of nouns (string). `universals`
are nouns with valid semantics, both inside and outside of a system.
`universals` are listed but not described. There MUST NOT be any top level
entry with one of the `universals` as key. e.g. password, email etc.

### `particulars`

OPTIONAL. If exists, MUST be a [nested ]list of words (string). `particulars`
are words with specific semantics within a system. `particulars` are listed but
not described. There MUST NOT be any top level entry with one of the
`particulars` as key. e.g. `osed`, `entities`, `universals` in OSED etc.

### `<entity>`

REQUIRED, at least one in each OSED document. Each entity description consists
of a key and a value. Key MUST be string. Value is described using Value
Description.

#### Value Description

A Value Description MUST consists entirely of a
- string. This string MUST also be
present in `particulars`, `universals` or `entities`; checked in that order.
- a list. Each item of any list in an
OSED document MUST either be a list or a string i.e. only [nested ]list of
strings are allowed.
- a dictionary with many keys and corresponding values.
Each key-value pair in a Value Description dictionary have rules similar to
Entity Description.

##### Special Value Descriptions:

A dictionary containing the key `type` is a Special Value Description.

###### List Description

- `type`: MUST be `list` for it to be considered a list description.
- `items`: REQUIRED for all list descriptions. MUST be a value description.

###### Map Description

- `type`: MUST be `map` for it to be considered a map description.
- `key`: REQUIRED for all map descriptions. MUST be string.
- `value`: REQUIRED for all map descriptions. MUST be a value description.

# Authors

- name: Jitendra Marndi
- email: quantumtunneler@duck.com
- github: [jitmar](https://github.com/jitmar)
