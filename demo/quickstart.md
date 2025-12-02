# ⚡ Web Demo Quick Start

## Prerequisites

**All you need:**
- ✅ Python 3.12+                                 
- ✅ The demo dependencies (installed automatically by the script)

**You DON'T need:**
- ❌ `verus-analyzer` (only for building indexes)
- ❌ `scip` (only for building indexes)  
- ❌ Rust or Verus compiler

The demo uses **pre-built index files** already in the `data/` folder!

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

- `modulo is always less than divisor`
- `multiplication preserves inequality`
- `division bounds`
- `a * b <= c implies a <= c / b`

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
├── vstd_lemma_index.*              # Verus standard library
└── curve25519-dalek_lemma_index.*  # curve25519-dalek project
```

## Why This Demo Rocks

✅ **Minimal** - Only ~700 lines of code total  
✅ **Modern** - FastAPI + modern JS (2025 tech)  
✅ **Fast** - Semantic search in 10-50ms  
✅ **Beautiful** - Gradient UI, smooth animations  
✅ **Production-Ready** - Can deploy as-is  
✅ **No Build Step** - Works immediately  
✅ **Extensible** - Easy to add features  

