// ===== Theme Toggle =====
const themeToggle = document.getElementById('theme-toggle');
const body = document.body;

// Load saved theme
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
    console.log('View counter unavailable');
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

// ===== Citation Counter (Google Scholar - Manual Update) =====
// Note: Google Scholar doesn't have a public API, so you'll need to update this manually
// Or use a service like https://scholarlyapi.com/
const citationCountEl = document.getElementById('citation-count');
if (citationCountEl) {
  // Update this number periodically based on your Google Scholar profile
  citationCountEl.textContent = '100+'; // Replace with actual count
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
        headers: {
          'Accept': 'application/json'
        }
      });
      
      if (response.ok) {
        formStatus.textContent = '✅ Message sent successfully! I\'ll get back to you soon.';
        formStatus.className = 'success';
        contactForm.reset();
      } else {
        formStatus.textContent = '❌ Something went wrong. Please try again or email me directly.';
        formStatus.className = 'error';
      }
    } catch (error) {
      formStatus.textContent = '❌ Network error. Please try again or email me directly.';
      formStatus.className = 'error';
    }
    
    setTimeout(() => {
      formStatus.style.display = 'none';
    }, 5000);
  });
}

// ===== Smooth Scroll for Anchor Links =====
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function (e) {
    const href = this.getAttribute('href');
    if (href !== '#' && document.querySelector(href)) {
      e.preventDefault();
      document.querySelector(href).scrollIntoView({
        behavior: 'smooth'
      });
      
      // Close mobile menu if open
      if (mainNav && mainNav.classList.contains('active')) {
        mainNav.classList.remove('active');
        const icon = mobileMenuBtn.querySelector('i');
        icon.classList.remove('fa-times');
        icon.classList.add('fa-bars');
      }
    }
  });
});

// ===== Intersection Observer for Fade-in Animations =====
const observerOptions = {
  threshold: 0.1,
  rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.style.opacity = '1';
      entry.target.style.transform = 'translateY(0)';
    }
  });
}, observerOptions);

document.querySelectorAll('.fade-in').forEach(section => {
  observer.observe(section);
});

// ===== Typing Animation Reset on Visibility =====
const typingText = document.querySelector('.typing-text');
if (typingText) {
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      typingText.style.animation = 'none';
      typingText.offsetHeight; /* trigger reflow */
      typingText.style.animation = 'typing 3s steps(40) forwards, blink 0.7s step-end infinite';
    }
  });
}

// ===== Console Easter Egg =====
console.log('%c👋 Hello, fellow developer!', 'font-size: 20px; color: #667eea; font-weight: bold;');
console.log('%cInterested in the code? Check out my GitHub: https://github.com/pritamdeka', 'font-size: 12px; color: #888;');