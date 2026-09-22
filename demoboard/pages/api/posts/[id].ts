import type { NextApiRequest, NextApiResponse } from 'next';
import { getPostById, updatePost, deletePost } from '@/lib/posts';
import { Post } from '@/types/post';

type ResponseData = Post | { message: string } | { error: string };

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ResponseData>
) {
  const { id } = req.query;

  if (!id || typeof id !== 'string') {
    res.status(400).json({ error: '유효한 게시물 ID가 필요합니다.' });
    return;
  }

  if (req.method === 'GET') {
    try {
      const post = await getPostById(id);
      if (!post) {
        res.status(404).json({ error: '게시물을 찾을 수 없습니다.' });
        return;
      }
      res.status(200).json(post);
    } catch (error) {
      console.error('Failed to get post:', error);
      res.status(500).json({ error: '게시물을 불러올 수 없습니다.' });
    }
  } else if (req.method === 'PUT') {
    const { title, content } = req.body;

    if (!title || !content) {
      res.status(400).json({ error: '제목과 내용은 필수입니다.' });
      return;
    }

    try {
      const updatedPost = await updatePost(id, title, content);
      if (!updatedPost) {
        res.status(404).json({ error: '게시물을 찾을 수 없습니다.' });
        return;
      }
      res.status(200).json(updatedPost);
    } catch (error) {
      console.error('Failed to update post:', error);
      res.status(500).json({ error: '게시물을 수정할 수 없습니다.' });
    }
  } else if (req.method === 'DELETE') {
    try {
      const deleted = await deletePost(id);
      if (!deleted) {
        res.status(404).json({ error: '게시물을 찾을 수 없습니다.' });
        return;
      }
      res.status(200).json({ message: '게시물이 삭제되었습니다.' });
    } catch (error) {
      console.error('Failed to delete post:', error);
      res.status(500).json({ error: '게시물을 삭제할 수 없습니다.' });
    }
  } else {
    res.status(405).json({ error: 'Method not allowed' });
  }
}
