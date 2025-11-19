# ⚡ Web Demo Quick Start

## One Command to Rule Them All

```bash
./demo/start_demo.sh
```

Then open: **http://localhost:8000** 🎉

## What You Get

### Beautiful Web Interface
```
┌────────────────────────────────────────┐
│   🔍 Verus Lemma Finder               │
│   Semantic search for Verus lemmas     │
├────────────────────────────────────────┤
│ Search: [modular arithmetic        ] 🔍│
├────────────────────────────────────────┤
│ ┌────────────────────────────────────┐ │
│ │ lemma_mod_mod              [0.850] │ │
│ │ 📄 pow_lemmas.rs:42                 │ │
│ │ → View on GitHub                    │ │
│ │                                     │ │
│ │ Proof that (x % (a*b)) % a == x % a │ │
│ │                                     │ │
│ │ Signature: pub fn lemma_mod_mod(...) │ │
│ └────────────────────────────────────┘ │
│                                        │
│ Found 8 results for "modular arithmetic"│
└────────────────────────────────────────┘
```

### Complete REST API
```bash
# Search
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "sequence properties", "top_k": 5}'

# Health Check
curl http://localhost:8000/api/health

# Auto-Generated Docs
open http://localhost:8000/docs
```

## Try These Queries

- `modular arithmetic`
- `sequence properties`
- `vector bounds`
- `proving things about multiplication`

## Tech Stack

| Component | Tech | Lines of Code |
|-----------|------|---------------|
| Backend | FastAPI | 212 |
| Frontend | HTML/CSS/JS | 476 |
| Startup Script | Bash | 26 |
| **Total** | | **714** |

## Files Structure

```
demo/
├── server.py           # FastAPI backend
├── index.html          # Web UI (self-contained)
├── start_demo.sh       # One-command startup
└── quickstart.md       # This file!

data/
└── curve25519-dalek_lemma_index.*  # Pre-built indexes
```

## Why This Demo Rocks

✅ **Minimal** - Only ~700 lines of code total  
✅ **Modern** - FastAPI + modern JS (2025 tech)  
✅ **Fast** - Semantic search in 10-50ms  
✅ **Beautiful** - Gradient UI, smooth animations  
✅ **Production-Ready** - Can deploy as-is  
✅ **No Build Step** - Works immediately  
✅ **Extensible** - Easy to add features  

## Deploy Your Demo

### Fly.io (Recommended)
```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login and deploy
flyctl auth login
flyctl launch
```

**Live Demo**: https://verus-lemma-finder.fly.dev/

---

**Now go try it!** → `./demo/start_demo.sh` 🚀

