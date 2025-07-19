import mongoose, { Schema, model } from "mongoose";
import { IUser } from './interfaces.js';

const userSchema = new Schema<IUser>(
  {
  id: { type: 'String' },
  email: { type: 'String', required: true, unique: true },
  password: { type: 'String', required: true },
  tags: [{ type: 'String' }],
  metadata: { type: Map, of: { type: 'String' }, default: {} },
  posts: [{ type: mongoose.Schema.Types.ObjectId, ref: 'Post' }],
  profile: { type: mongoose.Schema.Types.ObjectId, ref: 'UserProfile', required: true },
  createdAt: { type: 'Date', default: Date.now },
  isActive: { type: 'Boolean', default: true }
  },
  { timestamps: true }
);



export const User = model<IUser>("User", userSchema);
