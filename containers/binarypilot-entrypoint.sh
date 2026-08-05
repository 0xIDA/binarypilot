#!/bin/bash
set -e

profile="${BINARYPILOT_VPN_PROFILE:-}"
if [ -z "$profile" ]; then
    profile=$(ls /vpn/*.ovpn 2>/dev/null | head -n1 || true)
fi

if [ -n "$profile" ] && [ -f "$profile" ]; then
    echo "[binarypilot] OpenVPN starting on $profile"
    if sudo openvpn --config "$profile" --daemon --log /tmp/openvpn.log --writepid /tmp/openvpn.pid; then
        # Wait for tun interface to come up (mirrors openvpn's --daemon return,
        # which happens before routes are installed). Cap at 30s so a down
        # server doesn't jam the agent forever.
        for _ in $(seq 1 30); do
            if ip link show dev tun0 >/dev/null 2>&1; then
                echo "[binarypilot] tun0 up"
                break
            fi
            sleep 1
        done
    else
        echo "[binarypilot] openvpn failed to start; see /tmp/openvpn.log"
    fi
fi

exec /usr/local/bin/docker-entrypoint.sh "$@"
