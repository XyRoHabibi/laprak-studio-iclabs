# Mata kuliah

Setiap subfolder di sini adalah satu mata kuliah praktikum. Nama folder = **kode matkul**, yaitu kata pertama perintah laprak
(`pp 01 Oktober 2026`, `alpro 26 November 2026`).

```
matkul/
└── <kode>/
    ├── matkul.json   nama matkul untuk tampilan studio
    ├── sampul.docx   template sampul
    └── ATURAN.md     (opsional) aturan khusus matkul ini untuk agent
```

## Menambah mata kuliah baru

1. Buat folder baru, misalnya `matkul/basisdata/`.
2. Salin `sampul.docx` dari matkul lain, lalu ubah nama praktikumnya di Word (mis. `PRAKTIKUM BASIS DATA`).
   Biarkan baris pertama tetap berformat `Tugas Evaluasi Praktikum I ... Makassar, 01 Oktober 2026` dan baris identitas tetap
   berlabel `Nama`, `Stambuk`, `Frekuensi`, `Dosen`, `Asisten 1`, `Asisten 2`, karena bagian itu diisi otomatis.
3. Buat `matkul.json`:

   ```json
   { "kode": "basisdata", "nama": "Basis Data", "singkat": "BD" }
   ```

4. Tambahkan data kelasmu di `identitas.json`:

   ```json
   "basisdata": { "frekuensi": "TI_BD-X (AX)", "dosen": "...", "asisten1": "...", "asisten2": "..." }
   ```

5. (Opsional) Tulis `ATURAN.md` bila matkul itu punya aturan jawaban sendiri, misalnya bahasa pemrograman yang dipakai
   (SQL, Java, Python), format query, atau cara menyalin diagram. Agent membacanya bersama `AGENTS.md`.

Matkul baru langsung muncul di form Laprak Studio dan bisa dipakai di chat: `basisdata 03 Desember 2026`.

Catatan: pembuat screenshot output (`laprak/buat_output.py`) saat ini khusus program C++. Untuk bahasa lain, sementara tulis di
`ATURAN.md` agar agent meminta screenshot asli dari pengguna.
