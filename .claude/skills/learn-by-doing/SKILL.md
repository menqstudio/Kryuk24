---
name: learn-by-doing
description: Use at the start of every KRYUK24 work session and again whenever something failed, had to be redone, or Gev corrected the approach. Reads LESSONS.md before acting and appends a new lesson after the event, so the same mistake is not repeated.
---

# Learn by doing

Gev asked on 2026-10-07 for a skill that makes Claude learn from its own work on this project.

## At session start

1. Read `docs/LESSONS.md` in the project root, after `docs/CURRENT_STATE.md` and `docs/ROADMAP.md`.
2. Before a risky or repeated kind of action (browser automation, server change, anything Armen must do, timestamps, passwords), re-read the matching section.

## When to write a lesson

Write one when any of these happened:

- an action failed and the cause was found;
- work had to be redone;
- Gev corrected the approach or rejected a result;
- a claim made earlier turned out to be wrong;
- a shortcut was found that saves real time next session.

Do not write a lesson for routine success, for one-off project state (that belongs in `docs/CURRENT_STATE.md`), or for a guess about the cause. If the cause is not proven, say so in the lesson.

## How to write it

Append to the matching section of `docs/LESSONS.md`. One lesson is three short lines:

- **What happened**: the concrete event, with the date.
- **Why**: the verified cause, or "cause not proven".
- **Do instead**: the exact action to take next time.

Keep each lesson specific enough to act on. Merge with an existing lesson instead of adding a near-duplicate. When a lesson stops being true (the tool or the code changed), correct or remove it and say why in the commit message.

## At session end

Check the session for events from the list above that were not written down yet, add them, and commit `docs/LESSONS.md` with the other state files.
