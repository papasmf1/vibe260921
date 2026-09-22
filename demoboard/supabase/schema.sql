-- DemoBoard Posts Table
-- Run this SQL in your Supabase SQL Editor to set up the database schema
-- RLS is disabled since all access goes through the service-role key (server-side only)

create table posts (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  content text not null,
  author text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Seed data: initial welcome post
insert into posts (title, content, author) values
  ('환영합니다!', 'DemoBoard에 오신 것을 환영합니다. 이곳에서 자유롭게 게시물을 작성하고 공유할 수 있습니다.', 'Admin');
