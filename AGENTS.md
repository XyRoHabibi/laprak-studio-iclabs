# AGENTS.md: Instruksi Pembuat Laprak Praktikum (PDF tulisan tangan)

> File ini adalah **instruksi untuk AI coding agent** (Claude Code, Codex CLI, Gemini CLI, Cursor, GitHub Copilot, dan agent lain
> yang bisa membaca file, menulis file, dan menjalankan perintah di folder ini). Dibuat untuk praktikum **FIKOM UMI (ICLabs)**.
> Tugas agent: membaca soal evaluasi praktikum (PDF), menulis jawabannya, lalu menghasilkan **satu file PDF**
> berisi **sampul + lembar jawaban bertulisan tangan rapi + watermark ICLabs + screenshot output**.
> Hasil dicetak tipis lalu ditimpa pulpen oleh pemilik laprak.

---

## 1. Cara memakai (perintah dari pengguna)

Pengguna cukup menulis satu baris:

```
pp 01 Oktober 2026
alpro 01 Oktober 2026
pp 01 Oktober 2026  catatan: tulisan hitam, jawaban soal 1 dibuat lebih singkat
```

| Bagian | Arti |
|---|---|
| kata pertama | kode mata kuliah = nama folder di `matkul/`: `pp` = Pengenalan Pemrograman, `alpro` = Algoritma Pemrograman (matkul lain bisa ditambahkan, bagian 2) |
| tanggal | tanggal yang dicetak di kanan atas sampul setelah "Makassar, ". Format akhir: `DD NamaBulan YYYY` (contoh `01 Oktober 2026`; rapikan `1 oktober 2026` → `01 Oktober 2026`). |
| `catatan:` (opsional) | Permintaan tambahan dari pengguna. **Catatan mengalahkan aturan default** di file ini (lihat bagian 9). |

Nomor evaluasi (I, II, III, …) **tidak diketik pengguna**: ambil dari PDF soal (tulisan "Evaluasi Praktikum N"),
lalu ubah ke **angka romawi** untuk sampul (1 → I, 2 → II, 3 → III, 4 → IV, …).

---

## 2. Struktur folder proyek

```
(folder proyek)/
├── AGENTS.md                ← file ini
├── identitas.json           ← data diri pengguna untuk sampul (salinan dari identitas.example.json)
├── config.json              ← perintah agent untuk tombol "Buat laprak" di studio
├── laprak/                  ← skrip: buat_laprak.py (PDF), buat_output.py (screenshot), buat_flowchart.py, potong_flowchart.py
├── studio/                  ← Laprak Studio: server.py, hook.py, web/
├── matkul/<kode>/           ← satu folder per mata kuliah: matkul.json, sampul.docx, ATURAN.md (opsional)
├── aset/                    ← fonts/PatrickHand-Regular.ttf (tulisan tangan), logo_iclabs.png (watermark)
├── contoh/                  ← contoh laprak untuk mencoba studio
└── kerja/                   ← folder kerja (tidak di-upload ke GitHub)
    ├── soal/                ← PDF soal evaluasi
    ├── kode/                ← file .cpp tiap soal yang butuh output (04.cpp, 05.cpp, ...), DIBUAT AGENT
    ├── output/              ← screenshot output (04.png, ...), dibuat otomatis lewat laprak/buat_output.py;
    │                          pengguna boleh menggantinya dengan screenshot asli (tidak ditimpa kecuali --force)
    ├── hasil/               ← PDF + isi_*.json versi kerja
    └── archive/             ← laprak yang SUDAH SELESAI, satu subfolder per laprak (bagian 3B)
```

Semua perintah dijalankan dari **folder proyek**. Path gambar di JSON (mis. `"output/04.png"`) **relatif terhadap `kerja/`**.

**Mata kuliah.** Kata pertama perintah pengguna = kode matkul = nama folder di `matkul/` (sekarang `pp` dan `alpro`).
Sampulnya `matkul/<kode>/sampul.docx`. Bila ada `matkul/<kode>/ATURAN.md`, **baca dan ikuti juga** (aturan khusus matkul itu
mengalahkan aturan umum di file ini, tetapi kalah dari `catatan:` pengguna). Bila pengguna menyebut matkul yang belum ada foldernya,
beri tahu pengguna dan jelaskan cara menambahkannya (lihat `matkul/README.md`); jangan mengarang sampul.

Kebutuhan: Python 3.10+ dan `pip install -r requirements.txt`; **Microsoft Word** (lewat `docx2pdf`) atau **LibreOffice** (`soffice`)
untuk mengubah sampul docx ke PDF; `g++` (MinGW/MSYS2) untuk screenshot output. Untuk melihat halaman PDF, render dengan PyMuPDF:
`fitz.open(pdf)[i].get_pixmap(dpi=70).save("cek.png")`. Jika `python` tidak menemukan paket, coba `py -3` atau Python lain yang punya paketnya.

---

## 3. Alur kerja (ikuti berurutan)

Laprak dikerjakan dalam **dua tahap**, karena screenshot output baru ada setelah jawaban/kode ada:

- **Tahap A — jawaban + kode + screenshot otomatis** (saat pengguna memberi perintah `pp ...`): agent menulis jawaban, membuat `kerja/kode/*.cpp`,
  lalu membuat screenshot output otomatis ke `kerja/output/` dan memasangnya di PDF. PDF yang dihasilkan sudah lengkap.
- **Tahap B — selesai** (saat pengguna bilang "selesai"/"arsipkan"; bila pengguna mengganti screenshot dengan yang asli, buat ulang PDF dulu):
  laprak dipindah ke `kerja/archive/` (bagian 3B).

### 3A. Tahap A

1. **Baca perintah pengguna** → tentukan `jenis` (pp/alpro), `tanggal`, dan `catatan`.
2. **Ambil PDF soal** dari `kerja/soal/` (kalau lebih dari satu, pakai yang paling baru diubah). Ekstrak teksnya **dan render halamannya jadi gambar**
   lalu lihat gambarnya: kode di dalam kotak (mis. kode yang harus diperbaiki) biasanya berupa gambar, dan huruf besar/kecil
   (mis. `Cout` vs `cout`) bisa hilang saat ekstraksi teks. **Gambar adalah sumber kebenaran.**
3. Tentukan **nomor evaluasi** (dari judul "Evaluasi Praktikum N") → angka romawi untuk sampul.
   Abaikan sub-judul yang bukan soal (mis. "Perhitungan Biaya Pencetakan Dokumen") dan header/footer modul.
4. **Baca data diri dari `identitas.json`**: `nama`, `stambuk` (NIM), dan per jenis praktikum `frekuensi`, `dosen`, `asisten1`, `asisten2`.
   `laprak/buat_laprak.py` mengisinya otomatis ke sampul. Pakai data ini juga untuk soal yang meminta identitas (mis. "tampilkan nama, NIM, kelas...").
   Jangan mengarang data. Bila `identitas.json` belum ada, minta pengguna menyalin `identitas.example.json` lalu mengisinya.
5. **Tulis jawaban** semua soal sesuai aturan bagian 4, simpan sebagai `kerja/hasil/isi_<jenis>_<N>.json` (format bagian 5).
   Pasang bagian `Output:` + `img` **hanya** pada soal yang menurut pengguna/soal memang memakai output (lihat `catatan:`; mis. "no. 1-3 tanpa output").
6. **Buat file kode + screenshot otomatis** (bagian 6): untuk setiap soal ber-output, tulis kodenya ke `kerja/kode/<NN>.cpp` (NN = nomor soal 2 digit),
   lalu jalankan `python laprak/buat_output.py` (mengompilasi, menjalankan, dan menggambar `kerja/output/<NN>.png` bergaya terminal gelap).
7. **Jalankan skrip**:
   ```
   python laprak/buat_laprak.py --json kerja/hasil/isi_pp_1.json --jenis pp --tanggal "01 Oktober 2026" --nomor 1 --out "kerja/hasil/Laprak_PP_Evaluasi_1.pdf"
   ```
   (`--ink 0.1` untuk tulisan hitam jika diminta catatan; default `0.85` = abu sangat tipis.
   Halo putih di sekeliling huruf aktif otomatis (`--halo 2.4`) supaya tulisan di atas watermark tetap terbaca saat dicetak mode Draft — lihat bagian 7.)
8. **Periksa hasil** dengan checklist bagian 8 (render ke PNG dan lihat). Perbaiki dan jalankan ulang jika ada yang salah.
9. **Laporkan singkat** ke pengguna: lokasi PDF, jumlah halaman, daftar `kerja/kode/*.cpp` dan `kerja/output/*.png` yang dibuat, dan asumsi yang dibuat.
   Beritahu bahwa pengguna boleh menjalankan kode sendiri dan mengganti screenshot dengan yang asli (nama sama), lalu minta "buat ulang".

### 3B. Tahap B (screenshot sudah ada → selesai → arsip)

1. Pastikan semua screenshot yang dibutuhkan ada di `kerja/output/` (cocokkan per soal; bagian 6). Jika ada yang kurang, buat dengan `laprak/buat_output.py`.
2. Jalankan ulang `laprak/buat_laprak.py` (perintah sama seperti Tahap A) → PDF final memakai screenshot terbaru. Periksa dengan checklist bagian 8.
3. Setelah pengguna puas / menyatakan selesai (atau PDF final lengkap tanpa kekurangan), **arsipkan**:
   buat `kerja/archive/<KODE MATKUL>_Evaluasi_<N>/` (mis. `ALPRO_Evaluasi_8`) lalu **pindahkan** ke dalamnya:
   - `Laprak_<JENIS>_Evaluasi_<N>.pdf` dan `isi_<jenis>_<N>.json` (dari `kerja/hasil/`)
   - folder `kerja/kode/` milik laprak itu (file `.cpp` yang tadi dibuat) dan screenshot-nya dari `kerja/output/` (di arsip menjadi subfolder `output/`)
   - PDF soal yang dipakai (dari `kerja/soal/`)
   Setelah dipindah, `kerja/kode/`, `kerja/output/`, `kerja/hasil/`, dan `kerja/soal/` di folder utama **kosong lagi** (siap untuk laprak berikutnya).
   Jangan menghapus apa pun; hanya memindahkan. Laporkan lokasi arsip ke pengguna.
4. Jika pengguna kemudian minta perbaikan laprak yang sudah diarsipkan, kerjakan dari salinan di `kerja/archive/` (kembalikan ke folder kerja bila perlu) dan arsipkan lagi.

---

## 4. Aturan isi jawaban

- Bahasa Indonesia sederhana ala mahasiswa; jawaban teori ringkas dan tepat (1–3 kalimat per poin). Gunakan poin `-` bila jawabannya beberapa butir
  (satu butir per istilah/konsep yang ditanyakan).
- **Salin teks soal apa adanya** dari PDF soal (nomor + kalimat soal). Soal berisi kode → salin kodenya sebagai blok `code`.
- Soal yang meminta program → tulis kode C++ lengkap (`#include`, `using namespace std;`, `main`, `return 0;`) dan **pasti bisa dikompilasi**.
  Indentasi per level = 1 unit (di JSON `[level, "teks"]`). Sertakan komentar jika diminta soal.
- Jika baris-baris `cout` berisi pasangan `label : isi`, sejajarkan titik duanya dengan penanda `|` (lihat contoh di bagian 5).
- Soal "perbaiki program": tampilkan kode salah di bagian soal (blok `code`), lalu `Jawab:` dengan kode yang benar.
- Soal yang meminta penjelasan setelah program (mis. "jelaskan apakah komentar memengaruhi…") → paragraf `Penjelasan: …` setelah output.
- Simbol `×`, `−`, `≥`, `•` ADA di font Patrick Hand: bila soal memakainya, salin apa adanya (jangan diganti `x`, `-`, `>=`).
- Hanya karakter yang ada di font: huruf, angka, tanda baca ASCII biasa. **Jangan** pakai emoji, simbol markdown (`**`, `` ` ``, `#` judul), tanda panah, atau
  tanda kutip melengkung; pakai `"` dan `'` biasa. Skrip akan memberi PERINGATAN jika ada karakter yang tidak didukung.
- Untuk **Alpro**: bila soal berupa algoritma/pseudocode, tulis sebagai blok `code` bergaya teks biasa.
- **Flowchart (Flowrun.io/Flowgorithm) → WAJIB dibuatkan** sebagai program FlowRun yang bisa di-paste: `kerja/hasil/flowchart_<NN>.flowrun`
  (JSON `Program` FlowRun: `id`, `name`, `config` dengan `"lang":"c++"`, `main` berisi statement ber-`"@type"` Begin/Declare/Input/Assign/If/Output/Return,
  `If` punya `trueBlock`/`falseBlock` tanpa `@type`; ekspresi pakai `==`, `!=`, `&&`, `||`; variabel harus di-Declare dulu).
  Pengguna menyalin isinya lalu klik *Paste* di flowrun.io (atau *Load* file .flowrun), lalu mengekspor flowchart (PNG) ke `kerja/output/`.
  **Jangan pasang flowchart utuh** (terlalu kecil saat dicetak): potong per bagian (`03a.png`, `03b.png`, …) dengan skala tampil ±0,5 pt per px
  asli (lebar maks. 13 cm), batas potong di sela node (jangan memotong diamond/kotak). **Tanpa judul/keterangan "Bagian"** —
  potongan langsung berurutan di bawah `Jawab:`, **tanpa bingkai dan tanpa latar putih**: potong dari PNG ekspor FlowRun yang
  latarnya sudah transparan (jangan diratakan ke putih) dan pasang dengan `{"t":"img","file":...,"transparent":true}`
  (skrip mempertahankan transparansi dan tidak menggambar bingkai, watermark tetap terlihat di belakangnya). Atur titik potong supaya sisa halaman terisi (potongan tinggi dibelah dua).
- **Algoritma/kode di dalam kotak gambar pada soal** (mis. "Perhatikan algoritma berikut") → JANGAN ditulis tangan; ambil gambarnya dari PDF soal
  (`extract_image`, lebar ±700 px) ke `kerja/output/algo_q<N>.png` dan pasang sebagai `img` (dicetak). Kode jawaban/perbaikan tetap ditulis tangan.
- **Soal tracing / "lengkapi tabel"** → jawab HANYA dengan tabel terisi, tanpa paragraf perhitungan di bawahnya.
- **Soal dengan sub-butir a., b., c. …** → tulis berselang: sub-soal a lalu `Jawab:` a, sub-soal b lalu `Jawab:` b, dst.
  (bukan semua sub-soal dulu baru semua jawaban). Sub-soal: `para` dengan `bullet` "a."; jawaban: `para` `"lvl":1` diawali "Jawab: ".
- Bila "Hasil/Luaran yang Dikumpulkan" meminta **File program Dev C++**, soal yang meminta beberapa versi algoritma (mis. "buat dua versi
  algoritma") dijawab dengan **program C++** per versi (`kerja/kode/07a.cpp`, `07b.cpp` + `.in` untuk input) beserta `Output:` screenshot.
- Jangan menambah soal atau bagian yang tidak ada di PDF soal.
- **Soal yang meminta "minimal N" (mis. "minimal dua kesalahan", "minimal 3 level") → jawab PERSIS N saja, jangan lebih.**
  Tujuan: pemilik laprak menulis tangan ulang, jadi jawaban sependek mungkin yang tetap memenuhi syarat. Berlaku untuk semua jenis soal
  (jumlah poin, contoh, kesalahan, level, dll.). Kalau soal menyebut daftar item yang wajib ("minimal modul: a-f"), semua item daftar itu tetap dijawab.
- **Deskripsi kasus di PDF soal ikut ditulis.** Bila di bawah judul "Evaluasi Praktikum N" ada teks sebelum "Soal Evaluasi"
  (judul kasus, paragraf deskripsi, "Ketentuan sistem:" beserta butirnya), salin semuanya apa adanya ke bagian `intro` di JSON
  (rata kiri sejajar judul, butir pakai `•`, rumus/simbol disalin PERSIS seperti di soal: `×`, `−`, `≥`, `<`; rumus di bawah butir ditulis
  sebagai `para` TERPISAH tanpa `bullet`, sehingga rata kiri penuh (sejajar "Ketentuan sistem:", TIDAK menjorok seperti teks butir)), lalu tulis label **"Soal Evaluasi"**
  (dengan `"gap": true`), baru soal-soal bernomor. Urutan di halaman: judul -> deskripsi kasus -> "Soal Evaluasi" -> soal 1, 2, ...
  Jangan menulis bagian "Hasil/Luaran yang Dikumpulkan" dan "Aturan Penilaian" (bukan soal). Jika PDF tidak punya deskripsi kasus
  (langsung soal), `intro` dikosongkan/dihilangkan.
- **Data/tabel yang ada di soal → salin sebagai tabel** (bagian `table` di JSON), bukan diubah jadi kalimat. Contoh: "Data | Nilai" pada soal tracing.
  Pecah soal: teks soal, lalu `table`, lalu kalimat lanjutan ("Tentukan: ..."), baru label `Jawab:`.
- **Hierarchy chart / struktur modul** → pakai bagian `tree` (gaya modul: nama akar di kiri, garis cabang `├──`/`└──`, sub-item bertingkat),
  bukan teks `+--`. Nama node ditulis dengan spasi seperti di modul ("Input Pelanggan", "Hitung Biaya"), bukan nama fungsi.
  Cara mengerjakan soal Alpro yang mirip contoh di modul (Level 3 modular, hierarchy chart, pseudocode) sebaiknya mengikuti gaya contoh di halaman modul.

---

## 5. Format `kerja/hasil/isi_<jenis>_<N>.json`

```json
{
  "title": "Evaluasi Praktikum 1",
  "sampul": {"jenis": "pp", "nomor": 1, "tanggal": "01 Oktober 2026"},
  "questions": [
    {
      "num": "1.",
      "text": "Jelaskan fungsi ... pada program C++ sederhana.",
      "parts": [
        {"t": "label", "text": "Jawab:"},
        {"t": "para", "bullet": "-", "text": "cout : singkatan dari 'character output' ..."}
      ]
    },
    {
      "num": "4.",
      "text": "Modifikasi program Hello World agar menampilkan nama, NIM, ...",
      "parts": [
        {"t": "label", "text": "Jawab:"},
        {"t": "code", "lines": [
          [0, "#include <iostream>"],
          [0, "using namespace std;"],
          [0, ""],
          [0, "int main() {"],
          [1, "// Identitas mahasiswa"],
          [1, "cout << \"Nama|: Nama Mahasiswa\" << endl;"],
          [1, "cout << \"NIM|: 130202600XX\" << endl;"],
          [1, "return 0;"],
          [0, "}"]
        ]},
        {"t": "label", "text": "Output:"},
        {"t": "img", "file": "output/04.png"}
      ]
    }
  ]
}
```

Jenis `parts`: `label` (teks "Jawab:" / "Output:"), `para` (paragraf, opsional `bullet`, opsional `"lvl": 1` = menjorok satu tingkat, untuk sub-butir), `code` (daftar `[level, "teks"]`;
`|` = titik sejajar kolom), `img` (path screenshot **relatif terhadap folder proyek**),
`table` (`{"t":"table","widths":[0.3,0.4],"header":["Data","Nilai"],"rows":[["ID","P001"],...]}`; `widths` = pecahan dari lebar area tulis 14 cm,
jumlah boleh < 1; kolom yang berisi nama panjang seperti `TampilkanTransaksi` butuh >= 0.27; baris tidak dipotong antar halaman, header diulang),
`tree` (`{"t":"tree","nodes":[[0,"Akar"],[1,"Anak"],[2,"Cucu"],[1,"Anak 2"]]}` urut DFS, kedalaman 0 = akar; garis cabang digambar otomatis).
Kunci opsional `"intro": [ ... ]` di tingkat atas JSON (sejajar `title` dan `questions`) berisi deskripsi kasus: daftar `label` (rata kiri, `"gap": true` memberi jarak
sebelumnya) dan `para` (opsional `bullet`), contoh: `{"t":"label","text":"Soal Evaluasi","gap":true}` sebagai penutup intro.
Bagian `table`/`tree` boleh diletakkan sebelum `Jawab:` bila merupakan bagian soal (mis. tabel data soal). Soal boleh berisi beberapa blok `code`
(mis. kode soal lalu kode jawaban). Teks soal boleh memakai `\n` untuk baris baru.

---

## 6. File kode otomatis dan aturan screenshot output

**File kode (dibuat agent):**
- Setiap soal yang meminta program ber-output → `kerja/kode/<NN>.cpp` (NN = nomor soal 2 digit: `04.cpp`). Isinya **identik** dengan blok kode di jawaban JSON
  (tanpa penanda `|`). Jika satu soal punya beberapa program, pakai `04a.cpp`, `04b.cpp` (screenshot: `04a.png`, `04b.png`).
- Jangan menambah `#include` yang tidak perlu (mis. `<string>` tidak perlu karena `<iostream>` sudah cukup dan program tetap jalan).
  Hanya sertakan header yang memang dibutuhkan agar program terkompilasi.
- Agent wajib memastikan tiap file **terkompilasi dan keluarannya sesuai penjelasan** di jawaban. Di Windows/MSYS, bila `g++` di Bash gagal diam-diam,
  jalankan lewat PowerShell dengan path penuh `C:\msys64\ucrt64\bin\g++.exe`. Hasil `.exe` jangan disimpan di `kerja/kode/`.

**Screenshot otomatis (`laprak/buat_output.py`):**
- `python laprak/buat_output.py` → untuk tiap `kerja/kode/*.cpp`: kompilasi, jalankan, lalu gambar keluarannya ke `kerja/output/<NN>.png` dengan tampilan terminal VS Code gelap
  (latar #24262D, titik biru, panah merah muda, perintah `./NN.exe` kuning, teks abu, font Cascadia Mono 31 px, jarak baris 41 px) — meniru contoh `kerja/output/04.png`.
- Opsi: `python laprak/buat_output.py 05 07` (hanya kode tertentu), `--force` (timpa yang sudah ada). Tanpa `--force`, screenshot yang sudah ada **tidak ditimpa**,
  jadi screenshot asli buatan pengguna aman.
- Program yang butuh input (`cin`) tidak bisa otomatis: beri tahu pengguna agar menjalankan sendiri dan men-screenshot-nya (nama `NN.png`).

**Screenshot (aturan umum):**
- Screenshot ada di `kerja/output/`. Cocokkan ke soal lewat **awalan nomor** nama file (`03.png`, `04_apa_saja.png`) atau, jika nama file acak,
  lewat nama program di bagian atas screenshot terminal (mis. `./03_Selamat_Datang_Praktikum.exe` → soal 3).
- Pasang screenshot **setelah kode jawaban**, di bawah label `Output:`, hanya untuk soal yang menjalankan program.
- Screenshot harus **tampil solid/opak** (tidak transparan, tidak tertutup watermark): skrip sudah menggambar gambar di atas watermark
  dan meratakan transparansinya. Jangan mengubah isi screenshot.
- Jika screenshot suatu soal **tidak ada**, jangan mengarang/membuat output palsu: lanjutkan tanpa gambar (skrip hanya memberi PERINGATAN, tidak error).
  Normalnya buat dulu dengan `laprak/buat_output.py`; hanya program ber-input (`cin`) yang perlu diminta ke pengguna. Jangan arsipkan bila masih ada yang kurang.

---

## 7. Spesifikasi tampilan PDF (sudah diimplementasikan skrip — jangan diubah kecuali catatan meminta)

| Hal | Aturan |
|---|---|
| Kertas | A4 |
| Margin **4433** | kiri **4 cm**, atas **4 cm**, kanan **3 cm**, bawah **3 cm** — semua isi **dan watermark** berada di dalam area margin |
| Sampul | halaman 1, dari `matkul/<kode>/sampul.docx` (diubah ke PDF). Kiri atas: `Tugas Evaluasi Praktikum <ROMAWI>`; kanan atas: `Makassar, <tanggal>`. Bagian lain sampul tidak diubah |
| Judul isi | "Evaluasi Praktikum N" (ikut nomor di PDF soal), di bagian atas halaman isi pertama |
| Font | Patrick Hand (tulisan tangan, **tegak**, rapi). Teks 14 pt, baris 18,5 pt; kode 13,5 pt, baris 16,5 pt |
| Warna tulisan | abu **sangat tipis** (`--ink 0.85`) agar tidak terlihat setelah ditimpa pulpen. Jika catatan minta "hitam": `--ink 0.1` |
| Halo tulisan | **Setiap tulisan diberi garis tepi putih** (`--halo 2.4` pt, default) sebelum diisi warna tinta, sehingga watermark di sekeliling huruf "terhapus" tipis. Alasannya: laprak biasa dicetak dengan **print quality Draft** (hemat tinta); tanpa halo, tulisan abu tipis yang jatuh di atas bagian hijau/toska logo ICLabs lebur dengan watermark dan tidak terbaca saat akan ditimpa pulpen. **Jangan dimatikan** kecuali catatan meminta (`--halo 0`). Jika masih kurang jelas, naikkan ke `--halo 3.5` |
| Jarak | **rapat**: antar baris/paragraf/kode kecil; antar soal sedikit lebih longgar (13 pt) |
| "Jawab:" dan "Output:" | **tanpa garis bawah** |
| Watermark | `logo_iclabs.png`, transparansi ±13 %, **di tengah area margin**, lebar = lebar area tulis (14 cm), di setiap halaman isi (sampul tidak diberi watermark tambahan) |
| Screenshot | lebar = ukuran asli × 0,4, rata kiri sejajar teks jawaban, bingkai tipis abu, opak di atas watermark |
| Pemenggalan halaman | **Tulisan harus memenuhi area margin sampai dasar (3 cm dari bawah); pindah halaman HANYA bila baris berikutnya benar-benar tidak muat.** Tidak ada aturan "judul/label tidak boleh sendirian" lagi: soal, label, paragraf, kode, node `tree` dan baris tabel dipenggal per baris/per node. Pengecualian yang tidak bisa dipotong: satu baris tabel (header diulang di halaman baru; header + baris pertama harus muat) dan gambar/screenshot. Pemilik laprak menulis tangan, jadi ruang kosong di dalam margin = kertas terbuang |
| Nomor halaman | tidak ada |

---

## 8. Checklist pemeriksaan sebelum menyerahkan

Render semua halaman (`pdftoppm -r 60 -png file.pdf cek`) dan **lihat gambarnya**:

- [ ] Sampul: angka romawi benar di kiri atas, tanggal benar di kanan atas, jenis praktikum (PP/ALPRO) sesuai.
- [ ] Semua soal 1…N ada, urut, teks soal sama dengan PDF soal (termasuk kode di soal).
- [ ] Tidak ada teks keluar dari area margin 4433; watermark berada di dalam area margin dan di tengah.
- [ ] Tulisan yang berada di atas logo watermark tetap terbaca: garis/warna logo terputus di sekeliling huruf (halo putih). Perbesar (zoom) bagian tengah halaman untuk memastikan.
- [ ] Tidak ada garis bawah pada "Jawab:" / "Output:".
- [ ] Screenshot solid (tidak transparan), tidak terpotong, sesuai nomor soal.
- [ ] Tidak ada ruang kosong di dasar halaman (di dalam margin) selain yang tak terhindarkan karena satu baris tabel atau gambar tidak muat; laporkan ke pengguna bila ada.
- [ ] Cek tiap halaman: baris terakhir teks berada tepat di dekat batas bawah margin (render `fitz` dan lihat), bukan berhenti jauh di atasnya.
- [ ] Kode benar secara sintaks; titik dua `|` sejajar; tidak ada PERINGATAN karakter.

---

## 9. Catatan dari pengguna (override)

Contoh catatan yang harus dipahami agent:

| Catatan | Tindakan |
|---|---|
| "tulisan hitam" / "tidak usah tipis" | `--ink 0.1` |
| "no. X-Y tidak ada output" | jangan beri `Output:`/`img` dan jangan buat `kerja/kode/*.cpp` untuk soal itu |
| "tanpa sampul" | tambahkan `--tanpa-sampul` |
| "tanpa watermark" | pakai logo transparan kosong / hapus pemanggilan watermark di skrip |
| "tulisan di logo tidak kelihatan" / "halo lebih tebal" | `--halo 3.5` (atau lebih); "tanpa halo" → `--halo 0` |
| "jawaban lebih singkat/panjang" | sesuaikan isi JSON |
| "tulis ulang soal X saja" | ubah bagian itu di JSON lalu jalankan ulang skrip |
| "cetak hanya halaman/nomor tertentu" | buat PDF terpisah dari halaman yang diminta (mis. `pypdf`), **jangan** mengubah pemenggalan halaman lain tanpa diminta, karena pengguna mungkin sudah menulis di kertas hasil cetak sebelumnya |

Jika pengguna sudah mencetak/menulis di versi sebelumnya dan meminta perbaikan, **pertahankan halaman yang sudah terpakai tetap identik**
(bandingkan gambar halaman lama vs baru) dan hanya ubah halaman yang diminta.

---

## 10. Hasil akhir

- File: `kerja/hasil/Laprak_<PP|ALPRO>_Evaluasi_<N>.pdf` (halaman 1 = sampul, halaman berikutnya = lembar jawaban).
- Simpan juga `kerja/hasil/isi_<jenis>_<N>.json` agar mudah diedit dan dibuat ulang.
- Setelah selesai (Tahap B), semuanya dipindah ke `kerja/archive/<PP|ALPRO>_Evaluasi_<N>/` (bagian 3B).
- Balasan ke pengguna singkat: nama file, jumlah halaman, catatan/asumsi, dan (Tahap A) daftar kode dan screenshot yang dibuat.

---

## 11. Skrip

Semua skrip sudah ada di repositori (`laprak/buat_laprak.py`, `laprak/buat_output.py`, `laprak/buat_flowchart.py`, `laprak/potong_flowchart.py`, `studio/server.py`).
Pakai skrip itu apa adanya; jangan menulis ulang dari nol. Bila perlu mengubah perilaku, ubah skripnya lalu jelaskan ke pengguna.

---

## 12. Laprak Studio (tampilan live di browser)

`studio/server.py` + `studio/web/` = tampilan web lokal: log langkah agent + halaman laprak yang "dibangun" kawanan kursor
(tata letaknya direkam dari `laprak/buat_laprak.py` yang sama, jadi persis seperti PDF).

### 12A. Cara kerja normal: pengguna memberi perintah di chat agent, studio menjadi penonton

Agentnya tetap kamu (sesi agent ini). Studio hanya menampilkan. Langkahnya:

1. **Awal tugas** (sebelum membaca soal): nyalakan studio **di latar belakang** (proses tidak boleh menahan kamu menunggu):
   ```
   python studio/server.py --viewer
   ```
   Browser pengguna terbuka sendiri ke http://localhost:8000. Jika studio sudah jalan, perintah ini hanya membuka browser.
2. **Setiap langkah penting**, kirim satu baris log (singkat, bahasa Indonesia), **digabung dengan perintah Bash yang memang akan dijalankan**
   (`python studio/server.py log "..."; <perintah>`), jangan sebagai langkah tersendiri — supaya tidak menambah putaran/token:
   ```
   python studio/server.py log "membaca soal: 5 soal, Evaluasi Praktikum 8"
   python studio/server.py log "menulis jawaban soal 3" 
   python studio/server.py log "Soal no. 4 butuh input cin — menunggu jawaban pengguna di chat" warn
   ```
   Jenis opsional di argumen ke-3: `tool` (default), `say`, `done`, `warn`, `build`. Jika studio tidak jalan, perintah ini diam saja.
3. **Tulis `kerja/hasil/isi_<jenis>_<N>.json` sebelum menjalankan `laprak/buat_laprak.py`**, dan sertakan field
   `"sampul": {"jenis": "alpro", "nomor": 8, "tanggal": "26 November 2026"}` di JSON (diabaikan `laprak/buat_laprak.py`,
   dipakai studio untuk membangun sampul langsung dari `matkul/<kode>/sampul.docx`). Setiap kali JSON ditulis/diubah, studio otomatis
   membangun halamannya (hanya halaman yang berubah). Saat PDF di `kerja/hasil/` jadi, studio otomatis menampilkan "PDF asli".
4. **Akhir tugas** (PDF jadi dan checklist bagian 8 selesai, atau tugas dihentikan): matikan studio:
   ```
   python studio/server.py stop
   ```
   Tab browser menampilkan "Laprak selesai" + lokasi PDF. Bila menunggu jawaban pengguna (mis. input `cin`), studio **jangan** dimatikan dulu.
5. Jika catatan pengguna berkata "tanpa studio", atau kamu tidak bisa menjalankan proses di latar belakang, lewati semua langkah di atas.

### 12B. Mode mandiri: `studio.bat` (form di browser, lalu jendela agent terbuka)

Pengguna klik dua kali `studio.bat` → studio menyala dan browser terbuka. Di form (jenis, tanggal, PDF soal, catatan) pengguna klik
**Buat laprak** → studio membuka **jendela agent interaktif** (perintahnya diatur di `config.json`, default Claude Code) di folder ini
dengan perintah laprak sudah terisi. Izin, pertanyaan, dan revisi dilakukan pengguna di jendela itu.

Agent yang dibuka dari mode ini (prompt-nya menyebut "Laprak Studio … bagian 12B"):
- Studio SUDAH menyala: **jangan** jalankan `studio.py --viewer` dan **jangan** `studio.py stop` (pengguna menutup studio sendiri).
- Tetap kirim log tiap langkah (`python studio/server.py log "..."`, python mana pun boleh) dan tulis JSON sebelum `laprak/buat_laprak.py` seperti 12A.
- Kirim log hemat: hanya di tahap penting (±6–10 kali per laprak: baca soal, tiap kelompok jawaban, kode+screenshot, render PDF, selesai).
  **Hemat token: jangan jadikan log langkah tersendiri** — gabungkan dengan perintah Bash yang memang dijalankan, mis.
  `python studio/server.py log "compile & screenshot soal 1-5"; python laprak/buat_output.py` atau
  `python studio/server.py log "render PDF"; python laprak/buat_laprak.py ...`. Setiap panggilan alat tambahan = satu putaran ekstra yang membaca ulang seluruh konteks.
- **Chat revisi dari studio (khusus Claude Code)**: `studio/hook.py` (Stop hook di `.claude/settings.json`, aktif hanya bila env `LAPRAK_STUDIO=1` yang di-set studio)
  menunggu sampai 3 menit setiap kali kamu selesai bekerja. Pesan yang diketik pengguna di chat studio datang sebagai
  "Pesan baru dari pengguna lewat chat Laprak Studio: …" — **perlakukan persis seperti pesan pengguna biasa** (kerjakan revisinya, kirim log, tulis ulang JSON/PDF).
  Pengguna juga tetap bisa mengetik langsung di jendela Claude Code setelah waktu tunggu habis.

Fitur "Putar ulang laprak lama" memutar animasi dari JSON di `kerja/archive/` dan `contoh/` tanpa agent.
