# NEXTME v2 — AI-ready prototype

## What this version has
- 10-question onboarding
- Real AI scenario generation through OpenAI Responses API
- 3 future paths
- 30-day action plan
- "Why this future?" explanation
- Future Self chat
- Local profile saving in the browser
- Mobile-friendly UI

## Windows setup

1. Install Python 3.11+.
2. Open Command Prompt inside this folder.
3. Run:
   pip install -r requirements.txt

4. Create an OpenAI API key in your OpenAI developer account.
5. In Command Prompt, set it for this session:
   set OPENAI_API_KEY=YOUR_KEY_HERE

6. Optional model override:
   set OPENAI_MODEL=gpt-6-luna

7. Start:
   python app.py

8. Open:
   http://127.0.0.1:5000

IMPORTANT:
- Do not put the API key in index.html or JavaScript.
- This prototype stores profile data only in the user's browser localStorage.
- For production, add authentication, database, encryption/privacy controls, rate limiting, billing, logging and abuse protection.


V3 adds English / Hindi / Hinglish selection and language-aware AI replies.


V4 India Multilingual supports: English, Hindi, Hinglish, Bengali, Marathi, Gujarati, Punjabi, Tamil, Telugu, Kannada, Malayalam, Odia, Assamese, Urdu.

V5: localized chat, 45s timeout/retry, saved reports dashboard.

V6:
- NEXTME Decision Simulator
- Compare 2-3 options
- Scores for money, stability, growth, family/lifestyle, time and reversibility
- 1/3/5 year scenario impact
- Best-fit option + confidence + biggest uncertainty
- What to verify before deciding
- 7-day decision plan
- Saved decision reports in browser localStorage
