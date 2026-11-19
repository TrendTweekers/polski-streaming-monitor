#!/bin/sh
# /vpn/client.ovpn (inline certs) and /vpn/auth.txt (user, password) are mounted read-only.
openvpn --config /vpn/client.ovpn --auth-user-pass /vpn/auth.txt --script-security 1 --pull-filter ignore "dhcp-option" --daemon --log /tmp/ovpn.log
for i in $(seq 1 40); do ip link show tun0 >/dev/null 2>&1 && break; sleep 1; done
ip link show tun0 >/dev/null 2>&1 || { echo "tun0 did not come up"; cat /tmp/ovpn.log; exit 1; }
echo "nameserver ${DNS:-1.1.1.1}" > /etc/resolv.conf
echo "vpn up"
exec microsocks -i 0.0.0.0 -p 1080
