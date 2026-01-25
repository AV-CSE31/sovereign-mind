Sovereign-Mind Custom UI
Why Build a Custom UI?
Open WebUI Limitations
Feature	Open WebUI	Custom UI Needed
Vault Integration	❌ No unlock/lock UI	✅ Show vault status, passphrase entry
Session Encryption	❌ No encrypted session picker	✅ Visual session management
PII Detection	❌ No privacy warnings	✅ Show when PII is detected/anonymized
Intent Display	❌ Hidden	✅ Badge showing simple_chat/RAG/reasoning
RAG Ingestion	⚠️ Basic file upload	✅ Full document management with metadata
Security Status	❌ None	✅ Show encryption status, audit trail
Branding	❌ Generic	✅ Sovereign-Mind identity
IMPORTANT

Open WebUI remains available on port 3000. Custom UI will run on port 3001.

Proposed Architecture
sovereign-mind/
├── app/                    # Existing FastAPI backend (unchanged)
├── ui/                     # NEW: Next.js custom UI
│   ├── src/
│   │   ├── app/           # Next.js App Router pages
│   │   ├── components/    # React components
│   │   ├── lib/           # API client, utilities
│   │   └── styles/        # Global styles
│   ├── package.json
│   └── Dockerfile
└── docker-compose.yml      # Updated to include custom UI
Key Components
1. Vault Panel
Passphrase entry for unlock
Lock button with visual indicator
Session list with encrypted badge
2. Chat Interface
Message bubbles with intent badges
Privacy indicator (🛡️ when PII anonymized)
Model selector (qwen2:0.5b, sovereign-mind-deep)
3. RAG Document Manager
File upload with drag-drop
Document list with chunk count
Search within ingested docs
4. Security Dashboard
Vault status (🔒/🔓)
Current session info
RAG collection stats
Tech Stack
Layer	Technology
Framework	Next.js 14 (App Router)
Styling	Tailwind CSS
State	React Context + SWR
API Client	Fetch with typed responses
Icons	Lucide React
Verification Plan
Manual Testing
Access UI at http://localhost:3001
Test vault unlock/lock flow
Send chat messages and verify responses
Upload document and query RAG