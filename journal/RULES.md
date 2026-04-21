# FUZZI RULES

Short on purpose. No "just this once".

## START

Pull `dev`. Hard. Your local copy is always wrong.
Read `events.jsonl` last 50 lines.
Read `state.json`.
Read your lane primer: `journal/primers/<lane>.md`.
If tests fail on a clean pull, stop. Tell Ciprian. Don't patch over it.

## WORK

Stay in your lane. Others will notice.
See a bug outside your lane? Log it in the journal. Don't silently "improve" someone else's code.
Already in `state.json.now` as somebody's subject? Pick something else.
One subject per commit. Bundled commits hide bugs.
Tests green *before* you commit. Not after. Not "will fix next round".
No `print()`. Everything goes through the blotter.
Secrets live in `.env`. If a key shows up in a diff, fix it now, not tomorrow.
If you hack something, say so in the journal. Hidden hacks become permanent debt.

## FINISH

Append one JSON line per subject done to `events.jsonl`.
Update `state.json`: drop done items from `now`, promote from `next`.
Run `python journal/render.py`.
One commit covers code + journal + docs. Bundled, not split.
`git push origin dev`.

## WORDS

No "I". No "we". No agent names. The journal doesn't care who did it.
Commit messages: lowercase, imperative. `add regime tests`, not `Added regime tests`.
Tone: simple, direct, occasional wit. Not corporate. Not robotic. Not chatty.
If a sentence could live on a motivational poster, delete it.

## CODE

Python 3.11+. Type hints everywhere. `slots=True` on dataclasses.
Short names. Use the Fuzzi vocab when there's a Fuzzi word: pit, tape, nerve, blotter, ghost, seatbelt, runner, signal.
Comments explain *why*, not *what*. The code says what. If the "why" isn't weird, skip it.
File over ~500 lines is probably two files pretending to be one.
No `TODO` without a matching journal entry. Otherwise it's a wish, not a task.

## GIT

Work on `dev`. No new branches unless Ciprian says so.
Never `--force`. Especially not on `main`.
Pull before you push.
One logical change per commit. If your message has "and" in it twice, split it.

## BEFORE YOU TOUCH ANYTHING

Check git log: has someone already done this? Merge, don't redo.
Check `state.json`: is this subject already in flight? Pick something else.
Unsure whose lane it is? Ask. Five seconds of asking saves an afternoon of untangling.

## STOP AND ASK CIPRIAN

Unknown test failure on a clean pull.
Design change, big or small.
New dependency, language, framework, or external service.
Two agents hit the same file.
Anything that changes how money flows.
Gut says something's off.

No guessing. This is money, not a toy.
