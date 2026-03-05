// ===== Theme Toggle =====
const themeToggle = document.getElementById('theme-toggle');
const body = document.body;

const savedTheme = localStorage.getItem('theme') || 'light';
if (savedTheme === 'dark') {
  body.classList.remove('light-mode');
  body.classList.add('dark-mode');
  themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
}

themeToggle.addEventListener('click', () => {
  if (body.classList.contains('light-mode')) {
    body.classList.remove('light-mode');
    body.classList.add('dark-mode');
    themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
    localStorage.setItem('theme', 'dark');
  } else {
    body.classList.remove('dark-mode');
    body.classList.add('light-mode');
    themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
    localStorage.setItem('theme', 'light');
  }
});

// ===== Mobile Menu Toggle =====
const mobileMenuBtn = document.getElementById('mobile-menu-btn');
const mainNav = document.getElementById('main-nav');

if (mobileMenuBtn) {
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

window.addEventListener('scroll', () => {
  const scrollTop = document.documentElement.scrollTop || document.body.scrollTop;
  const scrollHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
  const scrollPercentage = (scrollTop / scrollHeight) * 100;
  scrollProgress.style.width = scrollPercentage + '%';
});

// ===== Back to Top Button =====
const backToTop = document.getElementById('back-to-top');

window.addEventListener('scroll', () => {
  if (window.scrollY > 500) {
    backToTop.classList.add('visible');
  } else {
    backToTop.classList.remove('visible');
  }
});

backToTop.addEventListener('click', () => {
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

// ===== Search Functionality =====
const searchToggle = document.getElementById('search-toggle');
const searchContainer = document.getElementById('search-container');
const searchInput = document.getElementById('search-input');
const searchClose = document.getElementById('search-close');
const searchResults = document.getElementById('search-results');

if (searchToggle) {
  searchToggle.addEventListener('click', () => {
    searchContainer.classList.toggle('active');
    searchInput.focus();
  });
}

if (searchClose) {
  searchClose.addEventListener('click', () => {
    searchContainer.classList.remove('active');
    searchResults.classList.remove('active');
    searchInput.value = '';
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
  { title: 'Publications', type: 'Navigation', href: 'papers.html' },
  { title: 'Activities', type: 'Navigation', href: 'activities.html' },
  { title: 'Education', type: 'Navigation', href: 'education.html' },
];

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
  });
}

function navigateTo(target) {
  if (target.startsWith('http') || target.endsWith('.html')) {
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
      <div class="journey-location">
        <i class="fas ${item.icon} location-icon"></i>
        <div class="location-name">${item.location}</div>
        <div class="location-country">${item.country}</div>
      </div>
      <div class="journey-details">
        <div class="journey-role">${item.role}</div>
        <div class="journey-period">${item.period}</div>
        <p class="journey-description">${item.description}</p>
      </div>
    </div>
  `).join('');
}

// ===== View Counter =====
const viewCountEl = document.getElementById('view-count');
const counterId = 'pritamdeka-homepage';

async function updateViewCounter() {
  try {
    const response = await fetch(`https://api.countapi.xyz/hit/pritamdeka/${counterId}`);
    const data = await response.json();
    viewCountEl.textContent = data.value.toLocaleString();
  } catch (error) {
    viewCountEl.textContent = 'N/A';
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

// ===== Citation Counter =====
const citationCountEl = document.getElementById('citation-count');
if (citationCountEl) {
  citationCountEl.textContent = '100+'; // Update manually from Google Scholar
}

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
      } else {
        formStatus.textContent = '❌ Something went wrong. Please email me directly.';
        formStatus.className = 'error';
      }
    } catch (error) {
      formStatus.textContent = '❌ Network error. Please email me directly.';
      formStatus.className = 'error';
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

// ===== Console Easter Egg =====
console.log('%c👋 Hello, fellow developer!', 'font-size: 20px; color: #667eea; font-weight: bold;');
console.log('%cCheck out my GitHub: https://github.com/pritamdeka', 'font-size: 12px; color: #888;');