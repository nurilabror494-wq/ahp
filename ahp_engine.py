"""
Modul Perhitungan Analytical Hierarchy Process (AHP)
Mengimplementasikan logika matematis AHP Thomas L. Saaty:
- Matriks Perbandingan Berpasangan (Pairwise Comparison)
- Normalisasi Matriks
- Bobot Prioritas (Vektor Eigen)
- Lambda Max (Eigenvalue Maksimum)
- Consistency Index (CI)
- Random Index (RI)
- Consistency Ratio (CR) dan Evaluasi Konsistensi (CR <= 0.10)
- Sintesis Akhir dan Perangkingan Alternatif
"""

import numpy as np

# Tabel Random Index (RI) standar Saaty untuk n = 1 sampai 15
RI_TABLE = {
    1: 0.00,
    2: 0.00,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49,
    11: 1.51,
    12: 1.54,
    13: 1.56,
    14: 1.57,
    15: 1.59
}

SAATY_SCALE = [
    {"value": 1, "label": "1 - Sama Penting (Equal)", "desc": "Kedua elemen mempunyai pengaruh yang sama"},
    {"value": 2, "label": "2 - Mendekati Sedikit Lebih Penting", "desc": "Nilai-nilai antara dua pertimbangan yang berdekatan"},
    {"value": 3, "label": "3 - Sedikit Lebih Penting (Moderate)", "desc": "Pengalaman dan penilaian sedikit memihak satu elemen"},
    {"value": 4, "label": "4 - Mendekati Lebih Penting", "desc": "Nilai-nilai antara dua pertimbangan yang berdekatan"},
    {"value": 5, "label": "5 - Lebih Penting (Strong)", "desc": "Pengalaman dan penilaian sangat memihak satu elemen"},
    {"value": 6, "label": "6 - Mendekati Sangat Penting", "desc": "Nilai-nilai antara dua pertimbangan yang berdekatan"},
    {"value": 7, "label": "7 - Sangat Penting (Very Strong)", "desc": "Satu elemen sangat disukai dan praktis dominan"},
    {"value": 8, "label": "8 - Mendekati Mutlak", "desc": "Nilai-nilai antara dua pertimbangan yang berdekatan"},
    {"value": 9, "label": "9 - Mutlak Lebih Penting (Extreme)", "desc": "Bukti yang memihak satu elemen memiliki tingkat penegasan tertinggi"}
]

def get_ri(n: int) -> float:
    """Mengembalikan nilai Random Index untuk ukuran matriks n."""
    if n in RI_TABLE:
        return RI_TABLE[n]
    elif n > 15:
        # Estimasi rumus Golden & Wang untuk n > 15
        return 1.98 * (n - 2) / n
    return 0.00

def calculate_pairwise_ahp(items: list, comparisons_dict: dict) -> dict:
    """
    Menghitung AHP untuk sekumpulan item (kriteria atau alternatif).
    items: list of dicts [{'id': 1, 'kode': 'C1', 'nama': '...'}, ...]
    comparisons_dict: dict {(id1, id2): float_value}
    """
    n = len(items)
    if n == 0:
        return {
            "matrix": [],
            "col_sums": [],
            "norm_matrix": [],
            "weights": {},
            "weights_list": [],
            "lambda_max": 0.0,
            "ci": 0.0,
            "ri": 0.0,
            "cr": 0.0,
            "is_consistent": True,
            "status": "Tidak ada data",
            "items": []
        }

    id_to_idx = {item['id']: i for i, item in enumerate(items)}
    
    # Inisialisasi matriks n x n dengan 1.0 pada diagonal
    matrix = np.ones((n, n), dtype=float)
    
    # Isi matriks perbandingan
    for i in range(n):
        for j in range(n):
            if i == j:
                matrix[i][j] = 1.0
            else:
                id_i = items[i]['id']
                id_j = items[j]['id']
                
                # Cek jika ada nilai tersimpan untuk (id_i, id_j)
                if (id_i, id_j) in comparisons_dict:
                    val = float(comparisons_dict[(id_i, id_j)])
                    matrix[i][j] = val
                    matrix[j][i] = 1.0 / val if val != 0 else 1.0
                elif (id_j, id_i) in comparisons_dict:
                    val = float(comparisons_dict[(id_j, id_i)])
                    matrix[j][i] = val
                    matrix[i][j] = 1.0 / val if val != 0 else 1.0
                elif i < j:
                    # Default jika belum diisi: 1.0
                    matrix[i][j] = 1.0
                    matrix[j][i] = 1.0

    # 1. Hitung Jumlah Kolom
    col_sums = matrix.sum(axis=0)
    # Hindari pembagian dengan nol
    col_sums_safe = np.where(col_sums == 0, 1.0, col_sums)
    
    # 2. Normalisasi Matriks (tiap elemen dibagi jumlah kolomnya)
    norm_matrix = matrix / col_sums_safe
    
    # 3. Bobot Prioritas (Vektor Eigen): Rata-rata setiap baris
    weights = norm_matrix.mean(axis=1)
    
    # 4. Nilai Eigen Maksimum (Lambda Max)
    # Kalikan matriks awal A dengan vektor bobot W
    weighted_sum = matrix @ weights
    # Rasio per baris: (A * W)_i / W_i
    weights_safe = np.where(weights == 0, 1e-9, weights)
    t_vector = weighted_sum / weights_safe
    lambda_max = float(np.mean(t_vector))
    
    # 5. Consistency Index (CI)
    if n > 1:
        ci = float((lambda_max - n) / (n - 1))
    else:
        ci = 0.0
    # Tangani pembulatan floating point yang sangat kecil negatif
    if ci < 0:
        ci = 0.0

    # 6. Random Index (RI)
    ri = get_ri(n)
    
    # 7. Consistency Ratio (CR)
    if ri > 0:
        cr = float(ci / ri)
    else:
        cr = 0.0
        
    is_consistent = (cr <= 0.10) or (n <= 2)
    status = "Konsisten" if is_consistent else "Tidak Konsisten"
    
    weights_dict = {items[i]['id']: float(weights[i]) for i in range(n)}
    weights_list = [
        {
            "id": items[i]['id'],
            "kode": items[i].get('kode', f'I{i+1}'),
            "nama": items[i].get('nama', ''),
            "bobot": float(weights[i]),
            "persentase": round(float(weights[i]) * 100, 2)
        }
        for i in range(n)
    ]
    
    return {
        "matrix": matrix.tolist(),
        "col_sums": col_sums.tolist(),
        "norm_matrix": norm_matrix.tolist(),
        "weights": weights_dict,
        "weights_list": weights_list,
        "weighted_sum": weighted_sum.tolist(),
        "ratio_vector": t_vector.tolist(),
        "lambda_max": round(lambda_max, 4),
        "ci": round(ci, 4),
        "ri": round(ri, 2),
        "cr": round(cr, 4),
        "cr_percentage": round(cr * 100, 2),
        "is_consistent": is_consistent,
        "status": status,
        "n": n,
        "items": items
    }

def calculate_synthesis_rankings(criteria: list, alternatives: list, criteria_weights: dict, alt_weights_per_criteria: dict) -> list:
    """
    Menghitung skor akhir setiap alternatif dan mengurutkannya ke dalam ranking.
    Skor Akhir = Sum(Bobot Kriteria_j * Bobot Alternatif_ij)
    """
    if not alternatives or not criteria:
        return []
        
    scores = []
    for alt in alternatives:
        alt_id = alt['id']
        total_score = 0.0
        breakdown = {}
        
        for crit in criteria:
            crit_id = crit['id']
            crit_weight = criteria_weights.get(crit_id, 0.0)
            
            # Bobot alternatif terhadap kriteria ini
            crit_alt_dict = alt_weights_per_criteria.get(crit_id, {})
            alt_local_weight = crit_alt_dict.get(alt_id, 0.0)
            
            contribution = crit_weight * alt_local_weight
            total_score += contribution
            
            breakdown[crit_id] = {
                "local_weight": round(alt_local_weight, 4),
                "crit_weight": round(crit_weight, 4),
                "contribution": round(contribution, 4)
            }
            
        scores.append({
            "id": alt_id,
            "kode": alt.get('kode', ''),
            "nama": alt.get('nama', ''),
            "deskripsi": alt.get('deskripsi', ''),
            "skor_akhir": round(total_score, 4),
            "breakdown": breakdown
        })
        
    # Urutkan berdasarkan skor akhir tertinggi ke terendah
    scores.sort(key=lambda x: x['skor_akhir'], reverse=True)
    
    # Berikan ranking
    for idx, item in enumerate(scores):
        item['ranking'] = idx + 1
        
    return scores
