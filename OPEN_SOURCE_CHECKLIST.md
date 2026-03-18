# Open Source Release Checklist

Use this checklist before creating the public GitHub repository.

## 1) Security and privacy

- [ ] Ensure no secrets are committed (`apiKey`, tokens, credentials).
- [ ] Keep local runtime config out of git (`openclaw.json`, `.env*`, `.openclaw/`).
- [ ] Confirm `openclaw.example.json` is safe and up to date.
- [ ] Verify no personal machine paths are present in docs/screenshots.

## 2) Project metadata

- [ ] Update `README.md` placeholders:
  - [ ] `<your-github-username>`
  - [ ] `<your-support-email>`
- [ ] Confirm `LICENSE` is the intended license.
- [ ] Review `SECURITY.md` and `CODE_OF_CONDUCT.md`.
- [ ] Confirm `CONTRIBUTING.md` is current.

## 3) Quality baseline

- [ ] Run tests locally (`python -m unittest tests.test_core_modules -v`).
- [ ] Launch app and smoke test key pages:
  - [ ] Install
  - [ ] Skills
  - [ ] Instances
  - [ ] Cost
  - [ ] Team
- [ ] Confirm no startup exceptions.

## 4) Publish steps

```powershell
# In project root
git init
git add .
git commit -m "Initial open-source release"
```

If GitHub CLI is installed and authenticated:

```powershell
gh auth login
gh repo create butlerclaw --public --source . --remote origin --push
```

If GitHub CLI is not available:

1. Create an empty repo on GitHub web.
2. Then run:

```powershell
git remote add origin https://github.com/<your-github-username>/butlerclaw.git
git branch -M main
git push -u origin main
```

## 5) First release tag

```powershell
git tag -a v0.1.0 -m "First open-source release"
git push origin v0.1.0
```

