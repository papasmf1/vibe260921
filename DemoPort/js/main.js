(() => {
  'use strict';

  document.documentElement.classList.add('js');

  // ---------- 데이터 ----------
  const SKILLS = [
    {
      icon: '🤖',
      name: '바이브코딩',
      level: 90,
      desc: 'AI와 대화하며 아이디어를 빠르게 프로토타입하고 완성도 있는 결과물로 다듬습니다.',
    },
    {
      icon: '🐍',
      name: 'Python',
      level: 85,
      desc: '자동화, 데이터 처리, 게임 등 다양한 용도의 스크립트와 애플리케이션을 개발합니다.',
    },
    {
      icon: '🌐',
      name: 'HTML5',
      level: 85,
      desc: '시맨틱 마크업과 CSS3, JavaScript로 반응형·접근성 좋은 웹 페이지를 만듭니다.',
    },
  ];

  const PROJECTS = [
    {
      title: '테트리스',
      desc: 'HTML5 Canvas로 만든 테트리스. 홀드, 고스트 블록, 레벨 시스템을 지원합니다.',
      tech: ['HTML5', 'CSS3', 'JavaScript'],
      link: '../Game01/tetris.html',
    },
    {
      title: '뱀 게임: 사람 vs AI',
      desc: '사람이 조작하는 뱀과 BFS 기반 AI 뱀이 하나의 사과를 두고 경쟁하는 Python 게임.',
      tech: ['Python', 'tkinter', 'BFS'],
      link: '',
    },
    {
      title: '개발자 프로필 사이트',
      desc: '바로 이 사이트. 프레임워크 없이 정적 파일로 구성한 반응형 포트폴리오.',
      tech: ['HTML5', 'CSS3', 'JavaScript'],
      link: '#hero',
    },
  ];

  const EMAIL = 'papasmf1@gmail.com';

  // ---------- 렌더링 ----------
  const el = (tag, cls, html) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html !== undefined) n.innerHTML = html;
    return n;
  };
  const esc = s => String(s).replace(/[&<>"']/g, c => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));

  const skillsGrid = document.getElementById('skills-grid');
  SKILLS.forEach(s => {
    const card = el('article', 'card reveal');
    card.innerHTML = `
      <span class="icon" aria-hidden="true">${s.icon}</span>
      <h3>${esc(s.name)}</h3>
      <p>${esc(s.desc)}</p>
      <span class="level-label">숙련도 ${s.level}%</span>
      <div class="meter" role="progressbar" aria-label="${esc(s.name)} 숙련도"
           aria-valuemin="0" aria-valuemax="100" aria-valuenow="${s.level}">
        <div data-level="${s.level}"></div>
      </div>`;
    skillsGrid.appendChild(card);
  });

  const projectsGrid = document.getElementById('projects-grid');
  PROJECTS.forEach(p => {
    const card = el('article', 'card reveal');
    const link = p.link
      ? `<a class="card-link" href="${esc(p.link)}">열어보기 →</a>`
      : `<span class="card-link disabled">로컬 실행 프로젝트</span>`;
    card.innerHTML = `
      <h3>${esc(p.title)}</h3>
      <p>${esc(p.desc)}</p>
      <ul class="tags">${p.tech.map(t => `<li>${esc(t)}</li>`).join('')}</ul>
      ${link}`;
    projectsGrid.appendChild(card);
  });

  // ---------- 스크롤 등장 애니메이션 ----------
  const reveals = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries, obs) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('visible');
        entry.target.querySelectorAll('.meter > div').forEach(bar => {
          bar.style.width = bar.dataset.level + '%';
        });
        obs.unobserve(entry.target);
      });
    }, { threshold: 0.15 });
    reveals.forEach(r => io.observe(r));
  } else {
    reveals.forEach(r => r.classList.add('visible'));
    document.querySelectorAll('.meter > div').forEach(bar => {
      bar.style.width = bar.dataset.level + '%';
    });
  }

  // ---------- 테마 전환 ----------
  const root = document.documentElement;
  const themeBtn = document.getElementById('theme-toggle');
  const themeIcon = document.getElementById('theme-icon');

  function applyTheme(theme) {
    root.dataset.theme = theme;
    themeIcon.textContent = theme === 'dark' ? '☀' : '☾';
    themeBtn.setAttribute('aria-label', theme === 'dark' ? '라이트 테마로 전환' : '다크 테마로 전환');
    try { localStorage.setItem('theme', theme); } catch (e) {}
  }
  applyTheme(root.dataset.theme === 'light' ? 'light' : 'dark');
  themeBtn.addEventListener('click', () => {
    applyTheme(root.dataset.theme === 'dark' ? 'light' : 'dark');
  });

  // ---------- 모바일 메뉴 ----------
  const nav = document.getElementById('nav');
  const menuBtn = document.getElementById('menu-toggle');
  function setMenu(open) {
    nav.classList.toggle('open', open);
    menuBtn.setAttribute('aria-expanded', String(open));
    menuBtn.setAttribute('aria-label', open ? '메뉴 닫기' : '메뉴 열기');
  }
  menuBtn.addEventListener('click', () => setMenu(!nav.classList.contains('open')));
  nav.addEventListener('click', e => { if (e.target.closest('a')) setMenu(false); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') setMenu(false); });

  // ---------- 현재 섹션 표시 ----------
  const links = [...document.querySelectorAll('.nav-list a')];
  const sections = links.map(a => document.querySelector(a.getAttribute('href')));
  if ('IntersectionObserver' in window) {
    const spy = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        links.forEach(a => a.classList.toggle('active', a.getAttribute('href') === '#' + entry.target.id));
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    sections.forEach(s => s && spy.observe(s));
  }

  // ---------- 이메일 복사 ----------
  const copyBtn = document.getElementById('copy-email');
  const status = document.getElementById('copy-status');
  copyBtn.addEventListener('click', async () => {
    let ok = false;
    try {
      await navigator.clipboard.writeText(EMAIL);
      ok = true;
    } catch (e) {
      // file:// 등 클립보드 API를 쓸 수 없는 환경을 위한 대체 방법
      const ta = document.createElement('textarea');
      ta.value = EMAIL;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      try { ok = document.execCommand('copy'); } catch (err) {}
      ta.remove();
    }
    status.textContent = ok ? '이메일 주소를 복사했습니다.' : '복사에 실패했습니다. 직접 선택해 복사해 주세요.';
    setTimeout(() => { status.textContent = ''; }, 2500);
  });

  // ---------- 푸터 연도 ----------
  document.getElementById('year').textContent = new Date().getFullYear();
})();
