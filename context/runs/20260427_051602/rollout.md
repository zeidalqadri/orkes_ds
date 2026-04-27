The agent is in an idle loop — GOAL.md is done, INBOX.md is empty, and Steps 1-8 are all checking for work that doesn't exist. It's burning API credits spinning.

Want me to:

1. Fix the main loop to add a sleep/poll interval when idle (e.g., only check INBOX every few minutes instead of spinning)?
2. Give it a new task?
3. Something else?