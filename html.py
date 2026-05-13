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
      --blue: #1A6FD4; --blue-light: #E8F0FD; --blue-mid: #4A90E2;
      --green: #16A34A; --red: #DC2626; --red-light: #FEE2E2;
      --amber: #D97706; --amber-light: #FEF3C7;
      --g50: #F8FAFC; --g100: #F1F5F9; --g200: #E2E8F0; --g300: #CBD5E1;
      --g400: #94A3B8; --g500: #64748B; --g700: #334155; --g900: #0F172A;
      --white: #fff; --radius: 12px; --rsm: 8px;
      --shadow: 0 1px 3px rgba(0,0,0,.08), 0 4px 16px rgba(0,0,0,.06);
    }
    body { font-family: 'Noto Sans KR', sans-serif; background: var(--g50); color: var(--g900); min-height: 100vh; }
    .nav { position: sticky; top: 0; z-index: 100; background: var(--white); border-bottom: 1px solid var(--g200); height: 56px; display: flex; align-items: center; padding: 0 20px; gap: 8px; }
    .nav-logo { font-family: 'Bebas Neue', sans-serif; font-size: 22px; color: var(--blue); text-decoration: none; }
    .page { max-width: 720px; margin: 0 auto; padding: 28px 16px 80px; }

    /* 섹션 전환 */
    .section { display: none; animation: fadeIn 0.4s ease-out; }
    .section.active { display: block; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

    /* 카드 및 레이아웃 */
    .card { background: var(--white); border: 1px solid var(--g200); border-radius: var(--radius); padding: 24px; box-shadow: var(--shadow); margin-bottom: 16px; text-align: center; }
    .card-title { font-size: 15px; font-weight: 700; color: var(--g700); margin-bottom: 20px; display: flex; align-items: center; gap: 8px; justify-content: flex-start; }
    .step-badge { width: 22px; height: 22px; border-radius: 50%; background: var(--blue); color: var(--white); font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }

    /* 폼 스타일 */
    .form-group { margin-bottom: 20px; text-align: center; }
    .form-label { font-size: 13px; font-weight: 500; color: var(--g500); margin-bottom: 10px; display: block; }
    .form-input { width: 100%; max-width: 480px; height: 44px; padding: 0 14px; border: 1px solid var(--g200); border-radius: var(--rsm); background: var(--g50); margin: 0 auto; display: block; }
    
    /* 칩 스타일 (사진 속 디자인) */
    .chip-group { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-bottom: 10px; }
    .chip { padding: 8px 16px; border: 1px solid var(--g200); border-radius: 99px; font-size: 13px; background: white; cursor: pointer; transition: 0.2s; user-select: none; }
    .chip:hover { border-color: var(--blue-mid); }
    .chip.selected { background: var(--blue-light); border-color: var(--blue); color: var(--blue); }
    .chip.dc.selected { background: var(--red-light); border-color: var(--red); color: var(--red); }
    .chip.wc.selected { background: var(--amber-light); border-color: var(--amber); color: var(--amber); }

    /* 업로드 */
    .upload-zone { border: 2px dashed var(--g300); border-radius: var(--radius); padding: 32px 16px; cursor: pointer; position: relative; margin-bottom: 10px; }
    .upload-zone input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
    .preview-img { width: 100%; max-height: 280px; object-fit: cover; border-radius: var(--rsm); margin-top: 12px; }

    /* 버튼 */
    .btn-main { display: flex; align-items: center; justify-content: center; width: 100%; max-width: 480px; height: 54px; background: var(--blue); color: var(--white); border: none; border-radius: var(--rsm); font-size: 16px; font-weight: 700; cursor: pointer; margin: 20px auto; }
    .btn-main:active { transform: scale(0.98); }

    /* 로딩/결과 */
    .loading { display: none; text-align: center; padding: 40px 0; }
    .spinner { width: 40px; height: 40px; border: 4px solid var(--g200); border-top-color: var(--blue); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 16px; }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>

<nav class="nav"><a class="nav-logo" href="#" onclick="location.reload()">IDP</a></nav>

<div class="page">
  
  <!-- ──────────────── SECTION 1: 안내 화면 ──────────────── -->
  <section id="section-intro" class="section active">
    <div style="text-align: center; margin-bottom: 30px;">
      <div style="font-size: 50px; margin-bottom: 10px;">🍽️</div>
      <h1 style="font-size: 24px; font-weight: 700;">AI 메뉴 추천</h1>
      <p style="font-size: 14px; color: var(--g500); margin-top: 5px;">이번 주 식단표 이미지를 업로드하면<br>AI가 내 알레르기·선호도·시간표에 맞는 맞춤 메뉴를 추천해드려요</p>
    </div>

    <div class="card">
      <div class="card-title">AI 추천 시작하기</div>
      <div style="background: var(--blue-light); border-radius: 8px; padding: 15px; font-size: 13px; color: #1E40AF; text-align: left; line-height: 1.6; margin-bottom: 20px;">
        <strong>💡 어떻게 동작하나요?</strong><br>
        식단표 이미지를 업로드하면 Gemini AI가 자동으로 메뉴를 분석하고, 내 알레르기·선호도·시간표를 반영해 최적의 식사를 추천해드립니다.
      </div>
      <button class="btn-main" onclick="showStep2()">✨ AI 메뉴 추천 열기</button>
      <p style="font-size: 12px; color: var(--g400); margin-top: 10px;">Google 서버에서 실행됩니다 · 별도 앱 설치 불필요</p>
    </div>
  </section>

  <!-- ──────────────── SECTION 2: 입력 화면 (사진 속 모든 옵션 구현) ──────────────── -->
  <section id="section-main" class="section">
    <div style="text-align: center; margin-bottom: 24px;">
      <h2 style="font-size: 20px; font-weight: 700;">🍽️ AI 메뉴 추천</h2>
      <p style="font-size: 13px; color: var(--g500);">이미지를 업로드하고 정보를 입력해주세요</p>
    </div>

    <!-- 1. 이미지 업로드 -->
    <div class="card">
      <div class="card-title"><span class="step-badge">1</span> 이번 주 식단표 이미지 업로드</div>
      <div class="upload-zone">
        <input type="file" accept="image/*" onchange="handleFile(this)">
        <div id="upload-placeholder">
          <div style="font-size:40px;">🖼️</div>
          <div style="font-size:14px; color:var(--g700); font-weight:500; margin-top:8px;">이미지를 드래그하거나 클릭해서 선택</div>
          <div style="font-size:12px; color:var(--g400); margin-top:4px;">PNG · JPG · WEBP 지원</div>
        </div>
        <img id="previewImg" class="preview-img" style="display:none;">
      </div>
    </div>

    <!-- 2. 내 정보 입력 (여기가 핵심!) -->
    <div class="card">
      <div class="card-title"><span class="step-badge">2</span> 내 정보 입력</div>
      
      <div class="form-group">
        <label class="form-label">이름</label>
        <input class="form-input" id="userName" placeholder="홍길동">
      </div>

      <div class="form-group">
        <label class="form-label">좋아하는 식사 종류</label>
        <div class="chip-group" id="likedTypes">
          <div class="chip" onclick="tc(this)">🍚 밥</div>
          <div class="chip" onclick="tc(this)">🍜 면</div>
          <div class="chip" onclick="tc(this)">🍞 빵</div>
          <div class="chip" onclick="tc(this)">🍡 떡</div>
          <div class="chip" onclick="tc(this)">기타</div>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">좋아하는 국가별 음식</label>
        <div class="chip-group" id="likedCuisines">
          <div class="chip" onclick="tc(this)">🇰🇷 한식</div>
          <div class="chip" onclick="tc(this)">🍝 양식</div>
          <div class="chip" onclick="tc(this)">🥡 중식</div>
          <div class="chip" onclick="tc(this)">🍱 일식</div>
          <div class="chip" onclick="tc(this)">🌿 동남아식</div>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">싫어하는 재료 / 메뉴 (쉼표로 구분)</label>
        <input class="form-input" id="disliked" placeholder="고수, 민트, 해산물">
      </div>

      <div class="form-group">
        <label class="form-label">⚠️ 알레르기 재료</label>
        <div class="chip-group" id="allergies">
          <div class="chip dc" onclick="tc(this)">난류</div>
          <div class="chip dc" onclick="tc(this)">우유</div>
          <div class="chip dc" onclick="tc(this)">메밀</div>
          <div class="chip dc" onclick="tc(this)">땅콩</div>
          <div class="chip dc" onclick="tc(this)">대두</div>
          <div class="chip dc" onclick="tc(this)">밀</div>
          <div class="chip dc" onclick="tc(this)">생선류</div>
          <div class="chip dc" onclick="tc(this)">게</div>
          <div class="chip dc" onclick="tc(this)">새우</div>
          <div class="chip dc" onclick="tc(this)">돼지고기</div>
          <div class="chip dc" onclick="tc(this)">복숭아</div>
          <div class="chip dc" onclick="tc(this)">토마토</div>
          <div class="chip dc" onclick="tc(this)">호두</div>
          <div class="chip dc" onclick="tc(this)">닭고기</div>
          <div class="chip dc" onclick="tc(this)">쇠고기</div>
          <div class="chip dc" onclick="tc(this)">오징어</div>
          <div class="chip dc" onclick="tc(this)">조개류</div>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">🕐 수업/연강으로 식사 불가한 시간대</label>
        <div class="chip-group" id="blockedTimes">
          <div class="chip wc" onclick="tc(this)">아침</div>
          <div class="chip wc" onclick="tc(this)">점심</div>
          <div class="chip wc" onclick="tc(this)">저녁</div>
        </div>
      </div>
    </div>

    <button class="btn-main" id="runBtn" onclick="runAI()">✨ AI 메뉴 추천받기</button>

    <div class="loading" id="loading">
      <div class="spinner"></div>
      <div id="loadingMsg" style="font-weight: 500;">식단표 분석 중...</div>
      <div style="font-size:12px; color:var(--g400); margin-top:5px;">잠시만 기다려주세요 (약 20초)</div>
    </div>

    <div id="resultSection" style="display:none; margin-top: 30px;">
      <!-- 여기에 결과가 렌더링됩니다 -->
    </div>
  </section>
</div>

<script>
  // GAS 설정
  const GAS_URL = 'https://script.google.com/macros/s/AKfycbxaIeJ5hkoOCf1VZdmfK4vfZjaBXQWZ-UoOLlL4scxiJsjsSHVGHfksv8B-NbWsnctj/exec';
  let b64 = null, mime = null;

  // 화면 전환
  function showStep2() {
    document.getElementById('section-intro').classList.remove('active');
    document.getElementById('section-main').classList.add('active');
    window.scrollTo(0,0);
  }

  // 칩 선택 (Toggle)
  function tc(el) { el.classList.toggle('selected'); }

  // 이미지 핸들링
  function handleFile(input) {
    const file = input.files[0];
    if (!file) return;
    mime = file.type;
    const reader = new FileReader();
    reader.onload = e => {
      b64 = e.target.result.split(',')[1];
      document.getElementById('previewImg').src = e.target.result;
      document.getElementById('previewImg').style.display = 'block';
      document.getElementById('upload-placeholder').style.display = 'none';
    };
    reader.readAsDataURL(file);
  }

  // GAS 호출용
  function gas(fn, ...args) {
    return new Promise((res, rej) => {
      google.script.run.withSuccessHandler(res).withFailureHandler(rej)[fn](...args);
    });
  }

  // 메인 로직
  async function runAI() {
    if (!b64) { alert('식단표 이미지를 먼저 업로드해주세요.'); return; }
    
    document.getElementById('runBtn').style.display = 'none';
    document.getElementById('loading').style.display = 'block';
    document.getElementById('resultSection').style.display = 'none';

    const profile = {
      name: document.getElementById('userName').value,
      types: Array.from(document.querySelectorAll('#likedTypes .selected')).map(c => c.innerText),
      cuisines: Array.from(document.querySelectorAll('#likedCuisines .selected')).map(c => c.innerText),
      disliked: document.getElementById('disliked').value,
      allergies: Array.from(document.querySelectorAll('#allergies .selected')).map(c => c.innerText),
      blocked: Array.from(document.querySelectorAll('#blockedTimes .selected')).map(c => c.innerText)
    };

    try {
      const menuData = await gas('clientParseMenuImage', b64, mime);
      const recommendation = await gas('clientGetRecommendation', menuData, profile);
      
      document.getElementById('loading').style.display = 'none';
      const resSec = document.getElementById('resultSection');
      resSec.style.display = 'block';
      resSec.innerHTML = `<div class="card" style="text-align:left;">
        <div class="card-title">✨ AI 추천 결과</div>
        <div style="font-size:14px; line-height:1.7; white-space:pre-wrap;">${recommendation}</div>
      </div>`;
    } catch (e) {
      alert('오류: ' + e.message);
      document.getElementById('runBtn').style.display = 'flex';
      document.getElementById('loading').style.display = 'none';
    }
  }
</script>
</body>
</html>