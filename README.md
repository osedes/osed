# OSED - Open Standard Entity Description

![CI](https://github.com/osedes/osed/actions/workflows/osed.yaml/badge.svg)

Standard description of entities and inter-entity relations defined for a
system

# About

This document attempts to standardize machine-readable description of nouns
(entities) and, relations among nouns - applicable to function of a system -
while maintaining high degree of human-readability. The rules specified in this
document collectively form the standard.

**Currently in development for v0.3.0.**

*Note: The README and examples refer to v0.3.0, which is under active
development. The v0.3.0 tag will be added once the release is finalized and all
documentation is coherent.*

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

###### Version 0.3.0

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL
NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED",
"MAY", and "OPTIONAL" in this document are to be interpreted as
described in
[BCP 14](https://www.rfc-editor.org/bcp/bcp14)
[[RFC2119](https://www.rfc-editor.org/rfc/rfc2119)]
[[RFC8174](https://www.rfc-editor.org/rfc/rfc8174)]
when, and only when, they appear in all capitals, as shown here.

# CLI Usage

The `osed` command-line interface provides tooling for validating, linting, and generating
code from OSED documents.

## Validate an OSED document

```bash
osed validate --file sample/osed.driver.mongoose-mongodb.v0.3.0.yaml
```

## Lint an OSED document
```bash
osed lint --file=sample/osed.driver.mongoose-mongodb.v0.3.0.yaml
```

## Generate code from an OSED document

Generate Mongoose/TypeScript schema files:
```bash
osed generate --target mongoose --file sample/osed.driver.mongoose-mongodb.v0.3.0.yaml --out ./generated
```

The generate command supports:
- **Mongoose/TypeScript**: Generates TypeScript interfaces and Mongoose schema files
- Extensible framework support for future targets (Prisma, SQLAlchemy, etc.)

Generated files include:
- TypeScript interfaces with proper typing
- Mongoose schema definitions with metadata support
- Import/export statements for cross-references
- Support for arrays, maps, references, and nested objects

## Return Codes
| Code  |	Meaning                       |
|-------|-------------------------------|
| 0	    | Success                       |
| 1     |	Validation or linting failed  |
| 2     |	Input file or schema missing  |

# Driver-Based Approach

OSED v0.3.0 introduces a driver-based approach that makes the schema more flexible and extensible. Instead of using driver-specific prefixes (like `mongoose:`), the schema now uses a clean, driver-agnostic format with optional driver specification.

## Key Benefits

- **DBMS-Agnostic**: Schema definitions work across different database systems
- **Extensible**: Easy to add support for new drivers (Prisma, SQLAlchemy, etc.)
- **Cleaner Syntax**: No more verbose prefixes like `mongoose:type`, `mongoose:required`
- **Better Validation**: Driver-specific validation only when needed

## Driver Specification

You can optionally specify a target driver in your OSED document:

```yaml
osed: "0.3.0"
driver: "mongoose-mongodb"  # Optional: enables driver-specific validation
```

Supported drivers:
- `mongoose` - Mongoose/MongoDB (normalized to `mongoose-mongodb`)
- `mongoose-mongo` - Mongoose/MongoDB (normalized to `mongoose-mongodb`)
- `mongoose-mongodb` - Mongoose/MongoDB

## Schema Format

The new format uses clean, driver-agnostic keys:

```yaml
# Old format (deprecated)
user:
  email:
    mongoose:type: string
    mongoose:required: true
    mongoose:unique: true

# New format (driver-based)
user:
  email:
    type: string
    required: true
    unique: true
```

# End-to-End Workflow

This section demonstrates a complete workflow from OSED document to working
application.

## Step 1: Create Your OSED Document

Start with a YAML file describing your entities using the new driver-based approach:

```yaml
# sample/osed.driver.mongoose-mongodb.v0.3.0.yaml
osed: "0.3.0"
driver: "mongoose-mongodb"  # Optional: specifies the target driver

entities:
  - user
  - post
  - comment
  - userProfile
  - avatar
  - bio
  - displayName

universals:
  - string
  - number
  - boolean
  - date
  - email
  - password
  - url
  - array
  - list
  - map
  - reference
  - objectid
  - now

particulars:
  - systemId
  - Employee:
    - position
    - department

user:
  id: string
  email: email
  password: password
  isActive:
    type: boolean
    default: true
  posts:
    type: list
    items: post
    ref: post

post:
  id: string
  title: string
  content: string
  author:
    type: reference
    ref: user
    required: true
  tags:
    type: list
    items: string
  metadata:
    type: map
    value: string

displayName: string
bio: string
avatar: string

comment:
  id: string
  content: string

userProfile:
  id: string
  displayName: string
  bio: string
  avatar: string
```

## Step 2: Validate and Lint

Ensure your document is valid and follows best practices:

```bash
# Validate the document structure
osed validate --file sample/osed.driver.mongoose-mongodb.v0.3.0.yaml

# Lint for semantic issues and best practices
osed lint --file=sample/osed.driver.mongoose-mongodb.v0.3.0.yaml
```

## Step 3: Generate Code

Generate production-ready TypeScript and Mongoose files:

```bash
# Generate Mongoose/TypeScript schemas
osed generate --target mongoose --file sample/osed.driver.mongoose-mongodb.v0.3.0.yaml --out ./generated
```

This creates:
- `generated/user.model.ts` - User interface and schema
- `generated/post.model.ts` - Post interface and schema
- `generated/index.ts` - Export all models

## Step 4: Build Your Application

### Option A: Use the Provided Server Example

The project includes a complete server example in `examples/mongoose-mongo-server/`:

```bash
# Copy your generated files to the example
cp generated/* examples/mongoose-mongo-server/src/models/

# Navigate to the example
cd examples/mongoose-mongo-server

# Install dependencies
npm install

# Start MongoDB (using Docker or any running instance)
# Example with Docker:
docker run -d -p 27017:27017 --name mongodb mongo:latest
# Or connect to any MongoDB instance with API exposed at the standard endpoint

# Start the server
npm run dev
```

### Option B: Integrate with Your Own Application

```typescript
// app.ts
import express from 'express';
import mongoose from 'mongoose';
import { User, Post } from './generated';

const app = express();
app.use(express.json());

// Connect to MongoDB
mongoose.connect('mongodb://localhost:27017/myapp');

// Use generated models in your routes
app.get('/users', async (req, res) => {
  const users = await User.find().populate('posts');
  res.json(users);
});

app.post('/users', async (req, res) => {
  const user = new User(req.body);
  await user.save();
  res.status(201).json(user);
});

app.listen(3000, () => {
  console.log('Server running on port 3000');
});
```

## Step 5: Test Your Application

Use the provided test script or create your own tests:

```bash
# Test the server endpoints
./examples/mongoose-mongo-server/test_endpoints.sh

# Or test specific endpoints
./examples/mongoose-mongo-server/test_endpoints.sh \
  --ip localhost \
  --port 3000 \
  --user-id 123
```

## Complete Example

See `examples/mongoose-mongo-server/` for a complete, production-ready server that demonstrates:

- ✅ TypeScript with ES modules
- ✅ Express.js with proper routing
- ✅ Mongoose models with validation
- ✅ Complete CRUD operations
- ✅ Health check endpoints
- ✅ Error handling and logging
- ✅ MongoDB setup (Docker or any instance with standard endpoint)
- ✅ Comprehensive testing script

## Workflow Benefits

1. **Single Source of Truth**: Your OSED document defines both data structure
and relationships
2. **Type Safety**: Generated TypeScript interfaces ensure compile-time type
checking
3. **Consistency**: All generated code follows the same patterns and conventions
4. **Maintainability**: Changes to the OSED document automatically update all
generated code
5. **Validation**: Built-in validation ensures data integrity at multiple levels
6. **Documentation**: The OSED document serves as living documentation for your
data model

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
OSED version 0.2.0.

# Schema Validation and Linting

OSED provides comprehensive validation and linting to ensure schema correctness and consistency. The linter performs semantic analysis of entity references and structure validation.

## Entity Reference Extraction Logic

The linter uses a context-sensitive approach to extract entity references:

### What Gets Collected as "Used Entities":

1. **Top-level keys** (excluding reserved control keys):
   - Any top-level key that's not `osed`, `entities`, `universals`, or `particulars` is considered an entity declaration
   - These must be declared in the `entities`, `universals`, or `particulars` sections

2. **Leaf node values** (strings that are not property names):
   - String values that appear as direct values in entity descriptions
   - Values of `mongoose:ref` and `mongoose:items` fields
   - Any string value that represents an entity reference

### What Does NOT Get Collected:

- **Property names** (non-top-level keys): These are field names, not entity references
- **Metadata keys**: Keys like `mongoose:type`, `mongoose:required`, etc.

### Linting Rules:

- **Undeclared entities**: Any top-level key or leaf node value not found in `entities`, `universals`, or `particulars` is reported as undeclared
- **Unknown top-level keys**: Top-level keys that aren't declared entities are reported as unknown
- **Unused entities**: Entities declared but not used anywhere are reported as unused

### Example Linting Output:

```bash
✅ All required keys are present.
✅ All entity names are valid.
✅ No duplicate entities across entities/universals/particulars.
⚠️  Undeclared but used entities:
  - string      # Leaf node value not declared
  - systemId    # Leaf node value not declared
✅ All declared entities are used.
✅ No unknown top-level keys.
```

## Driver-Based Metadata: Embedding vs Referencing

OSED supports both embedded sub-documents and references in Mongoose/MongoDB
schema generation using the new driver-based approach. The convention and linter behavior are as follows:

## Embedding (Sub-Document)

If you use a direct entity name under `items` or `value`, the field will be treated as an embedded sub-document.

Example:
```yaml
tasks:
  type: list
  items: Task  # Embedded sub-document
```

ℹ️  The linter will print:
> Embedding entity 'Task' as a sub-document at ... For referencing, use
'type: list' with 'items: {type: reference, ref: Task}'.

## Referencing (Foreign Key)

If you want to create a reference to another collection, use the explicit type+ref pattern:

Example:
```yaml
tasks:
  type: list
  items:
    type: reference
    ref: Task  # Reference to another collection
```

ℹ️  The linter will print:
> Referencing entity 'Task' at ... For embedding, use 'items: Task'
(direct entity name) instead of type+ref.

## Summary Table

| Pattern                        | Treated As         | Linter Output         |
|--------------------------------|--------------------|-----------------------|
| `items: Task`                  | Embedded           | Info: Embedding entity 'Task'...                    |
| `items: {type: reference, ref: Task}` | Reference          | Info: Referencing entity 'Task'...                 |

## Notes
- Embedding is best for small, tightly coupled data.
- Referencing is best for large, independent, or shared data.
- The linter provides informative messages to help you choose the right approach.
- See MongoDB and Mongoose documentation for more on embedding vs referencing best practices.

# Code Generation Output

The `osed generate` command produces production-ready TypeScript and Mongoose files from OSED documents.

## Generated File Structure

For each entity in your OSED document, the following files are generated:

```
generated/
├── user.model.ts      # User entity interface and schema
├── post.model.ts      # Post entity interface and schema
└── index.ts           # Export all models
```

## TypeScript Interface Example

```typescript
// user.model.ts
import { Document, Schema, model } from 'mongoose';

export interface IUser extends Document {
  id: string;
  name: string;
  email: string;
  isActive: boolean;
  profile?: {
    displayName: string;
    xp: number;
  };
  posts?: Array<Schema.Types.ObjectId | IPost>;
}

const userSchema = new Schema<IUser>({
  id: { type: String, required: true },
  name: { type: String, required: true },
  email: { type: String, required: true, unique: true },
  isActive: { type: Boolean, default: true },
  profile: {
    displayName: { type: String },
    xp: { type: Number }
  },
  posts: [{ type: Schema.Types.ObjectId, ref: 'Post' }]
});

export const User = model<IUser>('User', userSchema);
```

## Supported Features

- **Primitive Types**: `string`, `number`, `boolean`, `date`
- **Arrays**: `type: list` with `items`
- **Maps**: `type: map` with `value`
- **References**: Cross-entity relationships with `type: reference` and `ref`
- **Metadata**: `required`, `unique`, `default` values
- **Nested Objects**: Embedded sub-documents
- **Import/Export**: Automatic dependency management
- **Driver Support**: Mongoose/MongoDB (extensible to other drivers)

## Metadata Support

Driver metadata is applied to generated schemas:

```yaml
user:
  email:
    type: string
    required: true
    unique: true
  isActive:
    type: boolean
    default: true
```

Generates:
```typescript
email: { type: String, required: true, unique: true },
isActive: { type: Boolean, default: true }
```

# Schema Versions and Changes

## v0.1.0

Initial version of the schema, with the following structure:

- ✅ Required fields: `osed`, `entities`
- ✅ Optional fields: `universals`, `particulars`
- ✅ Recursive `semanticNode` structure for noun grouping
- ✅ Entity descriptions supporting nested maps or flat string lists
- ✅ Naming convention enforced for all property names and entities

## v0.2.0

The following improvements were made without breaking compatibility:

- ✅ Defined reusable `entityNamePattern` via `$ref` to ensure consistency in
naming rules
- ✅ Added SemVer regex validation for the `osed` field to enforce proper
versioning format
- ✅ Introduced `$id` and `version` metadata in the schema to support external
tooling and hosting
- ✅ Improved `valueDescription` structure to support only well-defined types
(no booleans, nulls, or raw scalars)
- ✅ Removed support for `type: list/map` constructs from the core schema
(now handled via downstream metadata)
- ✅ Added `osed_lint.py` tool for semantic validation, checking:
  - Reserved word misuse
  - Undeclared/unused/duplicate entity names
  - Invalid characters in entity names
  - Misplaced entity descriptions

## v0.3.0

The following changes and improvements were made in v0.3.0:

- ✅ Major refactor from meta-entity structure (entityDescription,
valueDescription) to concrete, real-world entities (e.g., user, post, comment,
userProfile, etc.)
- ✅ Enhanced support for Mongoose metadata, including type, required, unique,
default, reference, and array/map handling (see sample/osed.v0.3.0.yaml)
- ✅ Simplified and clarified the OSED YAML structure for easier authoring and
downstream code generation
- ✅ Improved validation and linting via CLI (`osed validate`, `osed lint`)
with stricter schema enforcement and comprehensive entity reference extraction
- ✅ Updated all examples and documentation to use sample/osed.v0.3.0.yaml
- ✅ Example server and tests now support any MongoDB instance, not just Docker
- ✅ Deprecated or removed unused/obsolete meta-entities (e.g.,
specialValueDescription)
- ✅ Improved documentation and consistency across CLI, examples, and schema
- ✅ Enhanced linting logic that properly distinguishes between top-level keys,
leaf node values, and property names for accurate entity reference validation

# Authors

- name: Jitendra Marndi
- email: quantumtunneler@duck.com
- github: [jitmar](https://github.com/jitmar)
