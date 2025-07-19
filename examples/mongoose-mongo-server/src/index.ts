import express from 'express';
import mongoose from 'mongoose';
import userRouter from './routes/user.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const app = express();
const PORT = process.env.PORT || 3000;
const MONGO_URI = process.env.MONGO_URI || 'mongodb://localhost:27017/osed_demo';

// ES module __dirname workaround
const currentFilename = fileURLToPath(import.meta.url);
const currentDirname = path.dirname(currentFilename);

app.use(express.json());
app.use('/users', userRouter);

// Add version and health endpoints
app.get('/', (req, res) => {
  // Read version from package.json
  const pkgPath = path.resolve(currentDirname, '../package.json');
  let version = 'unknown';
  try {
    const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf-8'));
    version = pkg.version;
  } catch (e) { }
  res.json({ version });
});

app.get('/health', (req, res) => {
  res.json({ status: 'OK' });
});

// Only start server if not in test environment
if (process.env.NODE_ENV !== 'test') {
  mongoose.connect(MONGO_URI)
    .then(() => {
      console.log('Connected to MongoDB');
      app.listen(PORT, () => {
        console.log(`Server running on port ${PORT}`);
      });
    })
    .catch((err) => {
      console.error('MongoDB connection error:', err);
      process.exit(1);
    });
}

export { app };
