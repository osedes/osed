import mongoose from 'mongoose';
import { before, after, beforeEach } from 'node:test';

// Test database connection
const TEST_DB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/osed_test';

before(async () => {
  await mongoose.connect(TEST_DB_URI);
  if (mongoose.connection.db) {
    await mongoose.connection.db.collection('users').createIndex({ email: 1 }, { unique: true });
    console.log('Connected to test database and ensured unique index');
  } else {
    throw new Error('mongoose.connection.db is undefined');
  }
});

after(async () => {
  await mongoose.connection.close();
  console.log('Disconnected from test database');
});

beforeEach(async () => {
  // Clean up all collections after each test
  const collections = mongoose.connection.collections;
  for (const key in collections) {
    const collection = collections[key];
    await collection.deleteMany({});
  }
  console.log('Cleaned up test collections');
});
