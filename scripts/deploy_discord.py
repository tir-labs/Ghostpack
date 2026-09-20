#!/usr/bin/env python3
"""Interactive SSH deployment of the Ghostpack Discord development stack to Ubuntu 24.04.
Install locally: python -m pip install paramiko
Run: python scripts/deploy_discord.py --host YOUR_BOT_VPS_IP
No password, bot token or server secret is written to GitHub or printed.
"""
import argparse
import getpass
import io
import ipaddress
import os
import secrets
import shlex
import sys
import time
from pathlib import Path

try:
    import paramiko
except ImportError:
    sys.exit("Install the SSH client first: python -m pip install paramiko")

REPO="https://github.com/tir-labs/Ghostpack.git"
REMOTE="/opt/ghostpack"
REQUIRED={
    "DISCORD_TOKEN":"Discord bot token",
    "DISCORD_GUILD_ID":"Discord server (guild) ID",
    "DISCORD_MANAGEMENT_CHANNEL_ID":"Management channel ID",
    "DISCORD_REPORTING_CHANNEL_ID":"Reporting channel ID",
    "DISCORD_QUEUE_CHANNEL_ID":"Editor queue channel ID",
    "EDITOR_ROLE_ID":"Editor role ID",
}
def run(ssh,command,*,sudo=False,timeout=900):
    if sudo:
        command="sudo -n bash -lc "+shlex.quote(command)
    print("Running remote setup step...")
    _,out,err=ssh.exec_command(command,timeout=timeout,get_pty=False)
    code=out.channel.recv_exit_status()
    stdout=out.read().decode(errors="replace")
    stderr=err.read().decode(errors="replace")
    if code:
        raise RuntimeError("Remote step failed (exit "+str(code)+"):\n"+(stderr or stdout)[-2500:])
    return stdout
def known_host(ssh,host,port):
    key=ssh.get_transport().get_remote_server_key()
    fingerprint=":".join(f"{b:02x}" for b in __import__("hashlib").sha256(key.asbytes()).digest())
    print("Server SSH key SHA256 fingerprint (hex):",fingerprint)
    response=input("Compare this fingerprint with your VPS provider's console. Type TRUST to continue: ")
    if response!="TRUST": raise RuntimeError("Server host key was not approved")
    # Only trust this connection after explicit fingerprint verification; never AutoAddPolicy.
def collect():
    config={}
    for name,description in REQUIRED.items():
        value=getpass.getpass(description+" (hidden): ") if name=="DISCORD_TOKEN" else input(description+": ").strip()
        if not value: raise ValueError(name+" is required")
        if name.endswith("_ID") and not value.isdecimal(): raise ValueError(name+" must be a numeric Discord ID")
        config[name]=value
    config["LIVE_TOKEN"]=secrets.token_urlsafe(48)
    config["MEDIA_TOKEN"]=secrets.token_urlsafe(48)
    return config
def deploy(ssh,config,*,skip_install=False):
    if not skip_install:
        run(ssh,"export DEBIAN_FRONTEND=noninteractive; apt-get update && apt-get install -y git ca-certificates docker.io docker-compose-v2",sudo=True,timeout=1800)
        run(ssh,"systemctl enable --now docker",sudo=True)
    run(ssh,"docker compose version && git --version",sudo=True)
    run(ssh,"mkdir -p /opt && if [ -d /opt/ghostpack/.git ]; then git -C /opt/ghostpack fetch origin main && git -C /opt/ghostpack checkout main && git -C /opt/ghostpack pull --ff-only origin main; else git clone --branch main "+shlex.quote(REPO)+" /opt/ghostpack; fi",sudo=True,timeout=300)
    env="\n".join(k+"="+v for k,v in config.items())+"\n"
    # Stream environment via stdin, not via shell command arguments or process list.
    command="sudo -n sh -c 'umask 077; cat > /opt/ghostpack/.env; chmod 600 /opt/ghostpack/.env'"
    stdin,out,err=ssh.exec_command(command,timeout=30)
    stdin.write(env)
    stdin.channel.shutdown_write()
    status=out.channel.recv_exit_status()
    if status: raise RuntimeError("Could not write remote environment: "+err.read().decode(errors="replace")[-500:])
    run(ssh,"mkdir -p /opt/ghostpack/discord-attachments && chmod 700 /opt/ghostpack/discord-attachments",sudo=True)
    run(ssh,"cd /opt/ghostpack && docker compose --profile discord up -d --build live bot",sudo=True,timeout=1800)
def test(ssh):
    checks=[
        ("Live unit tests","cd /opt/ghostpack && docker compose run --rm --no-deps live python -m unittest discover -s tests -v"),
        ("Bot Python syntax","cd /opt/ghostpack && docker compose run --rm --no-deps bot python -m compileall -q /app"),
        ("Live API health","cd /opt/ghostpack && docker compose exec -T live python -c 'import urllib.request; assert urllib.request.urlopen(\"http://127.0.0.1:8090/health\",timeout=10).status == 200'"),
        ("Bot running","cd /opt/ghostpack && test \"$(docker compose ps --status running --services bot)\" = bot"),
    ]
    failed=[]
    for label,command in checks:
        try:
            result=run(ssh,command,sudo=True,timeout=240)
            print("PASS:",label)
        except Exception as exc:
            failed.append(label)
            print("FAIL:",label,str(exc)[-1000:])
    return failed
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host",required=True,help="Discord bot VPS IP or hostname")
    parser.add_argument("--port",type=int,default=22)
    parser.add_argument("--user",default="root")
    parser.add_argument("--key",help="SSH private key file (recommended)")
    parser.add_argument("--skip-install",action="store_true",help="Docker and Git already installed")
    args=parser.parse_args()
    print("Ghostpack Discord DEVELOPMENT deployment; not production-ready. Do not enter credentials in chat.")
    password=None if args.key else getpass.getpass("Temporary VPS SSH password (hidden): ")
    ssh=paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
    # First contact uses a transport to inspect the key before authenticating.
    import socket
    sock=socket.create_connection((args.host,args.port),timeout=20)
    transport=paramiko.Transport(sock)
    try:
        transport.start_client(timeout=20)
        key=transport.get_remote_server_key()
        digest=__import__("hashlib").sha256(key.asbytes()).digest()
        fingerprint=__import__("base64").b64encode(digest).decode().rstrip("=")
        print("SSH host key fingerprint: SHA256:"+fingerprint)
        if input("Verify against VPS provider console; type TRUST to proceed: ")!="TRUST":
            raise RuntimeError("SSH host key not approved")
        if args.key:
            sshkey=paramiko.RSAKey.from_private_key_file(args.key)
            transport.auth_publickey(args.user,sshkey)
        else:
            transport.auth_password(args.user,password)
        ssh._transport=transport
        config=collect()
        deploy(ssh,config,skip_install=args.skip_install)
        failures=test(ssh)
        print("Deployment finished. Automated checks:", "FAILED: "+", ".join(failures) if failures else "PASSED")
        print("Discord gateway login and slash-command permissions require a real Discord integration test.")
        if failures: sys.exit(1)
    finally:
        ssh.close()
if __name__=="__main__":main()
