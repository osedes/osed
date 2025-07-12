import mongoose, { Schema, model } from "mongoose";
import { IComment } from './interfaces.js';

const commentSchema = new Schema<IComment>(
  {
  id: { type: 'String' },
  content: { type: 'String' },
  author: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  post: { type: mongoose.Schema.Types.ObjectId, ref: 'Post', required: true },
  createdAt: { type: 'Date', default: Date.now }
  },
  { timestamps: true }
);



export const Comment = model<IComment>("Comment", commentSchema);
