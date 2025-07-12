import './setup.js';
import { describe, it } from 'node:test';
import assert from 'node:assert';
import mongoose from 'mongoose';
import request from 'supertest';
import { app } from '../index.js';
import { User } from '../models/user.model.js';

describe('User API', () => {
  describe('GET /users', () => {
    it('should return empty array when no users exist', async () => {
      const response = await request(app)
        .get('/users')
        .expect(200);

      assert.deepStrictEqual(response.body, []);
    });

    it('should return all users', async () => {
      const user1 = new User({
        email: 'john@example.com',
        password: 'password123',
        profile: new mongoose.Types.ObjectId() // Required field
      });
      const user2 = new User({
        email: 'jane@example.com',
        password: 'password456',
        profile: new mongoose.Types.ObjectId() // Required field
      });

      await user1.save();
      await user2.save();

      const response = await request(app)
        .get('/users')
        .expect(200);

      assert.strictEqual(response.body.length, 2);
      assert.strictEqual(response.body[0].email, 'john@example.com');
      assert.strictEqual(response.body[1].email, 'jane@example.com');
    });
  });

  describe('GET /users/:id', () => {
    it('should return 404 for non-existent user', async () => {
      await request(app)
        .get('/users/507f1f77bcf86cd799439011')
        .expect(404);
    });

    it('should return user by id', async () => {
      const user = new User({
        email: 'test@example.com',
        password: 'password123',
        profile: new mongoose.Types.ObjectId() // Required field
      });
      await user.save();

      const response = await request(app)
        .get(`/users/${user._id}`)
        .expect(200);

      assert.strictEqual(response.body.email, 'test@example.com');
    });
  });

  describe('POST /users', () => {
    it('should create a new user', async () => {
      const userData = {
        email: 'new@example.com',
        password: 'password123',
        profile: new mongoose.Types.ObjectId().toString() // Required field
      };

      const response = await request(app)
        .post('/users')
        .send(userData)
        .expect(201);

      assert.strictEqual(response.body.email, 'new@example.com');
      assert.strictEqual(response.body.isActive, true); // default value
      assert.ok(response.body._id);
    });

    it('should return 400 for invalid user data', async () => {
      const invalidData = {
        email: 'test@example.com'
        // missing required fields: password, profile
      };

      await request(app)
        .post('/users')
        .send(invalidData)
        .expect(400);
    });

    it('should return 400 for duplicate email', async () => {
      const userData = {
        email: 'duplicate@example.com',
        password: 'password123',
        profile: new mongoose.Types.ObjectId().toString()
      };

      // Create first user
      const firstResponse = await request(app)
        .post('/users')
        .send(userData)
        .expect(201);

      console.log('First user created:', firstResponse.body.email);

      // Check if user exists in database
      const existingUser = await User.findOne({ email: userData.email });
      console.log('User in database after first creation:', existingUser ? existingUser.email : 'not found');

      // Try to create second user with same email
      const secondResponse = await request(app)
        .post('/users')
        .send(userData);

      console.log('Second response status:', secondResponse.status);
      console.log('Second response body:', secondResponse.body);

      assert.strictEqual(secondResponse.status, 400);
    });
  });

  describe('PATCH /users/:id', () => {
    it('should return 404 for non-existent user', async () => {
      await request(app)
        .patch('/users/507f1f77bcf86cd799439011')
        .send({ name: 'Updated Name' })
        .expect(404);
    });

    it('should update user', async () => {
      const user = new User({
        email: 'original@example.com',
        password: 'password123',
        profile: new mongoose.Types.ObjectId()
      });
      await user.save();

      const response = await request(app)
        .patch(`/users/${user._id}`)
        .send({ email: 'updated@example.com' })
        .expect(200);

      assert.strictEqual(response.body.email, 'updated@example.com');
    });

    it('should return 400 for invalid update data', async () => {
      const user = new User({
        email: 'test@example.com',
        password: 'password123',
        profile: new mongoose.Types.ObjectId()
      });
      await user.save();

      await request(app)
        .patch(`/users/${user._id}`)
        .send({ email: 'invalid-email' })
        .expect(400);
    });
  });

  describe('DELETE /users/:id', () => {
    it('should return 404 for non-existent user', async () => {
      await request(app)
        .delete('/users/507f1f77bcf86cd799439011')
        .expect(404);
    });

    it('should delete user', async () => {
      const user = new User({
        email: 'delete@example.com',
        password: 'password123',
        profile: new mongoose.Types.ObjectId()
      });
      await user.save();

      await request(app)
        .delete(`/users/${user._id}`)
        .expect(200);

      // Verify user is deleted
      const deletedUser = await User.findById(user._id);
      assert.strictEqual(deletedUser, null);
    });
  });
});
