#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Naufal Habibi
"""Stop hook Claude Code untuk Laprak Studio (mode mandiri, studio.bat).

Saat agent di jendela Claude Code selesai bekerja, hook ini menunggu pesan dari kolom chat studio.
- Ada pesan  -> agent ditahan dan pesan itu diberikan sebagai instruksi berikutnya (decision: block).
- Tidak ada pesan sampai TUNGGU detik, atau studio mati -> agent berhenti seperti biasa.
Hanya aktif bila env LAPRAK_STUDIO=1 (di-set studio.py saat membuka jendela Claude Code),
jadi sesi Claude Code biasa di folder ini tidak terpengaruh. Tidak memakai token selama menunggu.
"""
import json, os, sys, time, urllib.request

TUNGGU = int(os.environ.get("LAPRAK_STUDIO_TUNGGU", "180"))   # detik
PORT = os.environ.get("LAPRAK_PORT", "8000")

def ambil():
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/antrean", timeout=3) as r:
            return json.loads(r.read().decode("utf8"))
    except OSError:
        return None          # studio mati

def main():
    if os.environ.get("LAPRAK_STUDIO") != "1": return
    try: sys.stdin.read()    # input hook tidak dipakai
    except Exception: pass
    batas = time.time() + TUNGGU
    while time.time() < batas:
        d = ambil()
        if d is None: return
        if d.get("pesan"):
            print(json.dumps({"decision": "block",
                              "reason": "Pesan baru dari pengguna lewat chat Laprak Studio (perlakukan seperti pesan pengguna biasa): "
                                        + d["pesan"]}, ensure_ascii=False))
            return
        time.sleep(1)

if __name__ == "__main__":
    main()
