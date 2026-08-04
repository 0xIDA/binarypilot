# BinaryPilot CTF Sandbox — strix-sandbox base + CTF toolchain layer.
#
# Base image carries Kali + the full web pentest/proxy stack (nmap, sqlmap,
# nuclei, ffuf, katana, agent-browser, caido, semgrep, trufflehog, trivy, etc).
# We only add what CTF playbooks actually call into: reverse/pwn/forensics/
# crypto/hashing. Web tooling is inherited as-is.

FROM ghcr.io/usestrix/strix-sandbox:1.2.0

LABEL description="BinaryPilot CTF Solver Sandbox — strix-sandbox + CTF toolchain"

USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        # reverse / pwn
        radare2 \
        gdb-multiarch \
        qemu-user \
        qemu-user-static \
        binwalk \
        upx-ucl \
        # forensics
        foremost \
        steghide \
        exiftool \
        pngcheck \
        tshark \
        p7zip-full \
        unrar-free \
        # crypto / hashing
        john \
        hashcat \
        hashid \
        # misc
        socat \
        ruby-full \
    && gem install --no-document zsteg one_gadget \
    && apt-get install -y --no-install-recommends wordlists seclists \
    && gunzip -c /usr/share/wordlists/rockyou.txt.gz > /usr/share/wordlists/rockyou.txt 2>/dev/null \
        || curl -fsSL https://github.com/brannondorsey/naive-hashcat/raw/master/rockyou.txt -o /usr/share/wordlists/rockyou.txt \
    && chmod 0644 /usr/share/wordlists/rockyou.txt \
    && apt-get autoremove -y \
    && apt-get autoclean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Python CTF libs into the same venv the base image's PATH puts first.
USER pentester
RUN /app/.venv/bin/pip install --no-cache-dir \
    pwntools \
    ropper \
    ROPgadget \
    checksec.py \
    pycryptodome \
    sympy \
    z3-solver \
    r2pipe

USER pentester
WORKDIR /workspace
