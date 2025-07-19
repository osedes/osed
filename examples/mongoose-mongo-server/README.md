# Mongoose-Mongo Server Example

> **Note:** This example assumes that the models and routes have already been
> generated from an OSED metadata YAML document. For details on how to author
> metadata and generate code, see the main [README.md](../../README.md) and
> follow the end-to-end workflow instructions there.

This example demonstrates a modular, production-ready Express server using
Mongoose and TypeScript (ES modules, strict mode), generated from OSED metadata.

## Integration Example

You can reuse the user router and model in your own Express/TypeScript project:

```ts
// app.ts (your own project)
import express from 'express';
import mongoose from 'mongoose';
import userRouter from './path/to/examples/mongoose-mongo-server/src/routes/user.js';

const app = express();
const PORT = process.env.PORT || 3000;
const MONGO_URI =
  process.env.MONGO_URI || 'mongodb://localhost:27017/osed_demo';

app.use(express.json());
app.use('/users', userRouter);

mongoose
  .connect(MONGO_URI)
  .then(() => {
    app.listen(PORT, () => {
      console.log(`Server running on port ${PORT}`);
    });
  })
  .catch(err => {
    console.error('MongoDB connection error:', err);
    process.exit(1);
  });
```

- Make sure to use the correct relative path to the router file.
- Your project should also have `mongoose`, `express`, and TypeScript
  dependencies installed.
- The router and model are fully typed and ready for extension.

## Project Structure

- `src/models/user.ts` — Mongoose model for User
- `src/routes/user.ts` — Express router for User CRUD
- `src/index.ts` — Main server entry point

## Setup & Usage

1. Install dependencies:
   ```bash
   npm install
   ```
2. Start MongoDB (locally or via cloud provider).
3. Run in development mode:
   ```bash
   npm run dev
   ```
4. Or build and run in production mode:
   ```bash
   npm run build
   npm start
   ```

## API Endpoints

- `POST /users` — Create a new user
- `GET /users` — List all users

Extend the models and routes as needed for your application.

## Example API Requests

### Create a new user

```bash
curl -X POST http://localhost:3000/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "password": "secret123",
    "tags": ["admin", "test"],
    "metadata": {"department": "engineering"},
    "profile": "<userProfileObjectId>"
  }'
```

> Note: Replace `<userProfileObjectId>` with a valid UserProfile ObjectId from
> your database.

### List all users

```bash
curl http://localhost:3000/users
```

### Root endpoint (version)

```sh
curl http://localhost:3000/
```

Response:

```json
{ "version": "<version-from-package.json>" }
```

### Health check

```sh
curl http://localhost:3000/health
```

Response:

```json
{ "status": "OK" }
```
