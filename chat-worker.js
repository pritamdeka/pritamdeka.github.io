// Chatbot proxy for pritamdeka.github.io
// Deploy: Cloudflare Workers → Create Worker → paste this code
// Set secret: Settings → Variables → GEMINI_API_KEY = your_key
// Replace CHAT_WORKER_URL in dynamic.js with the Worker URL
// After editing this file, re-paste it into the Cloudflare dashboard — the repo copy is not auto-deployed

const GEMINI_MODEL = 'gemini-3.8-flash';
const GEMINI_URL = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent`;

// Sites allowed to call this proxy (custom domain + GitHub Pages fallback)
const ALLOWED_ORIGINS = [
  'https://pritamdeka.com',
  'https://www.pritamdeka.com',
  'https://pritamdeka.github.io',
];

// Caps to keep abuse (and Gemini spend) bounded
const MAX_MESSAGE_CHARS = 1000;
const MAX_HISTORY_TURNS = 4;

const SYSTEM_PROMPT = `You are a friendly AI assistant on Dr. Pritam Deka's personal website. Answer questions about his research, publications, experience, education and projects. Be concise (2-4 sentences unless asked for detail). If you don't know something, say so and suggest emailing contact@pritamdeka.com.

You have access to Google Search — use it when visitors ask about recent publications, citations, news, or anything time-sensitive. Search for "Pritam Deka" along with relevant keywords (e.g., "Pritam Deka Google Scholar", "Pritam Deka arXiv", "Pritam Deka HuggingFace", "Pritam Deka Queen's University Belfast").

About Dr. Pritam Deka:
- AI Engineer & Research Fellow at Queen's University Belfast, UK
- PhD in Computer Science (QUB, 2019-2024), thesis on evidence-based verification of online health information
- Co-Founder & AI Product Lead at Khyontek AI (Guwahati, Assam, Jan 2026-present)
- Spasht Health (spashthealth.com, public beta since Sep 2026): Khyontek AI's free medical report reader for India. Users photograph a lab report, prescription or discharge summary and get each value explained in plain language in English or 19 Indian languages, plotted against the report's own reference ranges, with questions to ask their doctor. It explains reports, it does not diagnose; reports are not stored and no account is needed
- Research: NLP, LLMs, Vision-Language Models, agentic AI, document intelligence, information extraction, fact-checking, RAG
- 12+ publications including Best Paper at iiWAS 2021
- 2026: papers at ACM SAC 2026 and IEEE Access on process diagram extraction with VLMs
- 2025: Flowchart2Mermaid arXiv preprint
- 50+ models and 20+ datasets on HuggingFace
- Live apps: Spasht Health (spashthealth.com), Flowchart-to-Mermaid (Vercel), BelfastBuild AI (Vercel), Biomedical Fact-Checker (HF Spaces)
- Reviewer for ICML 2026, NeurIPS 2026, ACM SAC 2024, ICON 2021/2023, GPTMB 2024
- Education: PhD (QUB), MTech IT (Tezpur University), BE CSE (Gauhati University)
- Google Scholar ID: b0jYTAUAAAAJ
- Contact: contact@pritamdeka.com (p.deka@qub.ac.uk), Belfast, UK`;

// Simple in-memory rate limiting (per IP, resets on deploy)
const rateLimit = new Map();
const MAX_PER_HOUR = 20;

export default {
  async fetch(request, env) {
    // CORS — echo the origin only if it is one of ours
    const origin = request.headers.get('Origin') || '';
    const headers = {
      'Access-Control-Allow-Origin': ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0],
      'Vary': 'Origin',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Content-Type': 'application/json',
    };
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers });
    }
    if (request.method !== 'POST') {
      return new Response(JSON.stringify({ error: 'Method not allowed' }), { status: 405, headers });
    }
    if (!ALLOWED_ORIGINS.includes(origin)) {
      return new Response(JSON.stringify({ error: 'Forbidden' }), { status: 403, headers });
    }

    // Rate limiting
    const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
    const now = Date.now();
    const window = Math.floor(now / 3600000); // hour bucket
    const key = `${ip}:${window}`;
    const count = rateLimit.get(key) || 0;
    if (count >= MAX_PER_HOUR) {
      return new Response(JSON.stringify({ error: 'Rate limit exceeded. Please try again later.' }), { status: 429, headers });
    }
    rateLimit.set(key, count + 1);
    // Clean old entries
    if (rateLimit.size > 1000) {
      for (const [k] of rateLimit) {
        if (parseInt(k.split(':')[1]) < window - 1) rateLimit.delete(k);
      }
    }

    const apiKey = env.GEMINI_API_KEY || '';
    if (!apiKey) {
      return new Response(JSON.stringify({ error: 'Server not configured — add GEMINI_API_KEY secret' }), { status: 500, headers });
    }

    try {
      const body = await request.json();
      const userMessage = String(body.message || '').trim();
      const history = Array.isArray(body.history) ? body.history : [];

      if (!userMessage) {
        return new Response(JSON.stringify({ error: 'Empty message' }), { status: 400, headers });
      }
      if (userMessage.length > MAX_MESSAGE_CHARS) {
        return new Response(JSON.stringify({ error: `Please keep questions under ${MAX_MESSAGE_CHARS} characters.` }), { status: 400, headers });
      }

      // Build conversation: prior turns first, current question last.
      // The client sends history that already ends with the current question, so drop it.
      const prior = history.slice(0, -1).slice(-MAX_HISTORY_TURNS)
        .filter(h => h && typeof h.text === 'string' && h.text.trim())
        .map(h => ({
          role: h.role === 'bot' ? 'model' : 'user',
          parts: [{ text: h.text.slice(0, MAX_MESSAGE_CHARS * 2) }],
        }));
      const contents = [...prior, { role: 'user', parts: [{ text: userMessage }] }];

      // Enable Google Search grounding so Gemini can look up recent info
      const res = await fetch(GEMINI_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-goog-api-key': apiKey },
        body: JSON.stringify({
          systemInstruction: { parts: [{ text: SYSTEM_PROMPT }] },
          contents: contents,
          tools: [{ google_search: {} }],
          generationConfig: { temperature: 0.7, maxOutputTokens: 1024 },
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        console.error('Gemini error', res.status, JSON.stringify(data).slice(0, 500));
        return new Response(JSON.stringify({ error: 'The AI service is busy right now. Please try again shortly.' }), { status: 502, headers });
      }
      // Extract text from response (may include multiple parts if grounding citations are present; skip thought parts)
      const parts = data?.candidates?.[0]?.content?.parts || [];
      const reply = parts.filter(p => !p.thought).map(p => p.text || '').filter(Boolean).join('
') || 'Sorry, I could not generate a response.';

      return new Response(JSON.stringify({ reply }), { headers });
    } catch (err) {
      return new Response(JSON.stringify({ error: 'Internal error' }), { status: 500, headers });
    }
  },
};
