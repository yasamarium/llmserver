# yasamarium/llmserver

[![CI / CD Server](https://github.com/yasamarium/llmserver/actions/workflows/server.yml/badge.svg)](https://github.com/yasamarium/llmserver/actions/workflows/server.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Model: Qwen3-4B](https://img.shields.io/badge/Model-Qwen3--4B-purple.svg)](https://huggingface.co/bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF)

An OpenAI-compatible HTTP API server running **Qwen3 4B** locally on a GitHub Actions runner (or local CPU environment). Designed as the dedicated AI inference backend for the user-facing **`yasamarium/llm`** application deployed on Vercel.

---

## Table of Contents

1. [What the Project Does](#1-what-the-project-does)
2. [Qwen3 4B Requirements](#2-qwen3-4b-requirements)
3. [How the Model is Downloaded](#3-how-the-model-is-downloaded)
4. [How to Run the Server Locally](#4-how-to-run-the-server-locally)
5. [How to Configure Environment Variables](#5-how-to-configure-environment-variables)
6. [How to Configure GitHub Secrets](#6-how-to-configure-github-secrets)
7. [How the GitHub Actions Workflow Works](#7-how-the-github-actions-workflow-works)
8. [How the ~5-Hour Restart Cycle Works](#8-how-the-5-hour-restart-cycle-works)
9. [GitHub Actions Runtime Limitations](#9-github-actions-runtime-limitations)
10. [How `yasamarium/llm` Should Call the API](#10-how-yasamariumllm-should-call-the-api)

---

## 1. What the Project Does

`yasamarium/llmserver` serves large language model inference using CPU-friendly quantized GGUF weights via `llama.cpp` and `llama-cpp-python`.

### Two-Repository Architecture

```
┌──────────────────────────────────────────────┐
│             yasamarium/llm                   │
│          (Deployed on Vercel)                │
│       User-facing web application            │
└──────────────────────┬───────────────────────┘
                       │
                       │ HTTPS Requests (Bearer $API_KEY)
                       │ (via Cloudflare Tunnel)
                       ▼
┌──────────────────────────────────────────────┐
│           yasamarium/llmserver               │
│        (GitHub Actions Runner / CPU)         │
│  - FastAPI OpenAI-compatible API             │
│  - Qwen3 4B GGUF Q4_K_M (llama.cpp)          │
│  - ~5h In-Job Restart Supervisor             │
│  - Concurrency-safe Workflow Retriggering    │
└──────────────────────────────────────────────┘
```

- **OpenAI Compatibility**: Provides standard endpoints (`/v1/chat/completions`, `/v1/completions`, `/v1/models`, `/health`).
- **Streaming Support**: Supports Server-Sent Events (`text/event-stream`) for real-time word-by-word streaming.
- **CPU Optimization**: Tuned specifically for standard multicore CPU environments (AVX2, OpenMP, zero GPU requirements).
- **Public Tunneling**: Exposes the local runner port securely to the internet via Cloudflare Tunnel (`trycloudflare.com` or custom domains).

---

## 2. Qwen3 4B Requirements

The server runs **Qwen3 4B** quantized to **GGUF `Q4_K_M`**:

| Parameter | Recommended Specification | GitHub Actions Standard Runner |
| :--- | :--- | :--- |
| **Model Format** | GGUF (`Q4_K_M` quantization) | GGUF (`Q4_K_M`) |
| **Model Size** | ~2.49 GB | Stored on runner ephemeral disk |
| **RAM Required** | 4.5 GB - 5.5 GB (weights + context) | 7 GB total available |
| **Context Window** | 2,048 tokens (configurable up to 4,096) | 2,048 tokens |
| **CPU Threads** | 2 - 4 vCPUs | 2 vCPUs (`THREADS=2`) |
| **GPU Requirement** | None (CPU only, `n_gpu_layers=0`) | Zero GPU dependency |

---

## 3. How the Model is Downloaded

The model is managed by [`scripts/download_model.py`](scripts/download_model.py):

1. **Existence Check**: Checks if `models/qwen3-4b-instruct-q4_k_m.gguf` is already present with valid file size (> 500 MB). If found, download is skipped.
2. **Resumable HTTP Download**: Uses HTTP `Range: bytes=X-` requests to resume automatically if network drops or is interrupted.
3. **Atomic Write**: Streams chunks to `.tmp` file and performs an atomic rename once finished, preventing corrupted partial files from loading.
4. **Integrity Check**: Supports optional SHA-256 verification via `MODEL_SHA256`.
5. **Git Safety**: Model weights are in `.gitignore` and are **never committed to Git**.
6. **No API Exposure**: The model binary is loaded internally and never served as a downloadable static file.

---

## 4. How to Run the Server Locally

### Prerequisites
- Python 3.10+
- `curl` and `git`

### Installation

```bash
# Clone the repository
git clone https://github.com/yasamarium/llmserver.git
cd llmserver

# Create virtual environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu

# Configure environment
cp .env.example .env
# Edit .env and set your API_KEY
```

### Download Model & Start Server

```bash
# 1. Download model
python scripts/download_model.py

# 2. Run unit tests
pytest tests/test_api.py -v

# 3. Start server
uvicorn src.server:app --host 0.0.0.0 --port 8000 --reload
```

---

## 5. How to Configure Environment Variables

All settings can be specified in `.env` or set as shell environment variables:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `API_KEY` | `""` | Secret Bearer token required in `Authorization: Bearer <API_KEY>` |
| `HOST` | `0.0.0.0` | Server bind IP address |
| `PORT` | `8000` | Server listening port |
| `MODEL_NAME` | `qwen3-4b` | Model identifier returned in API responses |
| `MODEL_FILE` | `qwen3-4b-instruct-q4_k_m.gguf` | Filename of the GGUF model |
| `MODEL_PATH` | `models/qwen3-4b-instruct-q4_k_m.gguf` | Local path where weights are stored |
| `MODEL_URL` | `https://huggingface.co/...` | Direct Hugging Face download URL for GGUF weights |
| `CONTEXT_SIZE` | `2048` | Maximum context tokens (CPU friendly) |
| `THREADS` | `2` | Number of CPU threads used for inference |
| `BATCH_SIZE` | `512` | Prompt processing batch size |
| `MAX_TOKENS` | `512` | Default max generation tokens |
| `TEMPERATURE` | `0.7` | Default sampling temperature |
| `MOCK_MODEL` | `false` | Set to `true` to simulate inference without GGUF weights (tests) |
| `RESTART_INTERVAL_SECONDS` | `18000` | In-job restart cycle interval in seconds (18,000s = 5 hours) |
| `CLOUDFLARE_TUNNEL_TOKEN` | `""` | Optional named tunnel token for fixed custom domain |
| `GH_PAT` | `""` | GitHub Personal Access Token for workflow re-dispatch and cross-repo syncing |
| `TARGET_REPO` | `yasamarium/llm` | Target Vercel repository to receive endpoint URL updates |

---

## 6. How to Configure GitHub Secrets

Navigate to your GitHub repository:
**Settings** ➔ **Secrets and variables** ➔ **Actions** ➔ **New repository secret**:

| Secret Name | Required? | Purpose |
| :--- | :--- | :--- |
| `API_KEY` | **Required** | Secret key for API authentication (e.g. `sk-live-...`). Clients must send this token. |
| `GH_PAT` | **Recommended** | Personal Access Token with `repo` and `workflow` scopes to allow automatic runner chaining and updating the target repo. |
| `CLOUDFLARE_TUNNEL_TOKEN` | Optional | If you configure a Cloudflare Named Tunnel, provide its token to get a **permanent static URL** (e.g., `https://llm.yourdomain.com`). |

> [!NOTE]
> If `CLOUDFLARE_TUNNEL_TOKEN` is not provided, the workflow automatically uses Cloudflare **Quick Tunnels** (`https://*.trycloudflare.com`). The live URL is printed in the step logs and added to the **GitHub Actions Job Summary**.

---

## 7. How the GitHub Actions Workflow Works

Workflow file: [`.github/workflows/server.yml`](.github/workflows/server.yml)

### Workflow Pipeline

```
1. Checkout Repo
       ↓
2. Setup Python 3.11 & Cache
       ↓
3. Install Dependencies & Cloudflared
       ↓
4. Download Qwen3 4B GGUF (Check Cache)
       ↓
5. Run Automated Tests
       ↓
6. Start Server & Public Tunnel
       ↓
7. Serve for ~5 Hours (scripts/start_server.sh)
       ↓
8. Graceful Handoff & Dispatch Next Runner (scripts/retrigger_workflow.py)
```

### Safety & Concurrency Control

The workflow enforces singleton execution:

```yaml
concurrency:
  group: llmserver-singleton
  cancel-in-progress: false
```

- **No duplicate parallel jobs**: If a runner is already executing, no second job will spin up.
- **Circuit breaker**: `scripts/retrigger_workflow.py` inspects recent workflow history. If more than 3 dispatches occurred in 2 hours, it halts to avoid runaway loops.

---

## 8. How the ~5-Hour Restart Cycle Works

Standard long-running processes on CPU can accumulate memory fragmentation. The server uses a two-tier restart strategy:

```
Start server (uvicorn)
        ↓
Health check (GET /health)
        ↓
Serve incoming requests
        ↓
~5 hours (RESTART_INTERVAL_SECONDS)
        ↓
Graceful stop (SIGTERM with 30s drain)
        ↓
Restart server
        ↓
Health check
        ↓
Serve requests again
        ↓
Repeat until job handoff
```

1. **Process Supervision**: [`scripts/start_server.sh`](scripts/start_server.sh) spawns `src.server:app` and captures its PID.
2. **Health Check Polling**: Polls `http://127.0.0.1:$PORT/health` every 2s until `{"status":"ok","model":"qwen3-4b"}` is verified.
3. **Heartbeat Monitoring**: Heartbeat logs print every 30 minutes.
4. **Graceful Drain**: When the ~5-hour threshold is reached, `SIGTERM` is dispatched to allow in-flight inference requests to complete before terminating.

---

## 9. GitHub Actions Runtime Limitations

> [!IMPORTANT]
> GitHub Actions is primarily a CI/CD platform, not a dedicated cloud VPS. Be mindful of these runtime realities:

1. **6-Hour Hard Job Limit**: Standard GitHub-hosted runners have an absolute ceiling of 360 minutes (6 hours). Any job exceeding 6 hours is forcibly killed. Our workflow runs for ~5 hours and then cleanly hands off to the next run.
2. **Ephemeral Runners**: Every runner VM is destroyed after completion. Model caches in `actions/cache` are opportunistic and have an eviction policy with a 10 GB total repository limit.
3. **Bandwidth & Abuse Policies**: Do not use GitHub Actions to run crypto miners or high-throughput commercial proxies. Using it for self-hosted developer staging or periodic AI experiments is within typical developer workflows.
4. **Public Tunnel Churn**: If using Cloudflare Quick Tunnel (`trycloudflare.com`), the URL changes whenever a new runner starts. For production reliability, use a **Cloudflare Named Tunnel** (`CLOUDFLARE_TUNNEL_TOKEN`) with a fixed custom domain.

---

## 10. How `yasamarium/llm` Should Call the API

In the `yasamarium/llm` repository (deployed on Vercel):

### 1. Configure Vercel Environment Variables
Set these variables in your Vercel Project Settings:
- `LLMSERVER_URL`: The public tunnel URL (e.g. `https://api.yourdomain.com` or `https://<hash>.trycloudflare.com`)
- `LLMSERVER_API_KEY`: The same value configured in `API_KEY`

### 2. Example cURL Request

```bash
curl -X POST "$LLMSERVER_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "qwen3-4b",
    "messages": [
      {
        "role": "user",
        "content": "Hello!"
      }
    ],
    "max_tokens": 256
  }'
```

### 3. Example Response

```json
{
  "id": "chatcmpl-1a2b3c4d5e6f",
  "object": "chat.completion",
  "created": 1725540000,
  "model": "qwen3-4b",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I assist you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 10,
    "total_tokens": 22
  }
}
```

### 4. Vercel Next.js / TypeScript Integration (AI SDK)

```typescript
// app/api/chat/route.ts
import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const { messages } = await req.json();

  const response = await fetch(`${process.env.LLMSERVER_URL}/v1/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${process.env.LLMSERVER_API_KEY}`,
    },
    body: JSON.stringify({
      model: "qwen3-4b",
      messages,
      stream: true,
    }),
  });

  return new Response(response.body, {
    headers: { "Content-Type": "text/event-stream" },
  });
}
```

---

## API Endpoints Reference

| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | None | Basic server status and metadata |
| `GET` | `/health` | None | Health check (`{"status": "ok", "model": "qwen3-4b"}`) |
| `GET` | `/v1/models` | Bearer | OpenAI-compatible model list |
| `POST` | `/v1/chat/completions` | Bearer | OpenAI chat completions (streaming & non-streaming) |
| `POST` | `/v1/completions` | Bearer | OpenAI text completion |

---

## License

This project is licensed under the [MIT License](LICENSE).
