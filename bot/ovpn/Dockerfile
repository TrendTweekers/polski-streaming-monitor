# OpenVPN client + SOCKS5 proxy, for VPN providers without WireGuard files (CyberGhost).
FROM alpine:3.20
RUN apk add --no-cache openvpn iproute2 \
 && apk add --no-cache --virtual .b build-base git \
 && git clone --depth 1 https://github.com/rofl0r/microsocks /tmp/ms && make -C /tmp/ms && cp /tmp/ms/microsocks /usr/local/bin/ \
 && apk del .b && rm -rf /tmp/ms
COPY run.sh /run.sh
RUN chmod +x /run.sh
ENTRYPOINT ["/run.sh"]
