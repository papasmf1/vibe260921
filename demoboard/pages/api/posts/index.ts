import type { NextApiRequest, NextApiResponse } from 'next';
import { getAllPosts, createPost } from '@/lib/posts';
import { Post } from '@/types/post';

type ResponseData = Post[] | Post | { message: string } | { error: string };

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ResponseData>
) {
  if (req.method === 'GET') {
    try {
      const posts = await getAllPosts();
      res.status(200).json(posts);
    } catch (error) {
      console.error('Failed to get posts:', error);
      res.status(500).json({ error: '게시물을 불러올 수 없습니다.' });
    }
  } else if (req.method === 'POST') {
    const { title, content, author } = req.body;

    if (!title || !content || !author) {
      res.status(400).json({ error: '제목, 내용, 작성자는 필수입니다.' });
      return;
    }

    try {
      const newPost = await createPost(title, content, author);
      res.status(201).json(newPost);
    } catch (error) {
      console.error('Failed to create post:', error);
      res.status(500).json({ error: '게시물을 작성할 수 없습니다.' });
    }
  } else {
    res.status(405).json({ error: 'Method not allowed' });
  }
}
