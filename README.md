# Resume Assets

This folder is the standalone resume workspace at the repository root.

Files:
- `index.html`: the resume source
- `resume.css`: page and print styling
- `yi-cian-huang-resume.pdf`: generated PDF output

Preview locally:

```bash
python3 -m http.server 4175 --directory resume
```

Then open `http://127.0.0.1:4175`.

Generate PDF:

```bash
google-chrome --headless --disable-gpu --no-sandbox \
  --print-to-pdf="$PWD/resume/yi-cian-huang-resume.pdf" \
  --no-pdf-header-footer \
  "file://$PWD/resume/index.html"
```
