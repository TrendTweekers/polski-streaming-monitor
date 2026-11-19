# OpenVPN client + SOCKS5 proxy, for VPN providers without WireGuard files (CyberGhost).
FROM alpine:3.20
RUN apk add --no-cache openvpn microsocks
COPY run.sh /run.sh
RUN chmod +x /run.sh
ENTRYPOINT ["/run.sh"]
