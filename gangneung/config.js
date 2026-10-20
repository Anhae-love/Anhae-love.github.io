// Supabase 연결 설정.
// anon 키는 공개돼도 되는 키예요 (브라우저에 노출되도록 설계된 키). 비밀 service_role 키는 절대 넣지 마세요.
window.APP_CONFIG = {
  supabaseUrl: "https://eihqvxxyvoawzgyreasy.supabase.co",
  supabaseAnonKey: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVpaHF2eHh5dm9hd3pneXJlYXN5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI0NzQ2MjEsImV4cCI6MjEwODA1MDYyMX0.kNQwer77Z0gzDndBy5Rm8ZWuW5yq3OQe5AKATSq8lTM",

  // 편집 암호: 비워 두면 링크 아는 누구나 편집.
  // 값을 넣으면, 그 암호를 입력한 사람만 추가·수정·삭제할 수 있어요 (브라우저에 기억됨).
  editKey: "1023",

  pollMs: 4000 // 다른 사람이 바꾼 내용을 몇 ms마다 받아올지
};
