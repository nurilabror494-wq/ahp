# 📊 Sistem Pendukung Keputusan (SPK) Berbasis Web - Metode Analytical Hierarchy Process (AHP)

Aplikasi web Sistem Pendukung Keputusan (SPK) menggunakan metode **Analytical Hierarchy Process (AHP)** yang dirancang sesuai dengan standar akademik untuk keperluan kuliah, praktikum, maupun tugas akhir/skripsi.

---

## 🚀 Fitur Aplikasi Berdasarkan Modul

### 1. Dashboard Utama
- **Overview Statistik:** Total Kriteria, Total Alternatif, Status Konsistensi (Konsisten/Tidak Konsisten), dan Alternatif Terbaik (#1).
- **Visualisasi Bobot Kriteria:** Grafik Donut & Bar Chart interaktif menggunakan Chart.js lengkap dengan persentase.
- **Visualisasi Perangkingan:** Grafik batang skor akhir seluruh alternatif.
- **Stepper Alur AHP:** Panduan visual interaktif 7 langkah proses pengambilan keputusan AHP.

### 2. Manajemen Kriteria
- CRUD (Tambah, Edit, Hapus) kriteria penilaian.
- Pengaturan kode kriteria (misal: $C_1, C_2, \dots$), nama, dan deskripsi/indikator penilaian.
- Penyesuaian otomatis perbandingan berpasangan saat kriteria ditambah atau dihapus.

### 3. Manajemen Alternatif
- CRUD (Tambah, Edit, Hapus) pilihan kandidat/alternatif (karyawan, produk, lokasi, beasiswa, vendor, dll).
- Informasi skor akhir dan perolehan ranking terkini.

### 4. Struktur Hierarki AHP
- Diagram pohon hierarki visual 3 level dekomposisi masalah:
  - **Level 1:** Fokus / Tujuan Keputusan (*Goal*).
  - **Level 2:** Kriteria Penilaian beserta bobot prioritasnya.
  - **Level 3:** Alternatif Pilihan beserta ranking dan skor akhirnya.

### 5. Perbandingan Berpasangan (*Pairwise Comparison*)
- **Perbandingan Kriteria:** Form input pasangan kriteria menggunakan **Skala Fundamental Saaty (1–9)**.
- **Perbandingan Alternatif:** Evaluasi perbandingan berpasangan alternatif untuk setiap kriteria.
- **Validasi Nilai Resiprokal Otomatis:** Memenuhi kaidah $a_{ji} = 1 / a_{ij}$ dan diagonal $a_{ii} = 1$.
- **Preview Matriks:** Matriks $n \times n$ diperbarui secara *real-time*.

### 6. Proses Perhitungan AHP & Uji Konsistensi
- **Matriks Awal ($A$):** Penjumlahan setiap kolom ($\sum_{i=1}^n a_{ij}$).
- **Normalisasi Matriks ($R$):** $r_{ij} = \frac{a_{ij}}{\sum a_{ij}}$.
- **Bobot Prioritas ($W$):** Rata-rata baris matriks normalisasi ($w_i = \frac{1}{n} \sum_{j=1}^n r_{ij}$).
- **Eigenvalue Maksimum ($\lambda_{\max}$):** Perkalian matriks awal dengan bobot $A \times W$ dibagi bobot.
- **Consistency Index ($CI$):**
  $$CI = \frac{\lambda_{\max} - n}{n - 1}$$
- **Random Index Saaty ($RI$):** Nilai standar indeks acak Saaty ($n=1$ s.d. $15$).
- **Consistency Ratio ($CR$):**
  $$CR = \frac{CI}{RI}$$
- **Evaluasi Konsistensi:** Status **KONSISTEN** jika $CR \le 0.10$ ($10\%$). Jika tidak, sistem memberikan peringatan untuk evaluasi perbandingan.

### 7. Hasil Perangkingan & Sintesis Akhir
- Perkalian matriks bobot lokal alternatif terhadap bobot kriteria.
- Peringkat akhir alternatif (Rank 1, 2, 3, ...).
- Highlight rekomendasi alternatif terbaik dengan lencana trofi emas.
- Matriks rincian kontribusi masing-masing kriteria terhadap skor akhir setiap alternatif.

### 8. Laporan & Ekspor Dokumen
- **Cetak / PDF:** Halaman format resmi A4 lengkap dengan Kop Surat, informasi keputusan, matriks bobot, tabel konsistensi, dan kolom tanda tangan pengesahan pimpinan.
- **Ekspor Excel (.xlsx):** File spreadsheet multi-sheet terstruktur rapi dibuat otomatis menggunakan `openpyxl`.
- **Ekspor CSV:** File data ringkasan hasil ranking.

### 9. Fitur Multi-Keputusan & Manajemen Pengguna
- **Multi-Studi Kasus:** Pengguna dapat membuat, beralih, dan mengelola banyak studi kasus keputusan yang berbeda dalam satu sistem.
- **Manajemen Akun & Role:**
  - **Administrator:** Akses penuh mengelola data kriteria, alternatif, perbandingan, dan manajemen user.
  - **Pengguna:** Evaluator/viewer yang dapat meninjau analisis, grafik, dan mengekspor laporan.

---

## 🗄️ Struktur Database SQLite (`spk_ahp.db`)

Sesuai rancangan relasional pada materi:

| Tabel | Kolom Utama |
|---|---|
| `users` | `id, nama, email, password, role, created_at` |
| `decisions` | `id, user_id, nama_keputusan, tujuan, deskripsi, tanggal, created_at, updated_at` |
| `criteria` | `id, decision_id, kode, nama, deskripsi, created_at` |
| `alternatives` | `id, decision_id, kode, nama, deskripsi, created_at` |
| `criteria_comparisons` | `id, decision_id, criteria_id_1, criteria_id_2, nilai` |
| `alternative_comparisons` | `id, decision_id, criteria_id, alternative_id_1, alternative_id_2, nilai` |
| `ahp_results` | `id, decision_id, jenis, criteria_id, lambda_max, ci, cr, status, updated_at` |
| `criteria_weights` | `id, decision_id, criteria_id, bobot` |
| `alternative_scores` | `id, decision_id, alternative_id, skor_akhir, ranking` |

---

## 💻 Cara Menjalankan Aplikasi

### Cara 1: Menggunakan File Batch (Paling Praktis di Windows)
Cukup **klik dua kali (double-click)** pada file:
```
run.bat
```

### Cara 2: Melalui Terminal / Command Prompt / PowerShell
1. Buka terminal pada folder proyek:
   ```bash
   cd "c:\Users\Administrator\Downloads\projek ahp"
   ```
2. Jalankan aplikasi dengan perintah:
   ```bash
   python app.py
   ```
3. Buka browser dan akses alamat:
   ```
   http://127.0.0.1:5000
   ```

---

## 🔑 Akun Login Bawaan

| Role | Email | Password | Hak Akses |
|---|---|---|---|
| **Administrator** | `admin@ahp.com` | `admin123` | Akses Penuh (Kelola Master Data, Kasus, User) |
| **Pengguna** | `user@ahp.com` | `user123` | Viewer & Evaluator (Hasil, Perhitungan, Laporan) |

---

## 📐 Tabel Nilai Random Index Saaty ($RI$)

| Ukuran Matriks ($n$) | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Nilai $RI$** | 0.00 | 0.00 | 0.58 | 0.90 | 1.12 | 1.24 | 1.32 | 1.41 | 1.45 | 1.49 | 1.51 | 1.54 | 1.56 | 1.57 | 1.59 |
