import mongoose, { Schema, Document, Model } from 'mongoose';

export interface IUser extends Document {
  email: string;
  password: string;
  tags: string[];
  metadata: Record<string, string>;
  posts: mongoose.Types.ObjectId[];
  profile: mongoose.Types.ObjectId;
  createdAt: Date;
  isActive: boolean;
}

const UserSchema: Schema<IUser> = new Schema<IUser>({
  email: { type: String, required: true, unique: true, index: true },
  password: { type: String, required: true },
  tags: { type: [String], default: [] },
  metadata: { type: Map, of: String, default: {} },
  posts: [{ type: Schema.Types.ObjectId, ref: 'Post' }],
  profile: { type: Schema.Types.ObjectId, ref: 'UserProfile', required: true },
  createdAt: { type: Date, default: Date.now },
  isActive: { type: Boolean, default: true },
});

// Ensure unique index is created
UserSchema.index({ email: 1 }, { unique: true });

export const User: Model<IUser> = mongoose.model<IUser>('User', UserSchema);
