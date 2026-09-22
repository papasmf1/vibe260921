import { Post } from '@/types/post';
import { supabase } from './supabaseClient';

type DbPost = {
  id: string;
  title: string;
  content: string;
  author: string;
  created_at: string;
  updated_at: string;
};

function mapRow(row: DbPost): Post {
  return {
    id: row.id,
    title: row.title,
    content: row.content,
    author: row.author,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export async function getAllPosts(): Promise<Post[]> {
  const { data, error } = await supabase
    .from('posts')
    .select('*')
    .order('created_at', { ascending: false });

  if (error) throw error;
  return (data || []).map(mapRow);
}

export async function getPostById(id: string): Promise<Post | null> {
  const { data, error } = await supabase
    .from('posts')
    .select('*')
    .eq('id', id)
    .maybeSingle();

  if (error) throw error;
  return data ? mapRow(data) : null;
}

export async function createPost(title: string, content: string, author: string): Promise<Post> {
  const { data, error } = await supabase
    .from('posts')
    .insert([{ title, content, author }])
    .select()
    .single();

  if (error) throw error;
  return mapRow(data);
}

export async function updatePost(id: string, title: string, content: string): Promise<Post | null> {
  const { data, error } = await supabase
    .from('posts')
    .update({ title, content, updated_at: new Date().toISOString() })
    .eq('id', id)
    .select()
    .maybeSingle();

  if (error) throw error;
  return data ? mapRow(data) : null;
}

export async function deletePost(id: string): Promise<boolean> {
  const { error, count } = await supabase
    .from('posts')
    .delete()
    .eq('id', id);

  if (error) throw error;
  return (count || 0) > 0;
}
