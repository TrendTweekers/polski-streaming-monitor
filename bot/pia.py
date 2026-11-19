#!/usr/bin/env python3
"""Build a WireGuard config for a PIA server in Poland from the PIA username and password.
PIA has no downloadable WireGuard file: each run asks the server to accept a new key
(the method from github.com/pia-foss/manual-connections). Run it WITHOUT a VPN."""
import base64, json, os, socket, ssl, urllib.parse, urllib.request
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives import serialization

CA = Path(__file__).with_name("pia_ca.crt")
REGION = "poland"


def _token(user, pw):
    data = urllib.parse.urlencode({"username": user, "password": pw}).encode()
    with urllib.request.urlopen(urllib.request.Request("https://www.privateinternetaccess.com/api/client/v2/token", data=data, headers={"User-Agent": "curl/8.5.0", "Accept": "*/*"}), timeout=30) as r:
        return json.load(r)["token"]


def _servers():
    with urllib.request.urlopen("https://serverlist.piaservers.net/vpninfo/servers/v6", timeout=30) as r:
        d = json.loads(r.read().decode().split("\n")[0])
    reg = next(x for x in d["regions"] if x["id"] == REGION)
    return reg["servers"]["wg"]


def _add_key(ip, cn, token, pub):
    ctx = ssl.create_default_context(cafile=str(CA))
    q = urllib.parse.urlencode({"pt": token, "pubkey": pub})
    with socket.create_connection((ip, 1337), timeout=20) as raw, ctx.wrap_socket(raw, server_hostname=cn) as s:
        s.sendall(f"GET /addKey?{q} HTTP/1.1\r\nHost: {cn}\r\nConnection: close\r\n\r\n".encode())
        buf = b""
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
    body = buf.split(b"\r\n\r\n", 1)[1]
    return json.loads(body)


def make_conf(user, pw):
    priv = X25519PrivateKey.generate()
    pk = base64.b64encode(priv.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())).decode()
    pub = base64.b64encode(priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
    token = _token(user, pw)
    last = None
    for srv in _servers():
        try:
            r = _add_key(srv["ip"], srv["cn"], token, pub)
            if r.get("status") == "OK":
                return (f"[Interface]\nAddress = {r['peer_ip']}\nPrivateKey = {pk}\nDNS = {r['dns_servers'][0]}\n\n"
                        f"[Peer]\nPersistentKeepalive = 25\nPublicKey = {r['server_key']}\nAllowedIPs = 0.0.0.0/0\n"
                        f"Endpoint = {r['server_ip']}:{r['server_port']}\n")
            last = r.get("status")
        except Exception as e:  # try the next server
            last = type(e).__name__
    raise RuntimeError(f"PIA addKey failed: {last}")


if __name__ == "__main__":
    c = make_conf(os.environ["PIA_USER"], os.environ["PIA_PASS"])
    print("config ok:", "Endpoint" in c, len(c))
