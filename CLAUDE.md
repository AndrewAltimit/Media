# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A media dump (images, video, audio, PDFs, LaTeX sources) that other systems and agents fetch by raw GitHub URL. There is no build, lint, or test tooling. It has one maintainer, and changes are committed and pushed directly to `main`, with no branches or PRs.

Files are consumed via `https://raw.githubusercontent.com/AndrewAltimit/Media/refs/heads/main/<path>`. **Renaming, moving, or deleting a file breaks external consumers**, so treat existing paths as a public API.

## `reaction/`: agent reaction images

`reaction/config.yaml` is the registry that agents read to pick a reaction image. It has a single top-level key, `reaction_images`, which holds a list of entries:

```yaml
  - id: "miku_typing"
    source_url: "https://raw.githubusercontent.com/AndrewAltimit/Media/refs/heads/main/reaction/miku_typing.webp"
    description: "..."
    usage_scenarios:
      - "..."
    tags: ["...", "..."]
    character_appearance: "..."
```

Conventions to keep when adding or editing reactions:
- `id` equals the filename without its extension, in snake_case (`<character>_<emotion>` where possible).
- `source_url` must use the full raw GitHub URL shown above and must match the file's real extension (.png/.webp/.gif).
- Every image in `reaction/` should have exactly one config entry, and every entry should point to a file that exists. Adding a reaction means committing the image and its config entry together.
- Known issue: `noire_shocked` is used as the `id` for two entries (one `.png`, one `.webp`). Use unique ids for new entries.

Check that images and config are in sync (run from `reaction/`):
```bash
grep -o 'reaction/[^"]*' config.yaml | sed 's#reaction/##' | sort > /tmp/c.txt
ls | grep -v -e README.md -e config.yaml | sort > /tmp/f.txt
comm -3 /tmp/c.txt /tmp/f.txt   # no output = in sync
grep '  - id:' config.yaml | sort | uniq -d   # duplicate ids
```

## LaTeX documents

Each `.tex` file at the root has a matching compiled `.pdf` committed next to it. If you edit a `.tex`, rebuild its PDF and commit both (e.g. `pdflatex <name>.tex`, run twice for TOC/overlays; the Beamer decks use `tikz`). Don't commit LaTeX build artifacts such as `.aux`, `.log`, `.nav`, `.out`, `.snm`, or `.toc`.
