// Force-unregister any old service workers from the cache-first era
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then(function(regs) {
    regs.forEach(function(r) { r.unregister(); });
  });
}

// ===== Privacy-Safe Analytics =====
function trackEvent(name, data = {}) {
  try {
    if (window.umami && typeof window.umami.track === 'function') {
      const rawPage = location.pathname === '/' ? 'index' : location.pathname.replace(/^\/|\/$/g, '');
      window.umami.track(name, {
        page: rawPage.replace(/\.html$/, '') || 'index',
        ...data,
      });
    }
  } catch (_) {
    // Analytics must never interrupt the visitor experience.
  }
}

function lengthBucket(length) {
  if (length <= 3) return '2-3';
  if (length <= 7) return '4-7';
  if (length <= 15) return '8-15';
  return '16+';
}

function latencyBucket(ms) {
  if (ms < 1000) return '<1s';
  if (ms < 3000) return '1-3s';
  if (ms < 7000) return '3-7s';
  return '7s+';
}

// ===== Theme Toggle =====
const themeToggle = document.getElementById('theme-toggle');
const themeActionButtons = document.querySelectorAll('[data-theme-action]');
const body = document.body;

function syncThemeUI() {
  const isDark = body.classList.contains('dark-mode');
  const actionLabel = isDark ? 'Light mode' : 'Dark mode';
  const actionIcon = isDark ? 'fa-sun' : 'fa-moon';

  if (themeToggle) {
    themeToggle.innerHTML = `<i class="fas ${actionIcon}"></i>`;
    themeToggle.setAttribute('aria-label', `Switch to ${actionLabel.toLowerCase()}`);
    themeToggle.title = `Switch to ${actionLabel.toLowerCase()}`;
  }

  themeActionButtons.forEach((button) => {
    button.innerHTML = button.classList.contains('appbar-theme-toggle')
      ? `<i class="fas ${actionIcon}"></i>`
      : `<i class="fas ${actionIcon}"></i> ${actionLabel}`;
    button.setAttribute('aria-label', `Switch to ${actionLabel.toLowerCase()}`);
    button.title = `Switch to ${actionLabel.toLowerCase()}`;
  });
}

function setTheme(theme, source = 'unknown', shouldTrack = true) {
  const nextTheme = theme === 'dark' ? 'dark' : 'light';
  body.classList.toggle('dark-mode', nextTheme === 'dark');
  body.classList.toggle('light-mode', nextTheme === 'light');
  localStorage.setItem('theme', nextTheme);
  syncThemeUI();
  if (shouldTrack) trackEvent('theme_change', { theme: nextTheme, source });
}

setTheme(localStorage.getItem('theme') || 'light', 'saved', false);

if (themeToggle) {
  themeToggle.addEventListener('click', () => {
    setTheme(body.classList.contains('dark-mode') ? 'light' : 'dark', 'desktop');
  });
}

themeActionButtons.forEach((button) => {
  button.addEventListener('click', () => {
    const menuToggle = document.getElementById('appmenu-toggle');
    if (menuToggle) menuToggle.checked = false;
    setTheme(body.classList.contains('dark-mode') ? 'light' : 'dark', 'mobile');
  });
});

// ===== Mobile Menu Toggle =====
const mobileMenuBtn = document.getElementById('mobile-menu-btn');
const mainNav = document.getElementById('main-nav');

if (mobileMenuBtn && mainNav) {
  mobileMenuBtn.addEventListener('click', () => {
    mainNav.classList.toggle('active');
    const icon = mobileMenuBtn.querySelector('i');
    if (mainNav.classList.contains('active')) {
      icon.classList.remove('fa-bars');
      icon.classList.add('fa-times');
    } else {
      icon.classList.remove('fa-times');
      icon.classList.add('fa-bars');
    }
  });
}

// ===== Scroll Progress Bar =====
const scrollProgress = document.getElementById('scroll-progress');
const backToTop = document.getElementById('back-to-top');
let scrollUpdatePending = false;
let backToTopVisible = false;
let cachedChatFab = null;

function updateScrollUI() {
  const scrollTop = document.documentElement.scrollTop || document.body.scrollTop;
  const scrollHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;

  if (scrollProgress) {
    const progress = scrollHeight > 0 ? Math.min(1, Math.max(0, scrollTop / scrollHeight)) : 0;
    scrollProgress.style.transform = `scaleX(${progress})`;
  }

  const shouldShowBackToTop = window.scrollY > 500;
  if (shouldShowBackToTop !== backToTopVisible) {
    backToTopVisible = shouldShowBackToTop;
    if (backToTop) backToTop.classList.toggle('visible', shouldShowBackToTop);
    cachedChatFab = cachedChatFab || document.querySelector('.chat-fab');
    if (cachedChatFab) cachedChatFab.classList.toggle('shifted', shouldShowBackToTop);
  }

  scrollUpdatePending = false;
}

function requestScrollUIUpdate() {
  if (scrollUpdatePending) return;
  scrollUpdatePending = true;
  requestAnimationFrame(updateScrollUI);
}

window.addEventListener('scroll', requestScrollUIUpdate, { passive: true });
requestScrollUIUpdate();

if (backToTop) {
  backToTop.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
}

// ===== Search Functionality =====
const searchToggle = document.getElementById('search-toggle');
const searchContainer = document.getElementById('search-container');
const searchInput = document.getElementById('search-input');
const searchClose = document.getElementById('search-close');
const searchResults = document.getElementById('search-results');

if (searchToggle) {
  searchToggle.addEventListener('click', (event) => {
    searchContainer.classList.toggle('active');
    if (searchContainer.classList.contains('active')) {
      searchInput.focus();
      trackEvent('search_open', { source: event.isTrusted ? 'desktop' : 'mobile' });
    } else {
      trackEvent('search_close', { source: event.isTrusted ? 'desktop' : 'mobile' });
    }
  });
}

if (searchClose) {
  searchClose.addEventListener('click', () => {
    searchContainer.classList.remove('active');
    searchResults.classList.remove('active');
    searchInput.value = '';
    trackEvent('search_close', { source: 'close_button' });
  });
}

// Search data
const searchData = [
  { title: 'Natural Language Processing', type: 'Research Interest', section: 'interests' },
  { title: 'Large Language Models', type: 'Research Interest', section: 'interests' },
  { title: 'Vision-Language Models', type: 'Research Interest', section: 'interests' },
  { title: 'Information Extraction', type: 'Research Interest', section: 'interests' },
  { title: 'AI for Cybersecurity', type: 'Research Interest', section: 'interests' },
  { title: 'Python', type: 'Skill', section: 'skills' },
  { title: 'NLP', type: 'Skill', section: 'skills' },
  { title: 'LLM/VLM', type: 'Skill', section: 'skills' },
  { title: 'C++', type: 'Skill', section: 'skills' },
  { title: 'Research Fellow', type: 'Experience', section: 'experience' },
  { title: 'Queen\'s University Belfast', type: 'Experience', section: 'experience' },
  { title: 'University of Southampton', type: 'Experience', section: 'experience' },
  { title: 'PhD', type: 'Education', section: 'about' },
  { title: 'Publications', type: 'Navigation', href: '/papers' },
  { title: 'Activities', type: 'Navigation', href: '/activities' },
  { title: 'Education', type: 'Navigation', href: '/education' },
  { title: 'Research Impact Dashboard', type: 'Navigation', href: '/analytics' },
];

let searchTrackTimer;
if (searchInput) {
  searchInput.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase();
    
    if (query.length < 2) {
      searchResults.classList.remove('active');
      return;
    }
    
    const results = searchData.filter(item => 
      item.title.toLowerCase().includes(query) ||
      item.type.toLowerCase().includes(query)
    );
    
    if (results.length > 0) {
      searchResults.innerHTML = results.map(item => `
        <div class="search-result-item" onclick="navigateTo('${item.section || item.href}')">
          <h4>${item.title}</h4>
          <p>${item.type}</p>
        </div>
      `).join('');
      searchResults.classList.add('active');
    } else {
      searchResults.innerHTML = '<div class="search-result-item"><p>No results found</p></div>';
      searchResults.classList.add('active');
    }

    clearTimeout(searchTrackTimer);
    searchTrackTimer = setTimeout(() => {
      trackEvent('search_results', {
        length_bucket: lengthBucket(query.length),
        result_count: results.length,
      });
    }, 350);
  });
}

function navigateTo(target) {
  const selectedItem = searchData.find(item => (item.section || item.href) === target);
  trackEvent('search_result_select', {
    destination_type: selectedItem ? selectedItem.type : 'unknown',
    destination_kind: target.startsWith('/') || target.endsWith('.html') ? 'page' : 'section',
  });
  if (target.startsWith('http') || target.startsWith('/') || target.endsWith('.html')) {
    window.location.href = target;
  } else {
    const element = document.getElementById(target);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
      searchContainer.classList.remove('active');
      searchResults.classList.remove('active');
    }
  }
}

// ===== Copy Email Button =====
const copyEmailBtn = document.getElementById('copy-email-btn');
const emailText = document.getElementById('email-text');
const copyToast = document.getElementById('copy-toast');

if (copyEmailBtn && emailText) {
  copyEmailBtn.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(emailText.textContent);
      copyToast.classList.add('show');
      setTimeout(() => {
        copyToast.classList.remove('show');
      }, 2000);
    } catch (err) {
      console.error('Failed to copy email');
    }
  });
}

// ===== CV Download Counter =====
const cvDownload = document.getElementById('cv-download');
const downloadCount = document.getElementById('download-count');

// Simple counter using localStorage (for demo - use backend for production)
let downloads = localStorage.getItem('cvDownloads') || 0;

if (cvDownload) {
  cvDownload.addEventListener('click', () => {
    downloads++;
    localStorage.setItem('cvDownloads', downloads);
    updateDownloadCount();
  });
  
  function updateDownloadCount() {
    if (downloadCount) {
      downloadCount.classList.remove('skeleton');
      downloadCount.textContent = `(${downloads} downloads)`;
    }
  }
  
  updateDownloadCount();
}

// ===== Academic Journey Map =====
const journeyData = [
  {
    location: 'Belfast',
    country: 'UK 🇬🇧',
    role: 'Research Fellow (AI)',
    period: 'May 2024 – Present',
    description: 'Focusing on AI for corporate document understanding with LLMs and VLMs.',
    icon: 'fa-briefcase'
  },
  {
    location: 'Belfast',
    country: 'UK 🇬🇧',
    role: 'PhD, Computer Science',
    period: 'Oct 2019 – Dec 2024',
    description: 'Thesis on evidence-based verification of online health-related content.',
    icon: 'fa-graduation-cap'
  },
  {
    location: 'Southampton',
    country: 'UK 🇬🇧',
    role: 'Senior Research Assistant (AI-Security)',
    period: 'Jul 2023 – Jan 2024',
    description: 'Led team creating NER dataset for cyber-attack attribution.',
    icon: 'fa-shield-alt'
  },
  {
    location: 'Tezpur',
    country: 'India 🇮🇳',
    role: 'MTech, Information Technology',
    period: 'Jun 2014 – Jul 2016',
    description: 'Probabilistic modeling of language competition and extinction.',
    icon: 'fa-graduation-cap'
  },
  {
    location: 'Guwahati',
    country: 'India 🇮🇳',
    role: 'BE, Computer Science',
    period: 'Jun 2009 – Jul 2013',
    description: 'Developed Android notepad application with reminder features.',
    icon: 'fa-graduation-cap'
  },
  {
    location: 'Assam',
    country: 'India 🇮🇳',
    role: 'Lecturer',
    period: 'Aug 2018 – Sep 2019',
    description: 'Taught Python, C++, Data Structures, and Algorithms.',
    icon: 'fa-chalkboard-teacher'
  }
];

const mapContainer = document.getElementById('map-container');

if (mapContainer) {
  mapContainer.innerHTML = journeyData.map(item => `
    <div class="journey-item">
      <div class="journey-pin">
        <i class="fas ${item.icon}"></i>
      </div>
      <div class="journey-card">
        <div class="journey-location">
          <span class="location-name">${item.location}</span>
          <span class="location-country">${item.country}</span>
        </div>
        <div class="journey-role">${item.role}</div>
        <span class="journey-period">${item.period}</span>
        <p class="journey-description">${item.description}</p>
      </div>
    </div>
  `).join('');
}

// ===== View Counter =====
const viewCountEl = document.getElementById('view-count');

async function updateViewCounter() {
 if (!viewCountEl) return;
 
 try {
   const response = await fetchWithTimeout('https://api.countapi.xyz/hit/pritamdeka-homepage/visits', 4500);
   const data = await response.json();
   viewCountEl.classList.remove('skeleton');
   whenVisible(viewCountEl, () => animateCounter(viewCountEl, data.value));
 } catch (error) {
   // countapi.xyz is frequently down — show a graceful fallback instead of a fake number
   viewCountEl.classList.remove('skeleton');
   viewCountEl.textContent = '—';
   viewCountEl.title = 'View counter unavailable';
 }
}

updateViewCounter();

// ===== Auto-update Year and Timestamp =====
const currentYearEl = document.getElementById('current-year');
if (currentYearEl) {
  currentYearEl.textContent = new Date().getFullYear();
}

const lastUpdatedEl = document.getElementById('last-updated');
if (lastUpdatedEl) {
  const now = new Date();
  const options = { year: 'numeric', month: 'short', day: 'numeric' };
  lastUpdatedEl.textContent = now.toLocaleDateString('en-GB', options);
}

// ===== Hero Typewriter Rotator =====
const heroTy = document.getElementById('hero-ty');
if (heroTy) {
  const roles = [
    'AI Engineer',
    'LLMs & Agentic AI',
    'Multimodal & Vision-Language AI',
    'Document Intelligence',
    'AI Research Fellow, QUB'
  ];
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduceMotion) {
    heroTy.textContent = roles[0];
  } else {
    let r = 0, c = 0, deleting = false;
    (function tick() {
      const word = roles[r];
      if (deleting) {
        heroTy.textContent = word.slice(0, --c);
      } else {
        heroTy.textContent = word.slice(0, ++c);
      }
      let delay = deleting ? 45 : 90;
      if (!deleting && c === word.length) {
        delay = 1800;
        deleting = true;
      } else if (deleting && c === 0) {
        deleting = false;
        r = (r + 1) % roles.length;
        delay = 350;
      }
      setTimeout(tick, delay);
    })();
  }
}

// ===== Animated Count-Up =====
function animateCounter(el, target, duration = 1200) {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduceMotion) {
    el.textContent = target.toLocaleString();
    return;
  }
  const start = performance.now();
  function frame(now) {
    const p = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - p, 3);
    el.textContent = Math.round(target * eased).toLocaleString();
    if (p < 1) requestAnimationFrame(frame);
    else el.textContent = target.toLocaleString();
  }
  requestAnimationFrame(frame);
}

function whenVisible(el, cb) {
  if (!el) return;
  if (el.getBoundingClientRect().top < window.innerHeight && el.getBoundingClientRect().bottom > 0) {
    cb();
    return;
  }
  const obs = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) { obs.disconnect(); cb(); }
  }, { threshold: 0.3 });
  obs.observe(el);
}

// ===== Dynamic Stats Fetcher =====
async function fetchDynamicStats() {
  const paperCountEl = document.getElementById('paper-count');
  const citationCountEl = document.getElementById('citation-count');
  const phCitationsEl = document.getElementById('ph-citations');
  
  try {
    const response = await fetch('citations.json');
    const data = await response.json();
    
    if (paperCountEl) {
      paperCountEl.textContent = data.papers + '+';
    }
    
    if (citationCountEl) {
      citationCountEl.classList.remove('skeleton');
      whenVisible(citationCountEl, () => animateCounter(citationCountEl, data.citations));
      citationCountEl.title = `Updated: ${new Date(data.updated).toLocaleDateString()}`;
    }

    if (phCitationsEl) {
      whenVisible(phCitationsEl, () => animateCounter(phCitationsEl, data.citations));
    }
  } catch (error) {
    console.error('Stats fetch error:', error);
    if (paperCountEl) paperCountEl.textContent = '10+';
    if (citationCountEl) {
      citationCountEl.classList.remove('skeleton');
      citationCountEl.textContent = '174';
    }
  }
}

// ===== Citation Growth Sparkline =====
async function renderCitationSparkline() {
  const spark = document.getElementById('citation-spark');
  const svg = document.getElementById('spark-svg');
  if (!spark || !svg) return;
  try {
    const res = await fetch('citations-history.json');
    const history = await res.json();
    if (!Array.isArray(history) || history.length < 2) return;
    const pts = history.map(h => h.citations);
    const min = Math.min(...pts), max = Math.max(...pts);
    const range = (max - min) || 1;
    const W = 120, H = 32, pad = 3;
    const x = (i) => pad + (i / (pts.length - 1)) * (W - 2 * pad);
    const y = (v) => H - pad - ((v - min) / range) * (H - 2 * pad);
    const line = pts.map((v, i) => `${i === 0 ? 'M' : 'L'} ${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(' ');
    const area = `${line} L ${x(pts.length - 1).toFixed(1)} ${H} L ${x(0).toFixed(1)} ${H} Z`;
    svg.innerHTML = `
      <defs><linearGradient id="spark-grad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="var(--accent)"/>
        <stop offset="1" stop-color="var(--accent)" stop-opacity="0"/>
      </linearGradient></defs>
      <path class="spark-area" d="${area}"/>
      <path class="spark-line" d="${line}"/>
    `;
    spark.hidden = false;
  } catch (e) {
    // No history yet — silently hide the widget
  }
}
renderCitationSparkline();

// ===== HuggingFace Stats =====
async function fetchHuggingFaceStats() {
  const hfDownloadsEl = document.getElementById('hf-downloads');
  const hfModelsEl = document.getElementById('hf-models');
  const osModelsEl = document.getElementById('os-models');
  
  if (!hfDownloadsEl && !hfModelsEl && !osModelsEl) return;
  
  try {
    const hfUsername = 'pritamdeka';
    const response = await fetchWithTimeout(`https://huggingface.co/api/models?author=${hfUsername}`, 5000);
    const models = await response.json();
    
    const totalDownloads = models.reduce((sum, model) => {
      return sum + (model.downloads || 0);
    }, 0);
    
    const totalModels = models.length;
    
    if (hfDownloadsEl) {
      hfDownloadsEl.classList.remove('skeleton');
      whenVisible(hfDownloadsEl, () => animateCounter(hfDownloadsEl, totalDownloads));
    }
    
    if (hfModelsEl) {
      hfModelsEl.classList.remove('skeleton');
      whenVisible(hfModelsEl, () => animateCounter(hfModelsEl, totalModels));
    }

    if (osModelsEl) {
      whenVisible(osModelsEl, () => animateCounter(osModelsEl, totalModels));
    }
  } catch (error) {
    if (hfDownloadsEl) {
      hfDownloadsEl.classList.remove('skeleton');
      hfDownloadsEl.textContent = '—';
      hfDownloadsEl.title = 'HuggingFace API unavailable';
    }
    if (hfModelsEl) {
      hfModelsEl.classList.remove('skeleton');
      hfModelsEl.textContent = '—';
      hfModelsEl.title = 'HuggingFace API unavailable';
    }
    if (osModelsEl) { osModelsEl.textContent = '50+'; }
    console.log('HuggingFace API unavailable');
  }
}

function formatNumber(num) {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k';
  }
  return num.toString();
}

// Run both functions
fetchDynamicStats();
fetchHuggingFaceStats();

// ===== Typing Animation =====
// Animation runs automatically via CSS, no JS needed for basic effect
// Just ensure the element has text content in HTML

// ===== Contact Form Handler =====
const contactForm = document.getElementById('contact-form');
const formStatus = document.getElementById('form-status');

if (contactForm) {
  contactForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(contactForm);
    
    try {
      const response = await fetch(contactForm.action, {
        method: 'POST',
        body: formData,
        headers: { 'Accept': 'application/json' }
      });
      
      if (response.ok) {
        formStatus.textContent = '✅ Message sent successfully!';
        formStatus.className = 'success';
        contactForm.reset();
        trackEvent('contact_form_submit', { outcome: 'success' });
      } else {
        formStatus.textContent = '❌ Something went wrong. Please email me directly.';
        formStatus.className = 'error';
        trackEvent('contact_form_submit', { outcome: 'service_error' });
      }
    } catch (error) {
      formStatus.textContent = '❌ Network error. Please email me directly.';
      formStatus.className = 'error';
      trackEvent('contact_form_submit', { outcome: 'network_error' });
    }
    
    setTimeout(() => { formStatus.style.display = 'none'; }, 5000);
  });
}

// ===== Smooth Scroll =====
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function(e) {
    const href = this.getAttribute('href');
    if (href !== '#' && document.querySelector(href)) {
      e.preventDefault();
      document.querySelector(href).scrollIntoView({ behavior: 'smooth' });
      if (mainNav && mainNav.classList.contains('active')) {
        mainNav.classList.remove('active');
      }
    }
  });
});

// ===== Intersection Observer for Animations =====
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.style.opacity = '1';
      entry.target.style.transform = 'translateY(0)';
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll('.fade-in').forEach(section => {
  observer.observe(section);
});

// ===== Spotlight Hover (cards) =====
document.querySelectorAll('.spotlight').forEach(card => {
  card.addEventListener('mousemove', (e) => {
    const r = card.getBoundingClientRect();
    card.style.setProperty('--mx', ((e.clientX - r.left) / r.width) * 100 + '%');
    card.style.setProperty('--my', ((e.clientY - r.top) / r.height) * 100 + '%');
  });
});

// ===== Experience Filters =====
const expFilters = document.getElementById('exp-filters');
if (expFilters) {
  expFilters.addEventListener('click', (e) => {
    const btn = e.target.closest('.filter-btn');
    if (!btn) return;
    expFilters.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const cat = btn.dataset.cat;
    document.querySelectorAll('#experience .timeline-item').forEach(item => {
      if (cat === 'all' || item.dataset.cat === cat) {
        item.style.display = '';
        item.style.opacity = '1';
      } else {
        item.style.display = 'none';
        item.style.opacity = '0';
      }
    });
  });
}

// ===== Scroll-Spy Nav (index only) =====
(function setupScrollSpy() {
  const isIndex = /index\.html$|\/$/.test(location.pathname);
  if (!isIndex) return;
  const navLinks = document.querySelectorAll('#main-nav a[href^="#"]');
  if (!navLinks.length) return;
  const sections = [];
  navLinks.forEach(a => {
    const id = a.getAttribute('href').slice(1);
    const sec = document.getElementById(id);
    if (sec) sections.push({ link: a, el: sec });
  });
  if (!sections.length) return;
  const spy = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        sections.forEach(s => s.link.classList.remove('spy-active'));
        const match = sections.find(s => s.el === entry.target);
        if (match) match.link.classList.add('spy-active');
      }
    });
  }, { rootMargin: '-45% 0px -50% 0px' });
  sections.forEach(s => spy.observe(s.el));
})();

// ===== Console Easter Egg =====
console.log('%c👋 Hello, fellow developer!', 'font-size: 20px; color: #667eea; font-weight: bold;');
console.log('%cCheck out my GitHub: https://github.com/pritamdeka', 'font-size: 12px; color: #888;');

// ===== Research Topic Network =====
const networkContainer = document.getElementById('research-network');

if (networkContainer) {
 // Define nodes (topics and papers)
 const nodes = [
  // Core Research Areas (Blue)
  { id: 1, label: 'NLP', group: 'core', value: 25 },
  { id: 2, label: 'LLMs', group: 'core', value: 20 },
  { id: 3, label: 'VLMs', group: 'core', value: 18 },
  { id: 4, label: 'Information Extraction', group: 'core', value: 22 },
  
  // Applications (Green)
  { id: 5, label: 'Fact Checking', group: 'application', value: 15 },
  { id: 6, label: 'Healthcare AI', group: 'application', value: 18 },
  { id: 7, label: 'Process Mining', group: 'application', value: 12 },
  { id: 8, label: 'Document Understanding', group: 'application', value: 16 },
  
  // Methods (Orange)
  { id: 9, label: 'BERT', group: 'method', value: 14 },
  { id: 10, label: 'Transformers', group: 'method', value: 16 },
  { id: 11, label: 'Prompt Engineering', group: 'method', value: 13 },
  { id: 12, label: 'Fine-tuning', group: 'method', value: 12 },
  
   // Domains (Purple)
   { id: 13, label: 'Cybersecurity', group: 'domain', value: 10 },
   { id: 14, label: 'Business Process', group: 'domain', value: 11 },
   { id: 15, label: 'Social Media', group: 'domain', value: 9 },
   { id: 16, label: 'Scientific Literature', group: 'domain', value: 8 },
   
   // Collaborators (Pink)
   { id: 20, label: 'Anna Jurek-Loughrey\n(QUB)', group: 'collab', value: 16 },
   { id: 21, label: 'Barry Devereux\n(QUB)', group: 'collab', value: 13 },
   { id: 22, label: 'Deepak P\n(QUB/IIT-M)', group: 'collab', value: 11 },
   { id: 23, label: 'Erisa Karafili\n(Southampton)', group: 'collab', value: 11 },
   { id: 24, label: 'Nayan J. Kalita', group: 'collab', value: 8 },
   { id: 25, label: 'Ashwathy T Revi\n(Southampton)', group: 'collab', value: 8 },
  ];
 
 // Define edges (connections)
 const edges = [
  // NLP connects to everything
  { from: 1, to: 2 },
  { from: 1, to: 3 },
  { from: 1, to: 4 },
  { from: 1, to: 5 },
  { from: 1, to: 6 },
  
  // LLMs/VLMs to applications
  { from: 2, to: 5 },
  { from: 2, to: 6 },
  { from: 2, to: 7 },
  { from: 2, to: 8 },
  { from: 3, to: 7 },
  { from: 3, to: 8 },
  
  // Information Extraction to applications
  { from: 4, to: 5 },
  { from: 4, to: 6 },
  { from: 4, to: 8 },
  { from: 4, to: 13 },
  
  // Methods to core research
  { from: 9, to: 1 },
  { from: 9, to: 5 },
  { from: 9, to: 6 },
  { from: 10, to: 2 },
  { from: 10, to: 3 },
  { from: 11, to: 2 },
  { from: 11, to: 8 },
  { from: 12, to: 2 },
  { from: 12, to: 3 },
  
   // Domains to applications
   { from: 13, to: 4 },
   { from: 13, to: 9 },
   { from: 14, to: 7 },
   { from: 14, to: 8 },
   { from: 15, to: 5 },
   { from: 15, to: 1 },
   { from: 16, to: 6 },
   
   // Collaborators to their research areas
   { from: 20, to: 1, dashes: true },
   { from: 20, to: 5, dashes: true },
   { from: 20, to: 6, dashes: true },
   { from: 21, to: 3, dashes: true },
   { from: 21, to: 7, dashes: true },
   { from: 21, to: 8, dashes: true },
   { from: 22, to: 5, dashes: true },
   { from: 22, to: 6, dashes: true },
   { from: 23, to: 13, dashes: true },
   { from: 23, to: 4, dashes: true },
   { from: 24, to: 15, dashes: true },
   { from: 24, to: 1, dashes: true },
   { from: 25, to: 5, dashes: true },
  ];
 
 // Create data arrays
 const data = {
  nodes: new vis.DataSet(nodes),
  edges: new vis.DataSet(edges)
 };
 
  // Options for styling
  const options = {
   nodes: {
    shape: 'dot',
    font: {
     size: 14,
     color: '#1a1d3a',
     face: 'Inter, Segoe UI, sans-serif',
     multi: 'html'
    },
    borderWidth: 2,
    shadow: true
   },
   edges: {
    width: 1.5,
    color: { color: '#e6e8f5', highlight: '#5b6ef5' },
    smooth: { type: 'continuous' }
   },
   groups: {
    core: {
     color: { background: '#5b6ef5', border: '#4456e8' },
     label: { bold: true }
    },
    application: {
     color: { background: '#10b981', border: '#059669' }
    },
    method: {
     color: { background: '#f59e0b', border: '#d97706' }
    },
    domain: {
     color: { background: '#8b5cf6', border: '#7c3aed' }
    },
    collab: {
     color: { background: '#ec4899', border: '#db2777' },
     shape: 'star',
     size: 18
    }
   },
   physics: {
    enabled: true,
    barnesHut: {
     gravitationalConstant: -3500,
     centralGravity: 0.25,
     springLength: 110,
     springConstant: 0.04,
     damping: 0.12
    },
    stabilization: { iterations: 200 }
   },
   interaction: {
   hover: true,
   tooltipDelay: 200,
   zoomView: true,
   dragNodes: true
  }
 };
 
 // Initialize network
 const network = new vis.Network(networkContainer, data, options);
 
  // Add click event to show paper links
  network.on('click', function(params) {
   if (params.nodes.length > 0) {
    const nodeId = params.nodes[0];
    const node = nodes.find(n => n.id === nodeId);
    console.log('Clicked:', node.label);
    // Could open papers filtered by topic here
   }
  });
}

// ===== Command Palette (Ctrl/Cmd+K) =====
(function setupCommandPalette() {
  const palette = document.createElement('div');
  palette.className = 'cmd-palette';
  palette.id = 'cmd-palette';
  palette.innerHTML = `
    <div class="cmd-box" role="dialog" aria-label="Command palette">
      <div class="cmd-input-wrap">
        <i class="fas fa-search"></i>
        <input type="text" class="cmd-input" id="cmd-input" placeholder="Type a command or search…" autocomplete="off" spellcheck="false">
        <span class="cmd-kbd">esc</span>
      </div>
      <div class="cmd-results" id="cmd-results"></div>
      <div class="cmd-footer">
        <span><kbd>↑</kbd><kbd>↓</kbd> navigate · <kbd>↵</kbd> select</span>
        <span>Press <kbd>Ctrl</kbd>+<kbd>K</kbd> anytime</span>
      </div>
    </div>`;
  document.body.appendChild(palette);

  const input = document.getElementById('cmd-input');
  const results = document.getElementById('cmd-results');
  let commands = [];
  let selected = 0;

  function isIndex() { return location.pathname === '/' || /\/index(?:\.html)?$/.test(location.pathname); }

  function buildCommands() {
    const isDark = body.classList.contains('dark-mode');
    const c = [
      { group: 'Navigate', icon: 'fa-user', label: 'Home / About', hint: '/', run: () => go('/') },
      { group: 'Navigate', icon: 'fa-graduation-cap', label: 'Education', hint: '/education', run: () => go('/education') },
      { group: 'Navigate', icon: 'fa-file-alt', label: 'Papers', hint: '/papers', run: () => go('/papers') },
      { group: 'Navigate', icon: 'fa-trophy', label: 'Activities', hint: '/activities', run: () => go('/activities') },
      { group: 'Navigate', icon: 'fa-rss', label: 'Blog', hint: '/blog', run: () => go('/blog') },
      { group: 'Navigate', icon: 'fa-chart-line', label: 'Research Impact', hint: '/analytics', run: () => go('/analytics') },
      {
        group: 'Navigate',
        icon: 'fa-download',
        label: 'Download CV',
        hint: 'PDF',
        run: () => {
          trackEvent('cv_download', { source: 'command_palette' });
          go('/cv/Pritam_Deka_CV.pdf');
        }
      },
      {
        group: 'Action',
        icon: isDark ? 'fa-sun' : 'fa-moon',
        label: isDark ? 'Switch to light mode' : 'Switch to dark mode',
        hint: 'theme',
        run: () => {
          setTheme(isDark ? 'light' : 'dark', 'command_palette');
          closePalette();
        }
      },
    ];
    if (isIndex()) {
      c.push(
        { group: 'Jump to', icon: 'fa-newspaper', label: 'News', run: () => scrollTo('#news') },
        { group: 'Jump to', icon: 'fa-project-diagram', label: 'Research Network', run: () => scrollTo('#research-network-section') },
        { group: 'Jump to', icon: 'fa-map-marked-alt', label: 'Academic Journey', run: () => scrollTo('#journey') },
        { group: 'Jump to', icon: 'fas fa-rocket', label: 'Projects & Demos', run: () => scrollTo('#projects') },
        { group: 'Jump to', icon: 'fa-tools', label: 'Skills', run: () => scrollTo('#skills') },
        { group: 'Jump to', icon: 'fa-briefcase', label: 'Experience', run: () => scrollTo('#experience') },
        { group: 'Jump to', icon: 'fa-paper-plane', label: 'Contact', run: () => scrollTo('#contact') },
      );
    }
    searchData.forEach(item => {
      if (item.href) {
        c.push({ group: 'Search', icon: 'fa-link', label: item.title, hint: item.type, run: () => go(item.href) });
      } else if (item.section) {
        c.push({ group: 'Search', icon: 'fa-search', label: item.title, hint: item.type, run: () => scrollTo('#' + item.section) });
      }
    });
    return c;
  }

  function go(url) { location.href = url; }
  function scrollTo(sel) {
    closePalette();
    const el = document.querySelector(sel);
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  }

  function render(list) {
    if (!list.length) {
      results.innerHTML = '<div class="cmd-item" style="cursor:default;color:var(--text-muted)">No matches</div>';
      return;
    }
    results.innerHTML = '';
    let lastGroup = '';
    list.forEach((cmd, i) => {
      if (cmd.group !== lastGroup) {
        const g = document.createElement('div');
        g.className = 'cmd-group';
        g.textContent = cmd.group;
        results.appendChild(g);
        lastGroup = cmd.group;
      }
      const item = document.createElement('div');
      item.className = 'cmd-item' + (i === selected ? ' selected' : '');
      item.innerHTML = `<i class="fas ${cmd.icon}"></i><span>${cmd.label}</span>${cmd.hint ? '<span class="cmd-hint">' + cmd.hint + '</span>' : ''}`;
      item.addEventListener('click', () => { runCommand(cmd); });
      results.appendChild(item);
    });
  }

  function runCommand(command) {
    trackEvent('command_action', {
      group: command.group.toLowerCase().replace(/\s+/g, '_'),
      action: command.label.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, ''),
    });
    command.run();
  }

  function filter(q) {
    if (!q) { selected = 0; return commands; }
    return commands.filter(c => (c.label + ' ' + (c.hint || '') + ' ' + c.group).toLowerCase().includes(q.toLowerCase()));
  }

  function openPalette() {
    commands = buildCommands();
    palette.classList.add('active');
    input.value = '';
    render(filter(''));
    setTimeout(() => input.focus(), 30);
    trackEvent('command_palette_open');
  }

  function closePalette() {
    palette.classList.remove('active');
  }

  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      palette.classList.contains('active') ? closePalette() : openPalette();
      return;
    }
    if (!palette.classList.contains('active')) return;
    if (e.key === 'Escape') { closePalette(); }
    else if (e.key === 'ArrowDown') {
      e.preventDefault();
      const f = filter(input.value);
      selected = (selected + 1) % f.length;
      render(f);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      const f = filter(input.value);
      selected = (selected - 1 + f.length) % f.length;
      render(f);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const f = filter(input.value);
      if (f[selected]) runCommand(f[selected]);
    }
  });

  input.addEventListener('input', () => { selected = 0; render(filter(input.value)); });
  palette.addEventListener('click', (e) => { if (e.target === palette) closePalette(); });
})();

// ===== Service Worker Registration =====
if ('serviceWorker' in navigator && location.protocol === 'https:') {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('sw.js').catch((err) => {
      console.warn('SW registration failed:', err);
    });
  });
}

// ===== Fetch with timeout helper =====
function fetchWithTimeout(url, ms, options) {
  return Promise.race([
    fetch(url, options),
    new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), ms))
  ]);
}

// (Mobile tab bar + drawer removed — replaced by app bar + overlay menu in HTML.)

// ===== Scroll Reveal Animations =====
(function setupScrollReveal() {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  // Add .reveal to .fade-in sections (upgrade from the old CSS-only animation)
  document.querySelectorAll('section.fade-in').forEach(s => {
    s.classList.remove('fade-in');
    s.classList.add('reveal');
  });
  if (reduceMotion) {
    document.querySelectorAll('.reveal, .reveal-left, .reveal-right, .reveal-scale').forEach(el => el.classList.add('revealed'));
    return;
  }
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('revealed');
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
  document.querySelectorAll('.reveal, .reveal-left, .reveal-right, .reveal-scale').forEach(el => obs.observe(el));
})();

// ===== Cursor-Following Gradient Orb =====
(function setupCursorOrb() {
  if (window.matchMedia('(max-width: 700px)').matches) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const orb = document.createElement('div');
  orb.className = 'cursor-orb';
  document.body.appendChild(orb);
  let tx = window.innerWidth / 2, ty = window.innerHeight / 2;
  let cx = tx, cy = ty;
  document.addEventListener('mousemove', (e) => { tx = e.clientX; ty = e.clientY; });
  function lerp() {
    cx += (tx - cx) * 0.08;
    cy += (ty - cy) * 0.08;
    orb.style.setProperty('--cx', cx + 'px');
    orb.style.setProperty('--cy', cy + 'px');
    requestAnimationFrame(lerp);
  }
  lerp();
})();

// ===== 3D Card Tilt on Hover =====
(function setupTilt() {
  if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  document.querySelectorAll('.project-card, .paper-item, .activity-card, .degree-card').forEach(card => {
    card.classList.add('tilt');
    card.addEventListener('mousemove', (e) => {
      const r = card.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width - 0.5;
      const py = (e.clientY - r.top) / r.height - 0.5;
      card.style.transform = `perspective(800px) rotateY(${px * 8}deg) rotateX(${-py * 8}deg) scale(1.02)`;
    });
    card.addEventListener('mouseleave', () => {
      card.style.transform = '';
    });
  });
})();

// ===== Page Transitions =====
(function setupPageTransitions() {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduceMotion) return;
  document.addEventListener('click', (e) => {
    const link = e.target.closest('a');
    if (!link) return;
    const href = link.getAttribute('href');
    if (!href || href.startsWith('#') || href.startsWith('http') || href.startsWith('mailto:') || link.target === '_blank' || link.hasAttribute('download')) return;
    const currentPath = location.pathname.replace(/\/index(?:\.html)?$/, '/').replace(/\.html$/, '').replace(/\/$/, '') || '/';
    const targetPath = new URL(href, location.href).pathname.replace(/\/index(?:\.html)?$/, '/').replace(/\.html$/, '').replace(/\/$/, '') || '/';
    const samePage = targetPath === currentPath;
    if (samePage) return;
    if (typeof document.startViewTransition === 'function') {
      // Native View Transitions API (Chrome/Edge)
      // The browser handles the animation automatically
      return;
    }
    // JS fallback: fade out before navigation
    e.preventDefault();
    document.documentElement.classList.add('vt-leaving');
    setTimeout(() => { window.location.href = href; }, 200);
  });
})();

// ===== Chat Widget =====
(function setupChatWidget() {
  // CONFIG: Replace this with your Cloudflare Worker URL after deploying chat-worker.js
  const CHAT_WORKER_URL = 'https://pritam-chat.pritam26491.workers.dev/'; // e.g., 'https://pritam-chat.your-subdomain.workers.dev'

  const fab = document.createElement('button');
  fab.className = 'chat-fab';
  fab.innerHTML = '<i class="fas fa-comments"></i>';
  fab.setAttribute('aria-label', 'Open chat');
  document.body.appendChild(fab);
  cachedChatFab = fab;
  fab.classList.toggle('shifted', window.scrollY > 500);

  const panel = document.createElement('div');
  panel.className = 'chat-panel';
  panel.innerHTML = `
    <div class="chat-header">
      <div class="chat-header-info">
        <i class="fas fa-robot"></i>
        <div>
          <h3>Ask AI about Pritam</h3>
          <span>Powered by Gemini</span>
        </div>
      </div>
      <button class="chat-close" aria-label="Close chat"><i class="fas fa-times"></i></button>
    </div>
    <div class="chat-messages" id="chat-messages">
      <div class="chat-msg bot">Hi! I'm an AI assistant that can answer questions about Dr. Pritam Deka's research, publications, experience and projects. How can I help?</div>
    </div>
    <div class="chat-quick-replies" id="chat-quick">
      <button class="chat-quick" data-q="What is your research area?">Research areas</button>
      <button class="chat-quick" data-q="Show me your papers">Show papers</button>
      <button class="chat-quick" data-q="Tell me about Khyontek AI">Khyontek AI</button>
      <button class="chat-quick" data-q="What models have you published on HuggingFace?">HuggingFace models</button>
    </div>
    <div class="chat-input-bar">
      <input type="text" class="chat-input" id="chat-input" placeholder="Type your question..." autocomplete="off">
      <button class="chat-send" id="chat-send"><i class="fas fa-paper-plane"></i></button>
    </div>`;
  document.body.appendChild(panel);

  const messages = document.getElementById('chat-messages');
  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send');
  const closeBtn = panel.querySelector('.chat-close');
  let history = [];

  function toggle(source = 'button') {
    panel.classList.toggle('active');
    fab.classList.toggle('hidden');
    const isOpen = panel.classList.contains('active');
    if (isOpen) input.focus();
    trackEvent(isOpen ? 'chat_open' : 'chat_close', { source });
  }
  fab.addEventListener('click', () => toggle('floating_button'));
  closeBtn.addEventListener('click', () => toggle('close_button'));

  function addMsg(text, type) {
    const div = document.createElement('div');
    div.className = 'chat-msg ' + type;
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
  }

  function addTyping() {
    const div = document.createElement('div');
    div.className = 'chat-typing';
    div.id = 'chat-typing-indicator';
    div.innerHTML = '<span></span><span></span><span></span>';
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }
  function removeTyping() {
    const t = document.getElementById('chat-typing-indicator');
    if (t) t.remove();
  }

  async function send(msg, source = 'typed') {
    if (!msg.trim()) return;
    addMsg(msg, 'user');
    input.value = '';
    history.push({ role: 'user', text: msg });
    trackEvent('chat_question', {
      source,
      length_bucket: lengthBucket(msg.trim().length),
    });

    if (!CHAT_WORKER_URL) {
      addMsg("I'm not connected to the AI service yet. Please email contact@pritamdeka.com or check back after the chat proxy is deployed.", 'error');
      trackEvent('chat_response', { outcome: 'not_configured', latency_bucket: '<1s' });
      return;
    }

    addTyping();
    const startedAt = Date.now();
    try {
      const res = await fetchWithTimeout(
        CHAT_WORKER_URL,
        15000,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: msg, history: history.slice(-4) }),
        }
      );
      const data = await res.json();
      removeTyping();
      if (data.reply) {
        addMsg(data.reply, 'bot');
        history.push({ role: 'bot', text: data.reply });
        trackEvent('chat_response', {
          outcome: 'success',
          latency_bucket: latencyBucket(Date.now() - startedAt),
        });
      } else if (data.error) {
        addMsg(data.error, 'error');
        trackEvent('chat_response', {
          outcome: 'service_error',
          latency_bucket: latencyBucket(Date.now() - startedAt),
        });
      } else {
        addMsg("Sorry, I couldn't generate a response. Please try again.", 'error');
        trackEvent('chat_response', {
          outcome: 'empty_response',
          latency_bucket: latencyBucket(Date.now() - startedAt),
        });
      }
    } catch (err) {
      removeTyping();
      addMsg("Connection error. Please email contact@pritamdeka.com directly.", 'error');
      trackEvent('chat_response', {
        outcome: 'network_error',
        latency_bucket: latencyBucket(Date.now() - startedAt),
      });
    }
  }

  sendBtn.addEventListener('click', () => send(input.value, 'typed'));
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter') send(input.value, 'typed'); });
  document.querySelectorAll('.chat-quick').forEach(btn => {
    btn.addEventListener('click', () => {
      trackEvent('chat_quick_reply', {
        category: btn.textContent.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_'),
      });
      send(btn.dataset.q, 'quick_reply');
    });
  });
})();

// ===== Conversion and Content-Link Analytics =====
document.addEventListener('click', (event) => {
  const link = event.target.closest('a[href]');
  if (!link) return;

  const href = link.getAttribute('href') || '';
  const heading = link.querySelector('h3, h4') || link.closest('.project-card, .paper-item')?.querySelector('h3, h4, .paper-title');
  const labelText = heading ? heading.textContent : link.textContent;
  const label = labelText.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');

  if (/Pritam_Deka_CV\.pdf/i.test(href)) {
    trackEvent('cv_download', { source: link.closest('.appmenu') ? 'mobile_menu' : 'page' });
    return;
  }

  if (link.matches('.paper-link')) {
    trackEvent('content_link_open', { content_type: 'publication', label });
    return;
  }

  if (link.matches('.project-link, .project-card, .featured-card')) {
    trackEvent('content_link_open', { content_type: 'project', label });
    return;
  }

  if (link.matches('.landing-btn, .hero-btn, .cta-button, .cv-download-btn') || href.startsWith('mailto:')) {
    trackEvent('primary_cta', {
      action: href.startsWith('mailto:') ? 'email' : label,
      destination: href.startsWith('http') ? 'external' : 'internal',
    });
  }
});
