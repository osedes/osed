import mongoose, { Schema, model } from "mongoose";
import { IPost } from './interfaces.js';

const postSchema = new Schema<IPost>(
  {
  id: { type: 'String' },
  title: { type: 'String' },
  content: { type: 'String' },
  author: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  comments: [{ type: 'String' }],
  tags: [{ type: 'String' }],
  publishedAt: { type: 'Date' },
  isPublished: { type: 'Boolean', default: false }
  },
  { timestamps: true }
);



export const Post = model<IPost>("Post", postSchema);
