// Chatbot proxy for pritamdeka.github.io
// Deploy: Cloudflare Workers → Create Worker → paste this code
// Set secret: Settings → Variables → GEMINI_API_KEY = your_key
// Replace CHAT_WORKER_URL in dynamic.js with the Worker URL

const GEMINI_MODEL = 'gemini-2.5-flash';
const GEMINI_URL = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=`;

const SYSTEM_PROMPT = `You are a friendly AI assistant on Dr. Pritam Deka's personal website. Answer questions about his research, publications, experience, education and projects. Be concise (2-4 sentences unless asked for detail). If you don't know something, say so and suggest emailing p.deka@qub.ac.uk.

About Dr. Pritam Deka:
- AI Engineer & Research Fellow at Queen's University Belfast, UK
- PhD in Computer Science (QUB, 2019-2024), thesis on evidence-based verification of online health information
- Co-Founder & AI Product Lead at Khyontek AI (Guwahati, Assam, Jan 2026-present)
- Research: NLP, LLMs, Vision-Language Models, agentic AI, document intelligence, information extraction, fact-checking, RAG
- 12+ publications including Best Paper at iiWAS 2021
- 2026: papers at ACM SAC 2026 and IEEE Access on process diagram extraction with VLMs
- 2025: Flowchart2Mermaid arXiv preprint
- 50+ models and 20+ datasets on HuggingFace
- Live apps: Flowchart-to-Mermaid (Vercel), BelfastBuild AI (Vercel), Biomedical Fact-Checker (HF Spaces)
- Reviewer for ICML 2026, NeurIPS 2026, ACM SAC 2024, ICON 2021/2023, GPTMB 2024
- Education: PhD (QUB), MTech IT (Tezpur University), BE CSE (Gauhati University)
- Contact: p.deka@qub.ac.uk, Belfast, UK`;

// Simple in-memory rate limiting (per IP, resets on deploy)
const rateLimit = new Map();
const MAX_PER_HOUR = 20;

export default {
  async fetch(request) {
    // CORS
    const headers = {
      'Access-Control-Allow-Origin': 'https://pritamdeka.github.io',
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

    const apiKey = (typeof GEMINI_API_KEY !== 'undefined') ? GEMINI_API_KEY : (globalThis.GEMINI_API_KEY || '');
    if (!apiKey) {
      return new Response(JSON.stringify({ error: 'Server not configured' }), { status: 500, headers });
    }

    try {
      const body = await request.json();
      const userMessage = body.message || '';
      const history = body.history || [];

      if (!userMessage.trim()) {
        return new Response(JSON.stringify({ error: 'Empty message' }), { status: 400, headers });
      }

      // Build conversation
      const contents = [
        { role: 'user', parts: [{ text: SYSTEM_PROMPT + '\n\nVisitor question: ' + userMessage }] }
      ];
      // Add recent history for context (last 4 turns)
      const recent = history.slice(-4);
      recent.forEach(h => {
        contents.push({
          role: h.role === 'bot' ? 'model' : 'user',
          parts: [{ text: h.text }]
        });
      });

      const res = await fetch(GEMINI_URL + apiKey, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: contents,
          generationConfig: { temperature: 0.7, maxOutputTokens: 512 },
        }),
      });

      const data = await res.json();
      const reply = data?.candidates?.[0]?.content?.parts?.[0]?.text || 'Sorry, I could not generate a response.';

      return new Response(JSON.stringify({ reply }), { headers });
    } catch (err) {
      return new Response(JSON.stringify({ error: 'Internal error' }), { status: 500, headers });
    }
  },
};
