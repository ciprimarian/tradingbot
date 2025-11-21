# Documentation Deployment

So you want to know how this documentation gets deployed online. Fair enough.

## The Setup

The docs are built with MkDocs and the Material theme, then automatically deployed to GitHub Pages when you push changes. It's all automated via GitHub Actions. Pretty painless once it's set up.

Each branch gets its own documentation:
- `main` → https://ciprimarian.github.io/tradingbot/
- `dev` → https://ciprimarian.github.io/tradingbot/dev/
- `data` → https://ciprimarian.github.io/tradingbot/data/

## How Auto-Deployment Works

When you push changes to `docs/` or `mkdocs.yml` on main, dev, or data branches, GitHub Actions kicks in:

1. Spins up a Ubuntu container
2. Installs Python and MkDocs
3. Builds the static site
4. Deploys to GitHub Pages
5. Keeps other branch deployments intact

The workflow file is `.github/workflows/docs.yml` if you want to see how it works.

## Working on Docs Locally

### Install Dependencies

First time setup:

```bash
pip install mkdocs mkdocs-material pymdown-extensions mkdocs-git-revision-date-localized-plugin
```

Or just install everything:

```bash
pip install -r requirements.txt
```

### Preview Changes

Serve the docs locally with live reload:

```bash
mkdocs serve
```

Open http://localhost:8000 and any changes you make to markdown files will auto-refresh. Pretty convenient.

### Build Locally

Test that everything builds without errors:

```bash
mkdocs build
```

Or if you want to be strict about it:

```bash
mkdocs build --strict
```

The `--strict` flag treats warnings as errors. Good for catching issues before pushing.

## Adding New Pages

Say you want to add a new doc page. Here's the process:

### 1. Create the File

```bash
touch docs/your-new-page.md
```

### 2. Update Navigation

Edit `mkdocs.yml` and add it to the `nav` section:

```yaml
nav:
  - Home: index.md
  - Your Section:
      - Your Page: your-new-page.md
```

### 3. Write Content

Just write regular markdown. You can use some extra features:

**Code blocks:**

```python
def example():
    return "hello"
```

**Admonitions (those colored boxes):**

```markdown
!!! note
    This is a note

!!! warning
    This is a warning

!!! tip
    Pro tip here
```

**Mermaid diagrams:**

```markdown
```mermaid
graph LR
    A --> B --> C
```
```

### 4. Preview and Commit

```bash
mkdocs serve  # Check it looks good

git add docs/your-new-page.md mkdocs.yml
git commit -m "Add new page"
git push
```

Documentation will auto-deploy in a few minutes.

## Branch-Specific Docs

### Updating Dev Docs

```bash
git checkout dev
# Make changes to docs/
git commit -m "Update dev docs"
git push origin dev
```

Docs go live at `/dev/` subdirectory.

### Updating Data Branch

```bash
git checkout data
# Make changes
git commit -m "Update data docs"
git push origin data
```

### Syncing Between Branches

If you want to pull docs from main to dev:

```bash
git checkout dev
git checkout main -- docs/
git checkout main -- mkdocs.yml
git commit -m "Sync docs from main"
git push
```

## Configuration

### MkDocs Config (`mkdocs.yml`)

Main sections:

- `site_name` - Title shown in browser
- `theme` - Material theme setup, colors, features
- `nav` - Navigation structure (the sidebar menu)
- `markdown_extensions` - Extra markdown features
- `plugins` - Search, git dates, etc.

### GitHub Actions (`.github/workflows/docs.yml`)

Auto-deploys when:
- You push changes to `docs/**`
- You modify `mkdocs.yml`
- You edit the workflow file itself

It caches pip dependencies so builds are faster after the first run.

### Customizing Theme

Want different colors? Edit `mkdocs.yml`:

```yaml
theme:
  palette:
    - scheme: default
      primary: blue  # Change this
      accent: blue   # And this
```

Available: red, pink, purple, indigo, blue, cyan, teal, green, lime, yellow, amber, orange.

## Troubleshooting

### Build Fails

Check GitHub Actions logs:
1. Go to repo → Actions tab
2. Click failed workflow
3. Read the error

Common issues:
- Markdown syntax error - fix the formatting
- Broken link - make sure linked files exist
- Missing dependency - update requirements.txt

### Docs Not Updating

- Check Actions tab to see if workflow ran
- Clear browser cache (hard refresh)
- Wait a few minutes, GitHub Pages can be slow
- Verify you actually pushed the changes

### Local Build Works, GitHub Fails

- Make sure `mkdocs.yml` is committed
- Check all referenced files exist in repo
- Look at GitHub Actions logs for specifics

## One-Time Setup

If you're doing this fresh or on a fork:

1. Repo Settings → Pages
2. Source → **GitHub Actions**
3. Save

That's it. Workflow handles the rest.

## Maintenance

### Updating Theme

```bash
pip install --upgrade mkdocs-material
```

Test locally, then update version in `requirements.txt`.

### If Builds Get Slow

- Optimize or remove large images
- Remove unused plugins
- Check for big files in docs/

## What Not To Do

- Don't push huge images to docs. Compress them first.
- Don't break markdown syntax. Preview locally.
- Don't forget to update nav when adding pages.
- Don't commit the `site/` directory (it's in .gitignore for a reason).

## Resources

If you need to dig deeper:

- [MkDocs docs](https://www.mkdocs.org/)
- [Material theme docs](https://squidfunk.github.io/mkdocs-material/)
- [GitHub Pages](https://docs.github.com/en/pages)
- [GitHub Actions](https://docs.github.com/en/actions)

That's pretty much it. Keep docs in markdown, push to GitHub, let automation handle deployment.
