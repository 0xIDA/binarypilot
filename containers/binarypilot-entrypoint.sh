#!/bin/bash
set -e

profile="${BINARYPILOT_VPN_PROFILE:-}"
if [ -z "$profile" ]; then
    profile=$(ls /vpn/*.ovpn 2>/dev/null | head -n1 || true)
fi

if [ -n "$profile" ] && [ -f "$profile" ]; then
    echo "[binarypilot] OpenVPN starting on $profile"
    sudo openvpn --config "$profile" --daemon --log /tmp/openvpn.log --writepid /tmp/openvpn.pid \
        || echo "[binarypilot] openvpn failed to start; see /tmp/openvpn.log"
fi

exec /usr/local/bin/docker-entrypoint.sh "$@"
