<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>메뉴 추천 — IDP</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&family=Bebas+Neue&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --blue:#1A6FD4; --blue-light:#E8F0FD; --blue-mid:#4A90E2;
      --green:#16A34A; --green-light:#DCFCE7;
      --red:#DC2626; --red-light:#FEE2E2;
      --amber:#D97706; --amber-light:#FEF3C7;
      --yellow:#FBBF24; --yellow-light:#FEF9C3;
      --g50:#F8FAFC; --g100:#F1F5F9; --g200:#E2E8F0; --g300:#CBD5E1;
      --g400:#94A3B8; --g500:#64748B; --g700:#334155; --g900:#0F172A;
      --white:#fff; --radius:14px; --rsm:10px;
      --shadow:0 1px 3px rgba(0,0,0,.08),0 4px 16px rgba(0,0,0,.06);
      --shadow-lg:0 8px 32px rgba(0,0,0,.15);
    }
    html { scroll-behavior: smooth; }
    body { font-family:'Noto Sans KR',sans-serif; background:var(--g50); color:var(--g900); min-height:100vh; padding-bottom:100px; }

    /* ── 네비 ── */
    .nav { position:sticky; top:0; z-index:200; background:var(--white); border-bottom:1px solid var(--g200); height:56px; display:flex; align-items:center; padding:0 20px; gap:8px; }
    .nav-logo { font-family:'Bebas Neue',sans-serif; font-size:22px; letter-spacing:.06em; color:var(--blue); text-decoration:none; margin-right:8px; }
    .nav-links { display:flex; gap:4px; flex:1; }
    .nav-links a { font-size:13px; font-weight:500; color:var(--g500); text-decoration:none; padding:6px 12px; border-radius:var(--rsm); transition:background .15s,color .15s; }
    .nav-links a:hover { background:var(--g100); color:var(--g900); }
    .nav-links a.active { background:var(--blue-light); color:var(--blue); }

    /* ── 페이지 ── */
    .page { max-width:760px; margin:0 auto; padding:28px 16px 0; }

    /* ── 탭 ── */
    .tabs { display:flex; background:var(--g100); border-radius:12px; padding:4px; margin-bottom:20px; }
    .tab { flex:1; height:40px; border:none; background:transparent; border-radius:9px; font-size:13px; font-weight:600; color:var(--g500); cursor:pointer; transition:all .2s; font-family:'Noto Sans KR',sans-serif; }
    .tab.active { background:var(--white); color:var(--blue); box-shadow:0 1px 4px rgba(0,0,0,.1); }

    /* ── 탭 패널 ── */
    .tab-panel { display:none; }
    .tab-panel.active { display:block; }

    /* ── 카드 ── */
    .card { background:var(--white); border:1px solid var(--g200); border-radius:var(--radius); padding:20px; margin-bottom:16px; box-shadow:var(--shadow); }
    .card-title { font-size:14px; font-weight:700; color:var(--g700); margin-bottom:16px; display:flex; align-items:center; gap:8px; }
    .card-icon { font-size:18px; }

    /* ── 섹션 헤더 ── */
    .sec-label { font-size:12px; font-weight:600; color:var(--g500); margin-bottom:8px; margin-top:16px; }
    .sec-label:first-child { margin-top:0; }

    /* ── 인풋 ── */
    .inp { height:40px; padding:0 12px; border:1.5px solid var(--g200); border-radius:var(--rsm); font-size:13px; font-family:'Noto Sans KR',sans-serif; background:var(--white); color:var(--g900); outline:none; transition:border-color .15s; width:100%; }
    .inp:focus { border-color:var(--blue); }
    .inp::placeholder { color:var(--g400); }
    .inp-row { display:flex; gap:8px; }
    .inp-row .inp { flex:1; }

    /* ── 칩 ── */
    .chip-group { display:flex; flex-wrap:wrap; gap:6px; }
    .chip { padding:6px 14px; border:1.5px solid var(--g200); border-radius:99px; font-size:12px; font-weight:500; color:var(--g500); cursor:pointer; user-select:none; transition:all .15s; background:var(--white); }
    .chip:hover { border-color:var(--blue-mid); color:var(--blue); }
    .chip.sel     { background:var(--blue-light);   border-color:var(--blue);  color:var(--blue); }
    .chip.sel.dc  { background:var(--red-light);    border-color:var(--red);   color:var(--red); }
    .chip.sel.wc  { background:var(--amber-light);  border-color:var(--amber); color:var(--amber); }

    /* ── 버튼 ── */
    .btn { height:44px; padding:0 20px; border:none; border-radius:var(--rsm); font-size:14px; font-weight:700; cursor:pointer; font-family:'Noto Sans KR',sans-serif; transition:opacity .15s,transform .1s; display:inline-flex; align-items:center; gap:6px; }
    .btn:hover:not(:disabled) { opacity:.88; }
    .btn:active:not(:disabled) { transform:scale(.98); }
    .btn:disabled { opacity:.45; cursor:not-allowed; }
    .btn-primary { background:var(--blue); color:var(--white); width:100%; justify-content:center; height:50px; font-size:15px; }
    .btn-sm { height:36px; font-size:12px; padding:0 12px; background:var(--g100); color:var(--g700); }
    .btn-sm:hover { background:var(--g200); }

    /* ── 시간표 그리드 ── */
    .timetable-wrap { overflow-x:auto; }
    .timetable { width:100%; border-collapse:collapse; min-width:340px; }
    .timetable th { font-size:12px; font-weight:600; color:var(--g500); padding:6px 4px; text-align:center; border-bottom:1px solid var(--g200); }
    .timetable td { padding:2px; vertical-align:top; }
    .time-label { font-size:10px; color:var(--g400); text-align:right; padding-right:6px; width:36px; white-space:nowrap; }
    .time-slot { height:20px; border-radius:3px; cursor:pointer; transition:background .12s; }
    .time-slot:hover { opacity:.8; }
    .time-slot.empty { background:var(--g100); }
    .time-slot.empty:hover { background:var(--g200); }
    .time-slot.busy { background:#A5B4FC; }
    .time-slot.busy:hover { background:#818CF8; }
    .tt-legend { display:flex; gap:12px; margin-top:8px; font-size:11px; color:var(--g500); }
    .tt-legend span { display:flex; align-items:center; gap:4px; }
    .tt-dot { width:10px; height:10px; border-radius:2px; }

    /* ── 식단 업로드 카드 ── */
    .meal-day-card { border:1px solid var(--g200); border-radius:var(--rsm); overflow:hidden; margin-bottom:10px; }
    .meal-day-header { background:var(--g50); padding:10px 14px; font-size:13px; font-weight:700; color:var(--g700); display:flex; align-items:center; justify-content:space-between; cursor:pointer; user-select:none; }
    .meal-day-body { padding:12px 14px; display:none; }
    .meal-day-body.open { display:block; }
    .meal-time-section { margin-bottom:12px; }
    .meal-time-label { font-size:11px; font-weight:700; color:var(--g500); margin-bottom:6px; display:flex; align-items:center; gap:6px; }
    .meal-time-dot { width:8px; height:8px; border-radius:50%; }
    .dot-am { background:#F97316; }
    .dot-pm { background:#22C55E; }
    .dot-ev { background:#3B82F6; }
    .meal-inp { width:100%; min-height:60px; padding:8px 10px; border:1.5px solid var(--g200); border-radius:var(--rsm); font-size:12px; font-family:'Noto Sans KR',sans-serif; background:var(--white); resize:vertical; outline:none; transition:border-color .15s; }
    .meal-inp:focus { border-color:var(--blue); }
    .meal-inp::placeholder { color:var(--g400); }
    .allergy-inp { width:100%; padding:6px 10px; border:1.5px solid var(--g200); border-radius:var(--rsm); font-size:12px; font-family:'Noto Sans KR',sans-serif; background:var(--white); outline:none; transition:border-color .15s; }
    .allergy-inp:focus { border-color:var(--blue); }

    /* ── 결과 ── */
    .result-header { background:linear-gradient(135deg,var(--blue) 0%,var(--blue-mid) 100%); color:var(--white); border-radius:var(--radius); padding:18px 20px; margin-bottom:14px; }
    .result-header h2 { font-size:17px; font-weight:700; }
    .result-header .badges { display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }
    .result-badge { background:rgba(255,255,255,.2); border-radius:99px; padding:3px 10px; font-size:11px; font-weight:500; }

    .day-block { background:var(--white); border:1px solid var(--g200); border-radius:var(--radius); margin-bottom:12px; overflow:hidden; box-shadow:var(--shadow); animation:fadeUp .3s ease both; }
    @keyframes fadeUp { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
    .day-block-header { padding:12px 16px; background:var(--g50); border-bottom:1px solid var(--g200); font-size:14px; font-weight:700; color:var(--g700); }
    .meal-result-row { padding:14px 16px; border-bottom:1px solid var(--g100); display:flex; align-items:flex-start; gap:12px; }
    .meal-result-row:last-child { border-bottom:none; }
    .meal-badge { flex-shrink:0; width:42px; font-size:11px; font-weight:700; text-align:center; padding:4px 0; border-radius:6px; }
    .meal-badge.am { background:#FFF7ED; color:#C2410C; }
    .meal-badge.pm { background:#F0FDF4; color:#15803D; }
    .meal-badge.ev { background:#EFF6FF; color:#1D4ED8; }
    .meal-result-content { flex:1; min-width:0; }
    .meal-rec-ok { font-size:11px; font-weight:700; color:var(--green); margin-bottom:4px; display:flex; align-items:center; gap:4px; flex-wrap:wrap; }
    .meal-rec-ng { font-size:11px; font-weight:700; color:var(--red); margin-bottom:4px; }
    .meal-rec-skip { font-size:11px; font-weight:700; color:var(--g400); margin-bottom:4px; }
    .course-tag { display:inline-block; padding:1px 8px; background:var(--blue-light); color:var(--blue); border-radius:99px; font-size:10px; font-weight:700; margin-left:4px; }
    .score-tag { display:inline-block; padding:1px 7px; background:var(--yellow-light); color:#92400E; border-radius:99px; font-size:10px; font-weight:700; margin-left:4px; }
    .meal-menu-text { font-size:13px; color:var(--g700); line-height:1.7; }
    .meal-menu-text.ng { color:var(--g400); font-style:italic; }
    .meal-reason-text { font-size:11px; color:var(--g400); margin-top:4px; line-height:1.6; }

    /* ── 에러 ── */
    .error-box { display:none; background:var(--red-light); border:1px solid #FCA5A5; border-radius:var(--rsm); padding:12px 14px; font-size:13px; color:var(--red); margin-bottom:12px; line-height:1.6; }
    .error-box.show { display:block; }

    /* ── 저장 완료 토스트 ── */
    .toast { position:fixed; bottom:88px; left:50%; transform:translateX(-50%) translateY(20px); background:var(--g900); color:var(--white); padding:10px 20px; border-radius:99px; font-size:13px; font-weight:500; opacity:0; transition:all .3s; pointer-events:none; z-index:999; white-space:nowrap; }
    .toast.show { opacity:1; transform:translateX(-50%) translateY(0); }

    /* ── 하단 고정 버튼 ── */
    .bottom-bar { position:fixed; bottom:0; left:0; right:0; background:var(--white); border-top:1px solid var(--g200); padding:12px 16px; z-index:100; }
    .bottom-bar-inner { max-width:760px; margin:0 auto; }

    @media(max-width:500px) {
      .nav-links a { font-size:11px; padding:6px 7px; }
    }
  </style>
</head>
<body>

<nav class="nav">
  <a class="nav-logo" href="index.html">IDP</a>
  <div class="nav-links">
    <a href="laundry.html">세탁실 현황</a>
    <a href="Menu.html" class="active">메뉴 추천</a>
    <a href="usage.html">내 이용 현황</a>
    <a href="mypage.html">마이 페이지</a>
  </div>
</nav>

<div class="page">

  <!-- 탭 -->
  <div class="tabs">
    <button class="tab active" onclick="switchTab('pref')">⭐ 추천</button>
    <button class="tab" onclick="switchTab('menu')">🏢 기숙사 식당</button>
  </div>

  <!-- ══════════════════════════════════
       탭1: 추천 (선호도 설정 + 결과)
  ══════════════════════════════════ -->
  <div class="tab-panel active" id="tab-pref">

    <div class="error-box" id="errorBox"></div>

    <!-- 선호도 설정 카드 -->
    <div class="card">
      <div class="card-title"><span class="card-icon">⭐</span> 내 메뉴 선호도</div>

      <div class="sec-label">이름</div>
      <input class="inp" id="userName" placeholder="이름 입력 (선택)">

      <div class="sec-label" style="margin-top:14px">선호 유형</div>
      <div class="chip-group" id="likedCuisines">
        <div class="chip" data-val="한식" onclick="tc(this)">한식</div>
        <div class="chip" data-val="양식" onclick="tc(this)">양식</div>
        <div class="chip" data-val="중식" onclick="tc(this)">중식</div>
        <div class="chip" data-val="일식" onclick="tc(this)">일식</div>
      </div>

      <div class="sec-label" style="margin-top:14px">좋아하는 메뉴</div>
      <div class="chip-group" id="likedTypes">
        <div class="chip" data-val="밥" onclick="tc(this)">밥</div>
        <div class="chip" data-val="면" onclick="tc(this)">면</div>
        <div class="chip" data-val="고기" onclick="tc(this)">고기</div>
      </div>

      <div class="sec-label" style="margin-top:14px">싫어하는 메뉴</div>
      <div class="inp-row">
        <input class="inp" id="dislikedInput" placeholder="예) 고수, 당근">
        <button class="btn btn-sm" onclick="addDisliked()">추가</button>
      </div>
      <div class="chip-group" id="dislikedChips" style="margin-top:8px"></div>

      <div class="sec-label" style="margin-top:14px">알레르기</div>
      <div class="chip-group" id="allergies">
        <div class="chip dc" data-val="난류"    onclick="tc(this)">난류</div>
        <div class="chip dc" data-val="우유"    onclick="tc(this)">우유</div>
        <div class="chip dc" data-val="메밀"    onclick="tc(this)">메밀</div>
        <div class="chip dc" data-val="땅콩"    onclick="tc(this)">땅콩</div>
        <div class="chip dc" data-val="대두"    onclick="tc(this)">대두</div>
        <div class="chip dc" data-val="밀"      onclick="tc(this)">밀</div>
        <div class="chip dc" data-val="생선류"  onclick="tc(this)">생선류</div>
        <div class="chip dc" data-val="게"      onclick="tc(this)">게</div>
        <div class="chip dc" data-val="새우"    onclick="tc(this)">새우</div>
        <div class="chip dc" data-val="돼지고기" onclick="tc(this)">돼지고기</div>
        <div class="chip dc" data-val="복숭아"  onclick="tc(this)">복숭아</div>
        <div class="chip dc" data-val="토마토"  onclick="tc(this)">토마토</div>
        <div class="chip dc" data-val="호두"    onclick="tc(this)">호두</div>
        <div class="chip dc" data-val="닭고기"  onclick="tc(this)">닭고기</div>
        <div class="chip dc" data-val="쇠고기"  onclick="tc(this)">쇠고기</div>
        <div class="chip dc" data-val="오징어"  onclick="tc(this)">오징어</div>
        <div class="chip dc" data-val="조개류"  onclick="tc(this)">조개류</div>
      </div>
    </div>

    <!-- 시간표 카드 -->
    <div class="card">
      <div class="card-title"><span class="card-icon">📅</span> 내 시간표</div>
      <p style="font-size:12px;color:var(--g400);margin-bottom:12px">수업 있는 시간대를 클릭해서 표시하세요. 해당 시간 식사는 추천에서 제외됩니다.</p>

      <div class="timetable-wrap">
        <table class="timetable" id="timetable">
          <thead>
            <tr>
              <th style="width:36px"></th>
              <th>월</th><th>화</th><th>수</th><th>목</th><th>금</th>
            </tr>
          </thead>
          <tbody id="ttBody"></tbody>
        </table>
      </div>
      <div class="tt-legend">
        <span><div class="tt-dot" style="background:var(--g100);border:1px solid var(--g300)"></div>공강</span>
        <span><div class="tt-dot" style="background:#A5B4FC"></div>수업</span>
      </div>
    </div>

    <!-- 추천 결과 -->
    <div id="resultSection" style="display:none">
      <div class="result-header" id="resultHeader"></div>
      <div id="resultCards"></div>
    </div>

  </div><!-- /tab-pref -->

  <!-- ══════════════════════════════════
       탭2: 기숙사 식당 (식단 입력)
  ══════════════════════════════════ -->
  <div class="tab-panel" id="tab-menu">
    <div class="card">
      <div class="card-title"><span class="card-icon">📋</span> 주간 식단 입력</div>
      <p style="font-size:12px;color:var(--g400);margin-bottom:16px">각 요일·시간대의 메뉴를 입력하세요. 점심은 A/B코스를 구분해 입력하세요.</p>
      <div id="mealInputCards"></div>
    </div>
  </div>

</div><!-- /page -->

<!-- 하단 고정 버튼 -->
<div class="bottom-bar">
  <div class="bottom-bar-inner">
    <div id="bottomPref" style="display:flex;gap:8px">
      <button class="btn btn-primary" onclick="savePrefs()" style="flex:1">저장하기</button>
      <button class="btn btn-primary" onclick="recommend()" style="flex:1;background:var(--green)">✨ 추천받기</button>
    </div>
    <div id="bottomMenu" style="display:none">
      <button class="btn btn-primary" onclick="saveMenuData()">💾 식단 저장하기</button>
    </div>
  </div>
</div>

<!-- 토스트 -->
<div class="toast" id="toast"></div>

<script>
'use strict';

// ================================================================
// 전역 상태
// ================================================================
const DAYS  = ['월','화','수','목','금'];
const MEALS = ['아침','점심','저녁'];

// 시간표: 7:00~21:00, 30분 단위 → 28슬롯
const SLOT_START = 7;   // 7시부터
const SLOT_END   = 21;  // 21시까지
const SLOTS      = (SLOT_END - SLOT_START) * 2; // 28슬롯

// 식사 시간대 슬롯 범위 (인덱스)
// 아침: 07:30~09:00 → slot 1~3
// 점심: 11:30~13:30 → slot 9~12
// 저녁: 17:30~19:30 → slot 21~24
const MEAL_SLOTS = {
  '아침': [1, 2, 3],
  '점심': [9, 10, 11, 12],
  '저녁': [21, 22, 23, 24]
};

// 시간표 데이터: busy[day][slot] = true/false
let busy = {};
DAYS.forEach(d => { busy[d] = {}; });

// 식단 데이터
let menuData = {};
DAYS.forEach(d => {
  menuData[d] = {
    아침: { menus: [], allergy: [] },
    점심: {
      A코스: { menus: [], allergy: [], type: '', cuisine: '' },
      B코스: { menus: [], allergy: [], type: '', cuisine: '' }
    },
    저녁: { menus: [], allergy: [] }
  };
});

// 싫어하는 재료 (동적)
let dislikedList = [];

// ================================================================
// 초기화
// ================================================================
window.addEventListener('DOMContentLoaded', () => {
  buildTimetable();
  buildMealInputCards();
  loadStorage();
});

// ── 탭 전환 ────────────────────────────────────────────────────
function switchTab(tab) {
  document.querySelectorAll('.tab').forEach((t, i) => {
    const names = ['pref', 'menu'];
    t.classList.toggle('active', names[i] === tab);
  });
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('tab-' + tab).classList.add('active');
  document.getElementById('bottomPref').style.display = tab === 'pref' ? 'flex' : 'none';
  document.getElementById('bottomMenu').style.display = tab === 'menu' ? 'block' : 'none';
}

// ================================================================
// 시간표 빌드
// ================================================================
function buildTimetable() {
  const tbody = document.getElementById('ttBody');
  tbody.innerHTML = '';
  for (let s = 0; s < SLOTS; s++) {
    const hour   = SLOT_START + Math.floor(s / 2);
    const min    = s % 2 === 0 ? '00' : '30';
    const label  = min === '00' ? hour + ':00' : '';
    const tr     = document.createElement('tr');
    tr.innerHTML = `<td class="time-label">${label}</td>` +
      DAYS.map(d =>
        `<td><div class="time-slot empty" id="slot-${d}-${s}" onclick="toggleSlot('${d}',${s})"></div></td>`
      ).join('');
    tbody.appendChild(tr);
  }
}

function toggleSlot(day, slot) {
  busy[day][slot] = !busy[day][slot];
  const el = document.getElementById(`slot-${day}-${slot}`);
  el.className = 'time-slot ' + (busy[day][slot] ? 'busy' : 'empty');
}

// 식사 시간대에 수업이 1슬롯이라도 있으면 불가
function isMealBlocked(day, mealName) {
  const slots = MEAL_SLOTS[mealName] || [];
  return slots.some(s => busy[DAYS.indexOf(day) >= 0 ? day : day][s]);
}

// ================================================================
// 식단 입력 카드 빌드
// ================================================================
function buildMealInputCards() {
  const wrap = document.getElementById('mealInputCards');
  wrap.innerHTML = '';
  DAYS.forEach(d => {
    const fullDay = d + '요일';
    const div = document.createElement('div');
    div.className = 'meal-day-card';
    div.innerHTML = `
      <div class="meal-day-header" onclick="toggleDayCard('${d}')">
        <span>${fullDay}</span>
        <span id="arrow-${d}" style="font-size:12px;color:var(--g400)">▼</span>
      </div>
      <div class="meal-day-body" id="body-${d}">
        <!-- 아침 -->
        <div class="meal-time-section">
          <div class="meal-time-label">
            <div class="meal-time-dot dot-am"></div> 아침
            <span style="font-size:10px;color:var(--g400)">07:30~09:00</span>
          </div>
          <textarea class="meal-inp" id="menu-${d}-아침"
            placeholder="예) 흑미밥, 된장찌개, 제육볶음, 깍두기"></textarea>
          <input class="allergy-inp" id="allergy-${d}-아침" style="margin-top:4px"
            placeholder="알레르기 재료 (쉼표 구분): 예) 대두, 돼지고기">
        </div>
        <!-- 점심 A -->
        <div class="meal-time-section">
          <div class="meal-time-label">
            <div class="meal-time-dot dot-pm"></div> 점심 A코스
            <span style="font-size:10px;color:var(--g400)">11:30~13:30</span>
          </div>
          <textarea class="meal-inp" id="menu-${d}-점심A"
            placeholder="예) 짜장면, 군만두, 단무지"></textarea>
          <input class="allergy-inp" id="allergy-${d}-점심A" style="margin-top:4px"
            placeholder="알레르기 재료 (쉼표 구분)">
        </div>
        <!-- 점심 B -->
        <div class="meal-time-section">
          <div class="meal-time-label">
            <div class="meal-time-dot dot-pm"></div> 점심 B코스
          </div>
          <textarea class="meal-inp" id="menu-${d}-점심B"
            placeholder="예) 돈까스, 공기밥, 미소국, 샐러드"></textarea>
          <input class="allergy-inp" id="allergy-${d}-점심B" style="margin-top:4px"
            placeholder="알레르기 재료 (쉼표 구분)">
        </div>
        <!-- 저녁 -->
        <div class="meal-time-section">
          <div class="meal-time-label">
            <div class="meal-time-dot dot-ev"></div> 저녁
            <span style="font-size:10px;color:var(--g400)">17:30~19:30</span>
          </div>
          <textarea class="meal-inp" id="menu-${d}-저녁"
            placeholder="예) 현미밥, 부대찌개, 고등어구이, 나물"></textarea>
          <input class="allergy-inp" id="allergy-${d}-저녁" style="margin-top:4px"
            placeholder="알레르기 재료 (쉼표 구분)">
        </div>
      </div>`;
    wrap.appendChild(div);
  });
}

function toggleDayCard(day) {
  const body  = document.getElementById('body-' + day);
  const arrow = document.getElementById('arrow-' + day);
  const open  = body.classList.toggle('open');
  arrow.textContent = open ? '▲' : '▼';
}

// ================================================================
// 칩 토글
// ================================================================
function tc(el) {
  const isSel = el.classList.contains('sel');
  if (isSel) {
    el.classList.remove('sel');
  } else {
    el.classList.add('sel');
  }
}
function gc(id) {
  return [...document.querySelectorAll('#' + id + ' .chip.sel')].map(c => c.dataset.val);
}

// ================================================================
// 싫어하는 재료 동적 추가
// ================================================================
function addDisliked() {
  const inp = document.getElementById('dislikedInput');
  const vals = inp.value.split(',').map(s => s.trim()).filter(Boolean);
  vals.forEach(v => {
    if (!dislikedList.includes(v)) {
      dislikedList.push(v);
    }
  });
  inp.value = '';
  renderDislikedChips();
}

function renderDislikedChips() {
  const group = document.getElementById('dislikedChips');
  group.innerHTML = '';
  dislikedList.forEach(v => {
    const c = document.createElement('div');
    c.className = 'chip sel';
    c.style.background = 'var(--g100)';
    c.style.borderColor = 'var(--g300)';
    c.style.color = 'var(--g700)';
    c.textContent = v + ' ✕';
    c.onclick = () => {
      dislikedList = dislikedList.filter(x => x !== v);
      renderDislikedChips();
    };
    group.appendChild(c);
  });
}

// ================================================================
// 식단 데이터 읽기
// ================================================================
function readMenuFromInputs() {
  const result = {};
  DAYS.forEach(d => {
    const fullDay = d + '요일';
    result[fullDay] = {};

    // 아침
    result[fullDay]['아침'] = {
      menus: parseMenuText(getVal(`menu-${d}-아침`)),
      allergy: parseComma(getVal(`allergy-${d}-아침`))
    };
    // 점심 A/B
    result[fullDay]['점심'] = {
      A코스: {
        menus: parseMenuText(getVal(`menu-${d}-점심A`)),
        allergy: parseComma(getVal(`allergy-${d}-점심A`))
      },
      B코스: {
        menus: parseMenuText(getVal(`menu-${d}-점심B`)),
        allergy: parseComma(getVal(`allergy-${d}-점심B`))
      }
    };
    // 저녁
    result[fullDay]['저녁'] = {
      menus: parseMenuText(getVal(`menu-${d}-저녁`)),
      allergy: parseComma(getVal(`allergy-${d}-저녁`))
    };
  });
  return result;
}

function getVal(id) {
  const el = document.getElementById(id);
  return el ? el.value.trim() : '';
}
function parseMenuText(str) {
  return str ? str.split(/[,，\n]/).map(s => s.trim()).filter(Boolean) : [];
}
function parseComma(str) {
  return str ? str.split(',').map(s => s.trim()).filter(Boolean) : [];
}

// ================================================================
// 저장 / 불러오기
// ================================================================
function savePrefs() {
  const prefs = {
    name:     document.getElementById('userName').value.trim(),
    cuisines: gc('likedCuisines'),
    types:    gc('likedTypes'),
    disliked: dislikedList,
    allergy:  gc('allergies'),
    busy:     busy
  };
  localStorage.setItem('idp_prefs', JSON.stringify(prefs));
  showToast('선호도 저장 완료! ✓');
}

function saveMenuData() {
  const data = readMenuFromInputs();
  localStorage.setItem('idp_menu', JSON.stringify(data));
  showToast('식단 저장 완료! ✓');
}

function loadStorage() {
  // 선호도 불러오기
  try {
    const prefs = JSON.parse(localStorage.getItem('idp_prefs') || '{}');
    if (prefs.name)     document.getElementById('userName').value = prefs.name;
    if (prefs.cuisines) prefs.cuisines.forEach(v => selectChip('likedCuisines', v));
    if (prefs.types)    prefs.types.forEach(v => selectChip('likedTypes', v));
    if (prefs.allergy)  prefs.allergy.forEach(v => selectChip('allergies', v));
    if (prefs.disliked) { dislikedList = prefs.disliked; renderDislikedChips(); }
    if (prefs.busy) {
      busy = prefs.busy;
      DAYS.forEach(d => {
        Object.keys(busy[d] || {}).forEach(s => {
          if (busy[d][s]) {
            const el = document.getElementById(`slot-${d}-${s}`);
            if (el) el.className = 'time-slot busy';
          }
        });
      });
    }
  } catch(_) {}

  // 식단 불러오기
  try {
    const saved = JSON.parse(localStorage.getItem('idp_menu') || '{}');
    DAYS.forEach(d => {
      const fullDay = d + '요일';
      const sd = saved[fullDay];
      if (!sd) return;
      setVal(`menu-${d}-아침`,  (sd['아침']?.menus || []).join(', '));
      setVal(`allergy-${d}-아침`, (sd['아침']?.allergy || []).join(', '));
      setVal(`menu-${d}-점심A`,  (sd['점심']?.A코스?.menus || []).join(', '));
      setVal(`allergy-${d}-점심A`, (sd['점심']?.A코스?.allergy || []).join(', '));
      setVal(`menu-${d}-점심B`,  (sd['점심']?.B코스?.menus || []).join(', '));
      setVal(`allergy-${d}-점심B`, (sd['점심']?.B코스?.allergy || []).join(', '));
      setVal(`menu-${d}-저녁`,  (sd['저녁']?.menus || []).join(', '));
      setVal(`allergy-${d}-저녁`, (sd['저녁']?.allergy || []).join(', '));
    });
  } catch(_) {}
}

function setVal(id, val) {
  const el = document.getElementById(id);
  if (el) el.value = val;
}

function selectChip(groupId, val) {
  const chips = document.querySelectorAll('#' + groupId + ' .chip');
  chips.forEach(c => { if (c.dataset.val === val) c.classList.add('sel'); });
}

// ================================================================
// 핵심: 규칙 기반 추천 엔진 (API 없음)
// ================================================================
function recommend() {
  clearErr();
  document.getElementById('resultSection').style.display = 'none';

  const menu = readMenuFromInputs();
  const hasMenu = DAYS.some(d => {
    const fd = d + '요일';
    return (menu[fd]?.아침?.menus?.length > 0) ||
           (menu[fd]?.저녁?.menus?.length > 0) ||
           (menu[fd]?.점심?.A코스?.menus?.length > 0);
  });

  if (!hasMenu) {
    showErr('먼저 "기숙사 식당" 탭에서 이번 주 식단을 입력해주세요.');
    return;
  }

  const profile = {
    name:     document.getElementById('userName').value.trim() || '사용자',
    cuisines: gc('likedCuisines'),
    types:    gc('likedTypes'),
    disliked: dislikedList,
    allergy:  gc('allergies')
  };

  // 요일별 추천 계산
  const results = {};
  DAYS.forEach(d => {
    const fullDay = d + '요일';
    const dayMenu = menu[fullDay];
    results[fullDay] = {};

    // 아침
    results[fullDay]['아침'] = calcMeal(
      dayMenu['아침'], null, profile, isMealBlocked(d, '아침'), fullDay, '아침'
    );

    // 점심 (A/B 비교)
    const lunchBlocked = isMealBlocked(d, '점심');
    if (lunchBlocked) {
      results[fullDay]['점심'] = { status: 'blocked', reason: '점심 시간 수업/연강으로 식사 불가' };
    } else {
      const scoreA = calcMeal(dayMenu['점심']['A코스'], 'A코스', profile, false, fullDay, '점심');
      const scoreB = calcMeal(dayMenu['점심']['B코스'], 'B코스', profile, false, fullDay, '점심');
      // 둘 다 알레르기 제외면 전체 제외
      if (scoreA.status === 'allergy' && scoreB.status === 'allergy') {
        results[fullDay]['점심'] = { status: 'allergy', reason: 'A·B코스 모두 알레르기 성분 포함' };
      } else if (scoreA.status === 'empty' && scoreB.status === 'empty') {
        results[fullDay]['점심'] = { status: 'empty', reason: '점심 메뉴 미입력' };
      } else {
        // 점수 높은 코스 선택
        const chosen = (scoreA.score >= scoreB.score && scoreA.status !== 'allergy')
          ? scoreA : (scoreB.status !== 'allergy' ? scoreB : scoreA);
        results[fullDay]['점심'] = chosen;
      }
    }

    // 저녁
    results[fullDay]['저녁'] = calcMeal(
      dayMenu['저녁'], null, profile, isMealBlocked(d, '저녁'), fullDay, '저녁'
    );
  });

  renderRecommendation(results, profile);
}

// ── 단일 식사 점수 계산 ─────────────────────────────────────────
function calcMeal(mealInfo, course, profile, blocked, day, mealTime) {
  if (blocked) return { status: 'blocked', reason: mealTime + ' 시간 수업/연강으로 식사 불가', course };

  const menus   = mealInfo?.menus || [];
  const allergy = mealInfo?.allergy || [];

  if (menus.length === 0) return { status: 'empty', reason: '메뉴 미입력', course };

  // 알레르기 체크 (하드 필터)
  const userAllergy = new Set(profile.allergy);
  const allergyHit  = allergy.filter(a => userAllergy.has(a));
  if (allergyHit.length > 0) {
    return { status: 'allergy', reason: '알레르기 성분 포함: ' + allergyHit.join(', '), menus, course };
  }

  // 점수 계산
  let score = 50; // 기본 점수
  const menuText = menus.join(' ');
  const reasons  = [];

  // 좋아하는 국가 +20
  profile.cuisines.forEach(c => {
    if (isMatchCuisine(menuText, c)) { score += 20; reasons.push(c + ' 선호 반영'); }
  });

  // 좋아하는 종류 +15
  profile.types.forEach(t => {
    if (isMatchType(menuText, t)) { score += 15; reasons.push(t + ' 종류 선호 반영'); }
  });

  // 싫어하는 재료 -25
  const dislikedHit = profile.disliked.filter(d => menuText.includes(d));
  if (dislikedHit.length > 0) {
    score -= 25;
    reasons.push('비선호 재료 포함: ' + dislikedHit.join(', '));
  }

  const reasonStr = reasons.length > 0
    ? reasons.join(' · ')
    : (profile.cuisines.length === 0 && profile.types.length === 0
        ? '기본 추천 메뉴입니다.'
        : '선호도와 적합한 메뉴입니다.');

  return { status: 'ok', score, menus, allergy, course, reason: reasonStr };
}

// ── 국가/종류 매칭 ──────────────────────────────────────────────
function isMatchCuisine(text, cuisine) {
  const map = {
    '한식': ['밥','국','찌개','김치','나물','볶음','구이','조림','탕','비빔','된장','고추장'],
    '양식': ['파스타','스테이크','샐러드','빵','크림','피자','버거','스프'],
    '중식': ['짜장','짬뽕','탕수육','볶음밥','만두','마파두부'],
    '일식': ['우동','라멘','돈까스','초밥','덮밥','미소','규동','오야코']
  };
  return (map[cuisine] || []).some(kw => text.includes(kw));
}

function isMatchType(text, type) {
  const map = {
    '밥': ['밥','공기','덮밥','볶음밥','비빔밥'],
    '면': ['면','국수','라면','파스타','우동','짜장','짬뽕'],
    '고기': ['제육','불고기','삼겹','돼지','닭','쇠고기','갈비','닭갈비','스테이크','돈까스']
  };
  return (map[type] || []).some(kw => text.includes(kw));
}

// ================================================================
// 추천 결과 렌더링
// ================================================================
function renderRecommendation(results, profile) {
  const alStr = profile.allergy.length ? '알레르기: ' + profile.allergy.join(', ') : '알레르기 없음';

  // 시간표에서 불가 시간대 추출
  const blockedMeals = [];
  DAYS.forEach(d => {
    MEALS.forEach(m => { if (isMealBlocked(d, m)) blockedMeals.push(m); });
  });
  const uniqueBlocked = [...new Set(blockedMeals)];
  const blStr = uniqueBlocked.length ? '불가: ' + uniqueBlocked.join(', ') : '';

  document.getElementById('resultHeader').innerHTML =
    '<h2>✨ ' + esc(profile.name) + ' 님 추천 결과</h2>' +
    '<div class="badges">' +
    '<span class="result-badge">' + esc(alStr) + '</span>' +
    (blStr ? '<span class="result-badge">' + esc(blStr) + '</span>' : '') +
    '</div>';

  const cont = document.getElementById('resultCards');
  cont.innerHTML = '';

  DAYS.forEach((d, idx) => {
    const fullDay = d + '요일';
    const dayRes  = results[fullDay];
    if (!dayRes) return;

    const card = document.createElement('div');
    card.className = 'day-block';
    card.style.animationDelay = (idx * 60) + 'ms';

    let rows = '';
    MEALS.forEach(meal => {
      const r = dayRes[meal];
      if (!r) return;
      const badgeCls = meal === '아침' ? 'am' : meal === '점심' ? 'pm' : 'ev';
      let statusHtml, menuHtml, reasonHtml;

      if (r.status === 'ok') {
        const courseTag = r.course ? `<span class="course-tag">${esc(r.course)}</span>` : '';
        const scoreTag  = r.score  ? `<span class="score-tag">점수 ${r.score}</span>` : '';
        statusHtml = `<div class="meal-rec-ok">✔ 추천${courseTag}${scoreTag}</div>`;
        menuHtml   = `<div class="meal-menu-text">${esc((r.menus||[]).join(', '))}</div>`;
        reasonHtml = `<div class="meal-reason-text">${esc(r.reason)}</div>`;
      } else if (r.status === 'allergy') {
        statusHtml = `<div class="meal-rec-ng">✘ 제외 (알레르기)</div>`;
        menuHtml   = `<div class="meal-menu-text ng">${esc((r.menus||[]).join(', ') || '제외됨')}</div>`;
        reasonHtml = `<div class="meal-reason-text">${esc(r.reason)}</div>`;
      } else if (r.status === 'blocked') {
        statusHtml = `<div class="meal-rec-skip">— 수업 시간</div>`;
        menuHtml   = `<div class="meal-menu-text ng">식사 불가</div>`;
        reasonHtml = `<div class="meal-reason-text">${esc(r.reason)}</div>`;
      } else {
        statusHtml = `<div class="meal-rec-skip">— 미입력</div>`;
        menuHtml   = `<div class="meal-menu-text ng">식단 미입력</div>`;
        reasonHtml = `<div class="meal-reason-text">기숙사 식당 탭에서 식단을 입력해주세요.</div>`;
      }

      rows += `
        <div class="meal-result-row">
          <div class="meal-badge ${badgeCls}">${esc(meal)}</div>
          <div class="meal-result-content">
            ${statusHtml}${menuHtml}${reasonHtml}
          </div>
        </div>`;
    });

    card.innerHTML = `<div class="day-block-header">${esc(fullDay)}</div>${rows}`;
    cont.appendChild(card);
  });

  document.getElementById('resultSection').style.display = 'block';
  document.getElementById('resultSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ================================================================
// UI 유틸
// ================================================================
function showErr(msg) {
  const e = document.getElementById('errorBox');
  e.textContent = '⚠️ ' + msg;
  e.classList.add('show');
  e.scrollIntoView({ behavior: 'smooth', block: 'center' });
}
function clearErr() { document.getElementById('errorBox').classList.remove('show'); }

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2200);
}

function esc(s) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
</script>
</body>
</html>
