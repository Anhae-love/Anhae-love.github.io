// Supabase 연결 설정.
// Supabase 대시보드 → Project Settings → Data API (또는 API) 에서 두 값을 복사해 넣으세요.
//   1) Project URL        : https://xxxxxxxx.supabase.co
//   2) anon public key    : eyJ... (아주 긴 문자열, "anon"/"publishable" 키)
// anon 키는 공개돼도 되는 키예요 (브라우저에 노출되도록 설계된 키). 비밀 service_role 키는 절대 넣지 마세요.
window.APP_CONFIG = {
  supabaseUrl: "https://xxxxxxxx.supabase.co",
  supabaseAnonKey: "여기에_anon_public_key_붙여넣기",

  // 편집 암호: 비워 두면 링크 아는 누구나 편집.
  // 값을 넣으면, 그 암호를 입력한 사람만 추가·수정·삭제할 수 있어요 (브라우저에 기억됨).
  editKey: "",

  pollMs: 4000 // 다른 사람이 바꾼 내용을 몇 ms마다 받아올지
};
