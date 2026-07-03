# facebook_group_rag

Ask questions about your Facebook group posts locally on your Mac — including date lookups and summarization.

Everything runs locally with [Ollama](https://ollama.com). Your Facebook data never leaves your machine and is never committed to git.

## Prerequisites

- macOS (Intel or Apple Silicon)
- Python 3.10+
- [Ollama](https://ollama.com) — `brew install ollama`
- ~10 GB free disk space (models + index)
- 8 GB+ RAM recommended (`llama3.1:8b`)

## Quick start

```bash
git clone <your-repo-url> facebook_group_rag
cd facebook_group_rag
make install
```

Add your Facebook export to `data/` (see below), then:

```bash
make ingest
make run
```

Open http://localhost:8501

## How to export your Facebook group data

1. Go to [facebook.com/dyi](https://www.facebook.com/dyi) (Download Your Information)
2. Click **Download or transfer information** → **Download your information**
3. Select **Specific types of information**
4. Check **Groups** (and **Posts** if you posted in the group)
5. Date range: **All time** (or the date range you care about)
6. Format: **JSON** or **HTML** — both work (Facebook often delivers HTML)
7. Media quality: **Low** (text is what we need)
8. Click **Create files** and wait for Facebook's email
9. Download the `.zip`, unzip it
10. Copy the unzipped folder into `data/`

Your export should include files like:

```
data/your-export-folder/your_facebook_activity/groups/
  group_posts_and_comments.html   # or .json
  your_comments_in_groups.html    # optional
```

The `data/` folder is gitignored. Only you have your data.

## Usage

```bash
make install  # install Python deps and pull Ollama models
make ingest   # (re)build the search index from data/
make run      # start the chat UI
make test     # run unit tests
make clean    # delete the index
```

`make install` is a convenience wrapper around `./setup.sh`.

### Example questions

- What did I post on March 15, 2024?
- Summarize my posts from April
- What themes and changes do you see across my posts?
- What did I post most about in Sep 2025?

### Filter by group (optional)

`GROUP_FILTER` accepts comma-separated substrings. A post is included if its group name contains **any** filter (case-insensitive). Leave empty to index all posts.

**All posts (no filter):**

```bash
make ingest
```

**One group:**

```bash
GROUP_FILTER="group1" make ingest
```

**Two groups:**

```bash
GROUP_FILTER="group1,group2" make ingest
```

## Configuration

Environment variables (all optional):

| Variable | Default | Description |
|----------|---------|-------------|
| `CHAT_MODEL` | `llama3.1:8b` | Ollama model for answers |
| `EMBED_MODEL` | `nomic-embed-text` | Ollama model for embeddings |
| `GROUP_FILTER` | (empty) | Comma-separated substrings; match if group name contains any |
| `DATA_DIR` | `./data` | Facebook export location |
| `INDEX_DIR` | `./index` | Vector index location |

For Macs with 8 GB RAM, try `CHAT_MODEL=llama3.2:3b` in `setup.sh` or before `make run`.

## Troubleshooting

**Ollama not running**

```bash
ollama serve
```

**No posts found during ingest**

- Confirm your export is in `data/`
- Look for `group_posts_and_comments.html` or `.json` under `your_facebook_activity/groups/`

**Out of memory**

Use a smaller chat model: `CHAT_MODEL=llama3.2:3b make run`

## Project structure

```
facebook_group_rag/
├── data/           # your private Facebook export (gitignored)
├── index/          # built vector index (gitignored)
├── src/
│   ├── fb_parser.py
│   ├── ingest.py
│   ├── query_engine.py
│   └── app.py
├── examples/       # sample data for testing
├── setup.sh
└── Makefile
```

## License

MIT
