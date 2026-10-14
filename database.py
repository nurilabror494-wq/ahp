"""
Modul Database SQLite untuk Sistem Pendukung Keputusan (SPK) AHP
Menyediakan struktur tabel sesuai rancangan:
1. users
2. decisions
3. criteria
4. alternatives
5. criteria_comparisons
6. alternative_comparisons
7. ahp_results
8. criteria_weights
9. alternative_scores
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "spk_ahp.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. users
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'pengguna',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 2. decisions (Multi-keputusan / Studi Kasus)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        nama_keputusan TEXT NOT NULL,
        tujuan TEXT NOT NULL,
        deskripsi TEXT,
        tanggal TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    """)

    # 3. criteria
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS criteria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        decision_id INTEGER NOT NULL,
        kode TEXT NOT NULL,
        nama TEXT NOT NULL,
        deskripsi TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (decision_id) REFERENCES decisions(id) ON DELETE CASCADE
    )
    """)

    # 4. alternatives
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alternatives (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        decision_id INTEGER NOT NULL,
        kode TEXT NOT NULL,
        nama TEXT NOT NULL,
        deskripsi TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (decision_id) REFERENCES decisions(id) ON DELETE CASCADE
    )
    """)

    # 5. criteria_comparisons
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS criteria_comparisons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        decision_id INTEGER NOT NULL,
        criteria_id_1 INTEGER NOT NULL,
        criteria_id_2 INTEGER NOT NULL,
        nilai REAL NOT NULL DEFAULT 1.0,
        FOREIGN KEY (decision_id) REFERENCES decisions(id) ON DELETE CASCADE,
        FOREIGN KEY (criteria_id_1) REFERENCES criteria(id) ON DELETE CASCADE,
        FOREIGN KEY (criteria_id_2) REFERENCES criteria(id) ON DELETE CASCADE,
        UNIQUE(decision_id, criteria_id_1, criteria_id_2)
    )
    """)

    # 6. alternative_comparisons
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alternative_comparisons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        decision_id INTEGER NOT NULL,
        criteria_id INTEGER NOT NULL,
        alternative_id_1 INTEGER NOT NULL,
        alternative_id_2 INTEGER NOT NULL,
        nilai REAL NOT NULL DEFAULT 1.0,
        FOREIGN KEY (decision_id) REFERENCES decisions(id) ON DELETE CASCADE,
        FOREIGN KEY (criteria_id) REFERENCES criteria(id) ON DELETE CASCADE,
        FOREIGN KEY (alternative_id_1) REFERENCES alternatives(id) ON DELETE CASCADE,
        FOREIGN KEY (alternative_id_2) REFERENCES alternatives(id) ON DELETE CASCADE,
        UNIQUE(decision_id, criteria_id, alternative_id_1, alternative_id_2)
    )
    """)

    # 7. ahp_results
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ahp_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        decision_id INTEGER NOT NULL,
        jenis TEXT NOT NULL, -- 'criteria' atau 'alternative_<criteria_id>'
        criteria_id INTEGER,
        lambda_max REAL,
        ci REAL,
        cr REAL,
        status TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (decision_id) REFERENCES decisions(id) ON DELETE CASCADE
    )
    """)

    # 8. criteria_weights
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS criteria_weights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        decision_id INTEGER NOT NULL,
        criteria_id INTEGER NOT NULL,
        bobot REAL NOT NULL DEFAULT 0.0,
        FOREIGN KEY (decision_id) REFERENCES decisions(id) ON DELETE CASCADE,
        FOREIGN KEY (criteria_id) REFERENCES criteria(id) ON DELETE CASCADE,
        UNIQUE(decision_id, criteria_id)
    )
    """)

    # 9. alternative_scores
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alternative_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        decision_id INTEGER NOT NULL,
        alternative_id INTEGER NOT NULL,
        skor_akhir REAL NOT NULL DEFAULT 0.0,
        ranking INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (decision_id) REFERENCES decisions(id) ON DELETE CASCADE,
        FOREIGN KEY (alternative_id) REFERENCES alternatives(id) ON DELETE CASCADE,
        UNIQUE(decision_id, alternative_id)
    )
    """)

    conn.commit()
    conn.close()

def seed_default_data():
    """Mengisi data awal pengguna dan studi kasus contoh (5 kriteria, 4 alternatif)."""
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Seed Users (Admin & User)
    cursor.execute("SELECT COUNT(*) as count FROM users")
    if cursor.fetchone()['count'] == 0:
        admin_pass = generate_password_hash("admin123")
        user_pass = generate_password_hash("user123")
        cursor.execute(
            "INSERT INTO users (nama, email, password, role) VALUES (?, ?, ?, ?)",
            ("Administrator AHP", "admin@ahp.com", admin_pass, "admin")
        )
        cursor.execute(
            "INSERT INTO users (nama, email, password, role) VALUES (?, ?, ?, ?)",
            ("Pengambil Keputusan (User)", "user@ahp.com", user_pass, "pengguna")
        )
        conn.commit()
        
    # 2. Seed Default Decision (Contoh materi: 5 Kriteria, 4 Alternatif)
    cursor.execute("SELECT COUNT(*) as count FROM decisions")
    if cursor.fetchone()['count'] == 0:
        admin = cursor.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1").fetchone()
        admin_id = admin['id'] if admin else 1
        
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT INTO decisions (user_id, nama_keputusan, tujuan, deskripsi, tanggal)
            VALUES (?, ?, ?, ?, ?)
        """, (
            admin_id,
            "Pemilihan Karyawan Terbaik",
            "Menentukan karyawan berprestasi dan terbaik periode tahun ini secara objektif menggunakan metode Analytical Hierarchy Process (AHP).",
            "Studi kasus implementasi SPK AHP untuk mengevaluasi kinerja karyawan pada 5 aspek kriteria utama.",
            today
        ))
        decision_id = cursor.lastrowid
        
        # 5 Kriteria
        kriteria_data = [
            ("C1", "Kriteria A (Prestasi Kerja)", "Pencapaian target KPI, kualitas dan kuantitas hasil kerja"),
            ("C2", "Kriteria B (Kedisiplinan)", "Ketepatan waktu, absensi, dan kepatuhan SOP perusahaan"),
            ("C3", "Kriteria C (Kerjasama Tim)", "Kemampuan berkolaborasi dan komunikasi dalam tim kerja"),
            ("C4", "Kriteria D (Loyalitas)", "Dedikasi, integritas, dan komitmen terhadap perusahaan"),
            ("C5", "Kriteria E (Inisiatif)", "Kemampuan proaktif mencari solusi dan inovasi ide kerja")
        ]
        crit_ids = []
        for kode, nama, desk in kriteria_data:
            cursor.execute("""
                INSERT INTO criteria (decision_id, kode, nama, deskripsi)
                VALUES (?, ?, ?, ?)
            """, (decision_id, kode, nama, desk))
            crit_ids.append(cursor.lastrowid)
            
        # 4 Alternatif
        alternatif_data = [
            ("A1", "Alternatif A", "Kandidat karyawan dengan integritas dan performa unggul"),
            ("A2", "Alternatif B", "Kandidat karyawan dengan kedisiplinan dan loyalitas tinggi"),
            ("A3", "Alternatif C", "Kandidat karyawan dengan kreativitas dan inisiatif tinggi"),
            ("A4", "Alternatif D", "Kandidat karyawan dengan kerjasama tim yang solid")
        ]
        alt_ids = []
        for kode, nama, desk in alternatif_data:
            cursor.execute("""
                INSERT INTO alternatives (decision_id, kode, nama, deskripsi)
                VALUES (?, ?, ?, ?)
            """, (decision_id, kode, nama, desk))
            alt_ids.append(cursor.lastrowid)
            
        # Perbandingan Kriteria (Menghasilkan proporsi bobot ~37%, ~21%, ~21%, ~12%, ~7% dengan CR << 0.10)
        # c0 vs c1: 2.0, c0 vs c2: 2.0, c0 vs c3: 3.0, c0 vs c4: 4.0
        # c1 vs c2: 1.0, c1 vs c3: 2.0, c1 vs c4: 3.0
        # c2 vs c3: 2.0, c2 vs c4: 3.0
        # c3 vs c4: 2.0
        crit_pairs = [
            (crit_ids[0], crit_ids[1], 2.0),
            (crit_ids[0], crit_ids[2], 2.0),
            (crit_ids[0], crit_ids[3], 3.0),
            (crit_ids[0], crit_ids[4], 4.0),
            (crit_ids[1], crit_ids[2], 1.0),
            (crit_ids[1], crit_ids[3], 2.0),
            (crit_ids[1], crit_ids[4], 3.0),
            (crit_ids[2], crit_ids[3], 2.0),
            (crit_ids[2], crit_ids[4], 3.0),
            (crit_ids[3], crit_ids[4], 2.0),
        ]
        for c1, c2, val in crit_pairs:
            cursor.execute("""
                INSERT INTO criteria_comparisons (decision_id, criteria_id_1, criteria_id_2, nilai)
                VALUES (?, ?, ?, ?)
            """, (decision_id, c1, c2, val))
            
        # Perbandingan Alternatif untuk masing-masing kriteria
        # Buat perbandingan realistis & konsisten sehingga Alternatif A unggul
        alt_pairs_per_crit = {
            crit_ids[0]: [  # Prestasi Kerja: A1 unggul
                (alt_ids[0], alt_ids[1], 3.0),
                (alt_ids[0], alt_ids[2], 4.0),
                (alt_ids[0], alt_ids[3], 5.0),
                (alt_ids[1], alt_ids[2], 2.0),
                (alt_ids[1], alt_ids[3], 3.0),
                (alt_ids[2], alt_ids[3], 2.0),
            ],
            crit_ids[1]: [  # Kedisiplinan: A2 sedikit unggul
                (alt_ids[0], alt_ids[1], 0.5),
                (alt_ids[0], alt_ids[2], 2.0),
                (alt_ids[0], alt_ids[3], 3.0),
                (alt_ids[1], alt_ids[2], 3.0),
                (alt_ids[1], alt_ids[3], 4.0),
                (alt_ids[2], alt_ids[3], 2.0),
            ],
            crit_ids[2]: [  # Kerjasama Tim: A1 dan A4 seimbang
                (alt_ids[0], alt_ids[1], 2.0),
                (alt_ids[0], alt_ids[2], 3.0),
                (alt_ids[0], alt_ids[3], 1.0),
                (alt_ids[1], alt_ids[2], 2.0),
                (alt_ids[1], alt_ids[3], 0.5),
                (alt_ids[2], alt_ids[3], 0.3333),
            ],
            crit_ids[3]: [  # Loyalitas: A1 unggul
                (alt_ids[0], alt_ids[1], 2.0),
                (alt_ids[0], alt_ids[2], 3.0),
                (alt_ids[0], alt_ids[3], 3.0),
                (alt_ids[1], alt_ids[2], 2.0),
                (alt_ids[1], alt_ids[3], 2.0),
                (alt_ids[2], alt_ids[3], 1.0),
            ],
            crit_ids[4]: [  # Inisiatif: A3 unggul
                (alt_ids[0], alt_ids[1], 2.0),
                (alt_ids[0], alt_ids[2], 0.5),
                (alt_ids[0], alt_ids[3], 2.0),
                (alt_ids[1], alt_ids[2], 0.3333),
                (alt_ids[1], alt_ids[3], 1.0),
                (alt_ids[2], alt_ids[3], 3.0),
            ]
        }
        
        for cid, pairs in alt_pairs_per_crit.items():
            for a1, a2, val in pairs:
                cursor.execute("""
                    INSERT INTO alternative_comparisons (decision_id, criteria_id, alternative_id_1, alternative_id_2, nilai)
                    VALUES (?, ?, ?, ?, ?)
                """, (decision_id, cid, a1, a2, val))

        conn.commit()

    conn.close()

if __name__ == "__main__":
    init_db()
    seed_default_data()
    print("Database SQLite spk_ahp.db berhasil diinisialisasi dan diisi data seed.")
