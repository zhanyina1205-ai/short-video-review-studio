#!/bin/zsh
cd "${0:A:h}"
if /usr/bin/curl -fsS --max-time 2 http://127.0.0.1:18476/api/health 2>/dev/null | /usr/bin/grep -q video-review-studio; then
  open http://127.0.0.1:18476
else
  exec /usr/bin/python3 server.py --open
fi
