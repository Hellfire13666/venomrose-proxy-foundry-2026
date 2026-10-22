# 🥀 VENOMROSE // GitHub Guide

Official repository target: `Hellfire13666/venomrose-proxy-foundry-2026`

The WOLF FANG repository is unrelated and will not be modified.

## Publish from the standalone release kit

1. Download `VENOMROSE-GITHUB-PUBLICATION-v0.1.1.zip` into `~/Downloads`.
2. Extract, open the outer `venomrose-github-publication-v0.1.1/` folder.
3. Run `./PUBLISH_VENOMROSE.sh --check`. This is offline and publishes nothing.
4. When satisfied, run `./PUBLISH_VENOMROSE.sh --publish`. It checks GitHub CLI login, validates the owner and repository name, and requires the phrase `PUBLISH VENOMROSE` before creating a **public** repository.
5. It creates the initial source commit and opens a draft release containing the original v0.1.1 visual archive. This draft is not publicly released until you explicitly publish it on GitHub.

No `git push --force`, overwrites, arbitrary remote updates, report vault uploads, or GitHub credential prompting occur.

The prepared original image is an unmodified asset: `assets/venomrose-command-center-ORIGINAL.png`. For a live proxy to be shown as working, separate verification must have succeeded; the screenshots in the image are illustrative.

## Manual clone after publishing

```bash
git clone https://github.com/Hellfire13666/venomrose-proxy-foundry-2026.git
cd venomrose-proxy-foundry-2026
./RELEASE_CHECK.sh
./OPEN_LAUNCH_CENTER.sh
```
