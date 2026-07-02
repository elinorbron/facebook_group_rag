# Your Facebook data (private)

Place your Facebook **Download Your Information** export here.

This folder is **gitignored** — your personal data never goes to GitHub.

## What to copy

1. Request a Facebook export (see the main [README](../README.md)).
2. Unzip the download.
3. Copy the unzipped folder into this directory, **or** copy just:
   - `your_facebook_activity/groups/group_posts_and_comments.html`
   - `your_facebook_activity/groups/your_comments_in_groups.html` (optional)

Either JSON or HTML format works. HTML is common when Facebook does not offer JSON for a category.

## Example layout

```
data/
└── facebook-yourname-2026-06-30-xxxxx/
    └── your_facebook_activity/
        └── groups/
            ├── group_posts_and_comments.html
            └── your_comments_in_groups.html
```

Then run from the project root:

```bash
make ingest
make run
```
