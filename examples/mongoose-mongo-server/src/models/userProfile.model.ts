import mongoose, { Schema, model } from "mongoose";
import { IUserProfile } from './interfaces.js';

const userProfileSchema = new Schema<IUserProfile>(
  {
  id: { type: 'String' },
  displayName: { type: 'String' },
  bio: { type: 'String' },
  avatar: { type: 'String' },
  user: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true, unique: true }
  },
  { timestamps: true }
);



export const UserProfile = model<IUserProfile>("UserProfile", userProfileSchema);
