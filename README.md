# Laprak Studio

Pembuat **laporan praktikum (laprak) bertulisan tangan** untuk mahasiswa
[FIKOM Universitas Muslim Indonesia](https://fikom.umi.ac.id/) di lingkungan [ICLabs](https://iclabs.fikom.umi.ac.id/),
dikerjakan oleh AI coding agent.

Kamu cukup menaruh PDF soal evaluasi lalu menulis satu baris perintah, misalnya `alpro 26 November 2026`. Agent membaca soal, menulis
jawaban, membuat kode beserta screenshot output, lalu menghasilkan **satu PDF**: sampul FIKOM UMI + lembar jawaban berhuruf tulisan
tangan abu-abu tipis + watermark ICLabs. PDF itu dicetak, lalu tulisannya kamu timpa dengan pulpen.

Proses pembuatannya bisa ditonton di **Laprak Studio**: kanvas di browser tempat kawanan kursor "membangun" halaman laprak
(mengetik jawaban, menggambar tabel, menaruh logo dan screenshot) mengikuti pekerjaan agent.

> **Status: masih dikembangkan.** Saat ini mendukung praktikum **Pengenalan Pemrograman (PP)** dan **Algoritma Pemrograman (Alpro)**.
> Mata kuliah lain sedang menyusul, dan kamu bisa menambahkannya sendiri (lihat [Menambah mata kuliah](#menambah-mata-kuliah)).

## Fitur

- Sampul otomatis dari template Pedoman ICLabs 2025 (nomor romawi, tanggal, identitas dari `identitas.json`).
- Lembar jawaban font tulisan tangan (Patrick Hand), margin 4-4-3-3, watermark ICLabs, tanpa ruang kosong yang membuang kertas.
- Tulisan diberi **halo putih** supaya tetap terbaca di atas watermark walau dicetak mode Draft (hemat tinta).
- Kode C++ dikompilasi dan dijalankan otomatis, keluarannya digambar sebagai screenshot terminal.
- Tabel tracing, hierarchy chart, flowchart (FlowRun), dan deskripsi kasus dari soal.
- **Laprak Studio**: kanvas live di browser (penggaris, kursor multiplayer, daftar halaman, log agent, sampul, PDF akhir).
- Satu instruksi untuk banyak agent lewat `AGENTS.md`.
- Bisa dijalankan lewat **Docker** tanpa memasang Python, LibreOffice, dan g++ di komputer.

## Agent yang didukung

Project ini tidak terikat ke satu AI. Agent apa pun yang bisa membaca file, menulis file, dan menjalankan perintah di folder ini
bisa dipakai, karena semua aturan ada di `AGENTS.md` dan semua pekerjaan dilakukan skrip Python biasa.

| Agent | Memuat instruksi | Tombol "Buat laprak" di studio | Chat revisi dari studio |
|---|---|---|---|
| Claude Code | otomatis (`CLAUDE.md` mengimpor `AGENTS.md`) | ya (default) | ya |
| Codex CLI | otomatis (`AGENTS.md`) | ya, atur `config.json` | tidak, revisi di jendela agent |
| Gemini CLI | atur `contextFileName` ke `AGENTS.md`, atau awali perintah "baca AGENTS.md" | ya, atur `config.json` | tidak |
| Cursor, GitHub Copilot, agent lain | `AGENTS.md` / awali perintah "baca dan ikuti AGENTS.md" | tidak (pakai dari chat) | tidak |

## Kebutuhan

Tanpa Docker:

- Windows 10/11 (macOS/Linux kemungkinan jalan, belum diuji)
- Python 3.10 atau lebih baru
- Microsoft Word (sampul .docx ke PDF lewat `docx2pdf`) atau LibreOffice
- `g++` dari MinGW/MSYS2 (screenshot output program C++)
- Salah satu AI coding agent

Dengan Docker: cukup [Docker Desktop](https://www.docker.com/products/docker-desktop/) dan agent.

## Instalasi

```bash
git clone https://github.com/XyRoHabibi/laprak-studio-iclabs.git
cd laprak-studio-iclabs
pip install -r requirements.txt
copy identitas.example.json identitas.json
```

Buka `identitas.json`, isi nama, stambuk, serta frekuensi, dosen, dan asisten tiap mata kuliah. File ini tidak ikut ter-upload
ke GitHub (ada di `.gitignore`).

## Cara pakai

### Lewat chat agent (cara utama)

1. Taruh PDF soal evaluasi di `kerja/soal/`.
2. Buka agent di folder proyek, lalu ketik:

   ```
   pp 01 Oktober 2026
   alpro 26 November 2026
   alpro 26 November 2026  catatan: tulisan hitam, no. 1-2 tanpa output
   ```

   Kata pertama = kode mata kuliah (nama folder di `matkul/`), lalu tanggal untuk sampul. `catatan:` opsional.
3. Agent menyalakan Laprak Studio di browser supaya kamu bisa menonton halamannya dibangun.
4. Hasil: `kerja/hasil/Laprak_<KODE>_Evaluasi_<N>.pdf`. Bilang "selesai" atau "arsipkan" supaya laprak dipindah ke `kerja/archive/`.

### Lewat Laprak Studio

Klik dua kali `studio.bat` (atau `python studio/server.py --buka`). Browser terbuka ke `http://localhost:8000`.
Isi form, lalu klik **Buat laprak**: studio membuka jendela agent dengan perintah yang sudah terisi.

Agent yang dibuka diatur di `config.json`; `{prompt}` diganti otomatis dengan perintah laprak:

```json
{ "agent": { "nama": "Claude Code", "perintah": ["claude", "{prompt}"] } }
{ "agent": { "nama": "Codex CLI",   "perintah": ["codex", "{prompt}"] } }
{ "agent": { "nama": "Gemini CLI",  "perintah": ["gemini", "-i", "{prompt}"] } }
```

**Putar ulang laprak lama** memutar animasi dari laprak yang sudah jadi (`kerja/archive/` dan `contoh/`) tanpa menjalankan agent.

### Lewat Docker

```bash
copy identitas.example.json identitas.json      # lalu isi
docker compose up -d                             # studio di http://localhost:8000
docker compose exec studio bash                  # terminal di dalam container
```

Di terminal container, jalankan agentmu lalu ketik perintah laprak seperti biasa. Untuk memasang CLI agent di dalam container:

```bash
docker compose build --build-arg AGENT_NPM=@anthropic-ai/claude-code    # atau @openai/codex, @google/gemini-cli
```

Folder proyek di-mount ke container, jadi `kerja/` dan PDF hasil tetap ada di komputermu. Di Docker, sampul diubah ke PDF dengan
LibreOffice; tampilannya bisa sedikit berbeda dari hasil Microsoft Word.

## Menambah mata kuliah

Setiap mata kuliah adalah satu folder `matkul/<kode>/` berisi `matkul.json`, `sampul.docx`, dan `ATURAN.md` (opsional).
Langkah lengkapnya ada di [matkul/README.md](matkul/README.md). Kontribusi template matkul lain sangat diterima.

## Tips mencetak

- Tulisan sengaja abu-abu sangat tipis supaya tidak terlihat setelah ditimpa pulpen. Untuk tulisan hitam: `catatan: tulisan hitam`.
- Aman dicetak dengan **print quality Draft**: tulisan di atas watermark tetap terbaca karena ada halo putih.
  Bila masih samar: `catatan: halo lebih tebal`.

## Struktur folder

```
laprak-studio-iclabs/
├── AGENTS.md            instruksi lengkap untuk agent (CLAUDE.md mengimpor file ini)
├── config.json          agent yang dibuka tombol "Buat laprak"
├── identitas.example.json
├── studio.bat           buka Laprak Studio (Windows)
├── Dockerfile, docker-compose.yml
├── laprak/              buat_laprak.py (PDF), buat_output.py (screenshot), buat_flowchart.py, potong_flowchart.py
├── studio/              server.py (server lokal), hook.py (chat revisi Claude Code), web/ (tampilan)
├── matkul/              satu folder per mata kuliah: matkul.json, sampul.docx, ATURAN.md
├── aset/                font tulisan tangan dan logo watermark
├── contoh/              contoh laprak untuk mencoba studio
├── licenses/            lisensi font dan ikon
└── kerja/               soal/, kode/, output/, hasil/, archive/ (tidak di-upload)
```

## Gunakan dengan bertanggung jawab

Project ini membantu menyusun dan merapikan laprak. Pahami jawaban dan kode yang dihasilkan sebelum dikumpulkan, karena kamu yang
akan ditanya asisten saat asistensi. Ikuti aturan praktikum dan kebijakan akademik yang berlaku.

## Lisensi

- Kode program: [MIT](LICENSE), Copyright (c) 2026 Naufal Habibi.
- Font [Patrick Hand](licenses/PatrickHand-OFL.txt) dan [Geist](licenses/Geist-OFL.txt): SIL Open Font License 1.1.
- Ikon [Phosphor](licenses/Phosphor-MIT.txt): MIT.
- **Logo ICLabs (`aset/logo_iclabs.png`) dan logo Universitas Muslim Indonesia pada template sampul adalah milik pemiliknya
  masing-masing dan tidak termasuk dalam lisensi MIT.** Keduanya disertakan agar laprak sesuai format praktikum FIKOM UMI.
  Project ini tidak berafiliasi resmi dengan UMI maupun ICLabs.
