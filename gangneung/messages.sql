-- 익명 무전기(지야호) 기능용 테이블
-- Supabase 대시보드 > SQL Editor 에 붙여넣고 "Run" 하세요.
-- (anon 키로 '아무나 메시지 보내기 + 읽기'가 가능하도록 RLS 정책 포함)

create table if not exists public.messages (
  id         bigint generated always as identity primary key,
  text       text not null check (char_length(text) <= 200),
  created_at timestamptz not null default now()
);

-- 최신순 조회 빠르게
create index if not exists messages_id_desc on public.messages (id desc);

-- RLS 켜기
alter table public.messages enable row level security;

-- 누구나(anon 포함) 읽기 허용
drop policy if exists "messages read" on public.messages;
create policy "messages read"
  on public.messages for select
  to anon, authenticated
  using (true);

-- 누구나(anon 포함) 익명으로 쓰기 허용 (최대 200자)
drop policy if exists "messages insert" on public.messages;
create policy "messages insert"
  on public.messages for insert
  to anon, authenticated
  with check (char_length(text) <= 200);

-- (선택) 실시간 구독을 쓰고 싶다면:
-- alter publication supabase_realtime add table public.messages;
