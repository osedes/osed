import { Document, Schema } from "mongoose";

export interface IUser extends Document {
  id: string;
  email: string;
  password: string;
  tags: string[];
  metadata: Record<string, string>;
  posts: Schema.Types.ObjectId[];
  profile: Schema.Types.ObjectId;
  createdAt: Date;
  isActive: boolean;
}

export interface IPost extends Document {
  id: string;
  title: string;
  content: string;
  author: Schema.Types.ObjectId;
  comments: string[];
  tags: string[];
  publishedAt: Date;
  isPublished: boolean;
}

export interface IComment extends Document {
  id: string;
  content: string;
  author: Schema.Types.ObjectId;
  post: Schema.Types.ObjectId;
  createdAt: Date;
}

export interface IUserProfile extends Document {
  id: string;
  displayName: string;
  bio: string;
  avatar: string;
  user: Schema.Types.ObjectId;
}

