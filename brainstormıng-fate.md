what to do? web app or desktop?

answer:
For your "Landlord" (SaaS) model where you provide a portal for financial advisors and their clients, a Web-First approach (Next.js) is strongly recommended. Here is how that process looks and why it fits your vision:

1. Web-First (SaaS) is the "Landlord" Model
Since you want to be the "landlord," you host the entire infrastructure (Backend + Database) once.

Accessibility: Clients of financial advisors often don't want to download and install a desktop app just to check their portal once a week. They want a link they can click from an email or a bookmark.
Maintenance: You only have to update the web app once, and every advisor and client gets the new version instantly.
Onboarding: It’s much easier for an advisor to "invite" a client to a web URL than to ask them to install a .exe or .app file.
2. Your Current Tech Stack is Ready for This
Your current setup (FastAPI backend + Next.js frontend) is perfectly suited for a multi-tenant SaaS:

Backend (FastAPI): This is already your "Headless" engine. It handles all the ML models and data. It doesn't care if the request comes from a Web browser, a Mobile app, or a Desktop app.
Frontend (Next.js): This can be deployed as a standard website, but it also supports PWA (Progressive Web App). This means users can "install" the website to their phone or desktop home screen, and it will behave like a native app.
3. The "Landlord" Architecture (Multi-Tenancy)
To go live as a landlord, your next phase in the backend will focus on Multi-Tenancy. This usually follows one of two paths:

Shared Database: All advisors and clients are in the same tables, but every row has an advisor_id column. Your API ensures an advisor only sees their own clients.
Subdomain-based: Each advisor could have their own URL (e.g., advisor-a.fin-eye.com), which gives a premium "white-label" feel.
4. Expansion to Desktop/Mobile
If you later decide you need a dedicated Desktop or Mobile app, you don't have to rewrite everything:

Desktop: You can use Electron or Tauri to wrap your existing Next.js frontend into a .exe or .dmg file.
Mobile: You can build a Flutter or React Native app that connects to the same FastAPI backend you are using now.
Recommendation: When you "Go Live"
Deploy the Web App first: Use a platform like Vercel (for frontend) and AWS/GCP (for backend).
Handle Internet via API: Since you mentioned "with internet connection it will be handled," the frontend will simply fetch data from your FastAPI server. If there's no internet, the app can show cached data (handled by Next.js/service workers).
White-Labeling: Financial advisors will love if they can put their own logo on the portal you provide. Your "Landlord" role is to manage the "Tenants" (Advisors) and provide them with this customized experience.
In summary: Start with the Web App as your core SaaS product. It’s the most scalable "landlord" model and gives you the fastest path to getting your first financial advisor users.