#!/usr/bin/env bash
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$HOME/.npm-global/bin:/usr/local/bin:$HOME/.nvm/versions/node/v22.22.0/bin:$PATH"
cd "$HOME/orkes_ds2"
set -a
[ -f /home/the_bomb/orkes/.env ] && source /home/the_bomb/orkes/.env
[ -f ./.env ] && source ./.env
set +a
source .venv/bin/activate
exec python3 arbos.py 2>&1
