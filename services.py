"""
Modul Layanan (Services) SPK AHP
Mengintegrasikan database dan engine AHP:
- Sinkronisasi data perbandingan
- Eksekusi perhitungan otomatis
- Penyimpanan bobot kriteria, hasil AHP, dan skor perangkingan
- Generator Ekspor Excel (OpenPyXL)
"""

import io
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from database import get_db
from ahp_engine import calculate_pairwise_ahp, calculate_synthesis_rankings

def get_active_decision_id(conn, session):
    """Mendapatkan decision_id aktif dari session, atau mengambil keputusan pertama."""
    dec_id = session.get('active_decision_id')
    cursor = conn.cursor()
    if dec_id:
        exists = cursor.execute("SELECT id FROM decisions WHERE id = ?", (dec_id,)).fetchone()
        if exists:
            return dec_id
            
    first_dec = cursor.execute("SELECT id FROM decisions ORDER BY id ASC LIMIT 1").fetchone()
    if first_dec:
        session['active_decision_id'] = first_dec['id']
        return first_dec['id']
    return None

def get_decision_details(conn, decision_id):
    """Mendapatkan detail keputusan."""
    if not decision_id:
        return None
    cursor = conn.cursor()
    return cursor.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,)).fetchone()

def execute_ahp_calculation(conn, decision_id):
    """
    Menjalankan seluruh pipeline perhitungan AHP untuk sebuah keputusan:
    1. Kriteria: Matriks -> Bobot -> Konsistensi -> Simpan ke DB
    2. Alternatif per Kriteria: Matriks -> Bobot Lokal -> Konsistensi -> Simpan ke DB
    3. Sintesis: Perkalian Bobot -> Skor Akhir & Ranking -> Simpan ke DB
    """
    cursor = conn.cursor()
    
    # 1. Ambil Kriteria
    criteria_rows = cursor.execute(
        "SELECT * FROM criteria WHERE decision_id = ? ORDER BY id ASC", 
        (decision_id,)
    ).fetchall()
    criteria = [dict(c) for c in criteria_rows]
    
    # 2. Ambil Alternatif
    alt_rows = cursor.execute(
        "SELECT * FROM alternatives WHERE decision_id = ? ORDER BY id ASC", 
        (decision_id,)
    ).fetchall()
    alternatives = [dict(a) for a in alt_rows]
    
    if not criteria or not alternatives:
        return {
            "criteria": criteria,
            "alternatives": alternatives,
            "criteria_ahp": None,
            "alt_ahp_by_criteria": {},
            "final_rankings": [],
            "best_alternative": None,
            "overall_consistent": False
        }

    # 3. Hitung AHP Kriteria
    crit_comps = cursor.execute(
        "SELECT criteria_id_1, criteria_id_2, nilai FROM criteria_comparisons WHERE decision_id = ?",
        (decision_id,)
    ).fetchall()
    crit_comp_dict = {(c['criteria_id_1'], c['criteria_id_2']): c['nilai'] for c in crit_comps}
    
    criteria_ahp = calculate_pairwise_ahp(criteria, crit_comp_dict)
    
    # Simpan bobot kriteria ke database (tabel criteria_weights & criteria)
    for c_id, w in criteria_ahp['weights'].items():
        cursor.execute("""
            INSERT INTO criteria_weights (decision_id, criteria_id, bobot)
            VALUES (?, ?, ?)
            ON CONFLICT(decision_id, criteria_id) DO UPDATE SET bobot = excluded.bobot
        """, (decision_id, c_id, w))
        
    # Simpan hasil AHP kriteria ke ahp_results
    cursor.execute("""
        INSERT INTO ahp_results (decision_id, jenis, criteria_id, lambda_max, ci, cr, status, updated_at)
        VALUES (?, 'criteria', NULL, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (decision_id, criteria_ahp['lambda_max'], criteria_ahp['ci'], criteria_ahp['cr'], criteria_ahp['status']))

    # 4. Hitung AHP Alternatif untuk setiap Kriteria
    alt_ahp_by_criteria = {}
    alt_weights_per_criteria = {}
    all_alt_consistent = True
    
    for crit in criteria:
        cid = crit['id']
        alt_comps = cursor.execute(
            "SELECT alternative_id_1, alternative_id_2, nilai FROM alternative_comparisons WHERE decision_id = ? AND criteria_id = ?",
            (decision_id, cid)
        ).fetchall()
        alt_comp_dict = {(ac['alternative_id_1'], ac['alternative_id_2']): ac['nilai'] for ac in alt_comps}
        
        alt_res = calculate_pairwise_ahp(alternatives, alt_comp_dict)
        alt_ahp_by_criteria[cid] = alt_res
        alt_weights_per_criteria[cid] = alt_res['weights']
        
        if not alt_res['is_consistent']:
            all_alt_consistent = False
            
        cursor.execute("""
            INSERT INTO ahp_results (decision_id, jenis, criteria_id, lambda_max, ci, cr, status, updated_at)
            VALUES (?, 'alternative', ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (decision_id, cid, alt_res['lambda_max'], alt_res['ci'], alt_res['cr'], alt_res['status']))

    # 5. Sintesis Akhir dan Perangkingan
    final_rankings = calculate_synthesis_rankings(
        criteria, 
        alternatives, 
        criteria_ahp['weights'], 
        alt_weights_per_criteria
    )
    
    # Simpan ke tabel alternative_scores
    for r in final_rankings:
        cursor.execute("""
            INSERT INTO alternative_scores (decision_id, alternative_id, skor_akhir, ranking)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(decision_id, alternative_id) DO UPDATE SET 
                skor_akhir = excluded.skor_akhir,
                ranking = excluded.ranking
        """, (decision_id, r['id'], r['skor_akhir'], r['ranking']))

    conn.commit()
    
    best_alternative = final_rankings[0] if final_rankings else None
    overall_consistent = criteria_ahp['is_consistent'] and all_alt_consistent
    
    return {
        "criteria": criteria,
        "alternatives": alternatives,
        "criteria_ahp": criteria_ahp,
        "alt_ahp_by_criteria": alt_ahp_by_criteria,
        "final_rankings": final_rankings,
        "best_alternative": best_alternative,
        "overall_consistent": overall_consistent
    }

def generate_excel_report(conn, decision_id):
    """Menghasilkan file Excel (.xlsx) komprehensif berisi seluruh data dan perhitungan AHP."""
    wb = openpyxl.Workbook()
    
    decision = get_decision_details(conn, decision_id)
    calc_data = execute_ahp_calculation(conn, decision_id)
    
    # Font dan Style
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid") # Dark Blue
    sub_fill = PatternFill(start_color="3B82F6", end_color="3B82F6", fill_type="solid") # Blue
    accent_fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid") # Light Blue
    success_fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid") # Light Green
    
    title_font = Font(name="Arial", size=14, bold=True, color="1E3A8A")
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    bold_font = Font(name="Arial", size=10, bold=True)
    regular_font = Font(name="Arial", size=10)
    
    thin_border = Border(
        left=Side(style='thin', color='D1D5DB'),
        right=Side(style='thin', color='D1D5DB'),
        top=Side(style='thin', color='D1D5DB'),
        bottom=Side(style='thin', color='D1D5DB')
    )
    
    # ================= SHEET 1: RINGKASAN & PERANGKINGAN =================
    ws1 = wb.active
    ws1.title = "Hasil Perangkingan"
    ws1.views.sheetView[0].showGridLines = True
    
    # Title
    ws1["A1"] = "LAPORAN HASIL SISTEM PENDUKUNG KEPUTUSAN METODE AHP"
    ws1["A1"].font = title_font
    ws1["A2"] = f"Studi Kasus: {decision['nama_keputusan'] if decision else '-'}"
    ws1["A2"].font = bold_font
    ws1["A3"] = f"Tujuan: {decision['tujuan'] if decision else '-'}"
    ws1["A3"].font = regular_font
    ws1["A4"] = f"Tanggal: {decision['tanggal'] if decision else datetime.now().strftime('%Y-%m-%d')}"
    ws1["A4"].font = regular_font
    
    # Status Konsistensi
    ws1["A6"] = "Status Konsistensi Kriteria:"
    ws1["A6"].font = bold_font
    cr_stat = calc_data['criteria_ahp']['status'] if calc_data['criteria_ahp'] else '-'
    cr_val = calc_data['criteria_ahp']['cr'] if calc_data['criteria_ahp'] else 0
    ws1["C6"] = f"{cr_stat} (CR = {cr_val})"
    ws1["C6"].font = bold_font
    
    ws1["A7"] = "Rekomendasi Terbaik (#1):"
    ws1["A7"].font = bold_font
    best_name = f"{calc_data['best_alternative']['kode']} - {calc_data['best_alternative']['nama']}" if calc_data['best_alternative'] else '-'
    ws1["C7"] = best_name
    ws1["C7"].font = Font(name="Arial", size=11, bold=True, color="047857")
    
    # Tabel Ranking
    headers_rank = ["Peringkat", "Kode Alternatif", "Nama Alternatif", "Skor Akhir", "Persentase", "Status Rekomendasi"]
    for col_idx, h in enumerate(headers_rank, 1):
        cell = ws1.cell(row=9, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
        
    for row_idx, alt in enumerate(calc_data['final_rankings'], 10):
        c1 = ws1.cell(row=row_idx, column=1, value=f"Rank {alt['ranking']}")
        c1.alignment = Alignment(horizontal="center")
        c2 = ws1.cell(row=row_idx, column=2, value=alt['kode'])
        c2.alignment = Alignment(horizontal="center")
        c3 = ws1.cell(row=row_idx, column=3, value=alt['nama'])
        c4 = ws1.cell(row=row_idx, column=4, value=alt['skor_akhir'])
        c4.alignment = Alignment(horizontal="right")
        c5 = ws1.cell(row=row_idx, column=5, value=f"{round(alt['skor_akhir'] * 100, 2)}%")
        c5.alignment = Alignment(horizontal="right")
        rec_text = "Rekomendasi Utama (Terbaik)" if alt['ranking'] == 1 else ("Prioritas 2" if alt['ranking'] == 2 else "Dipertimbangkan")
        c6 = ws1.cell(row=row_idx, column=6, value=rec_text)
        c6.alignment = Alignment(horizontal="center")
        
        for col_i in range(1, 7):
            cell = ws1.cell(row=row_idx, column=col_i)
            cell.border = thin_border
            cell.font = regular_font
            if alt['ranking'] == 1:
                cell.fill = success_fill
                
    # ================= SHEET 2: BOBOT KRITERIA & KONSISTENSI =================
    ws2 = wb.create_sheet(title="Perhitungan Kriteria")
    ws2.views.sheetView[0].showGridLines = True
    
    ws2["A1"] = "MATRIKS PERBANDINGAN BERPASANGAN KRITERIA (PAIRWISE)"
    ws2["A1"].font = title_font
    
    c_ahp = calc_data.get('criteria_ahp')
    if c_ahp and c_ahp['items']:
        items = c_ahp['items']
        matrix = c_ahp['matrix']
        col_sums = c_ahp['col_sums']
        norm_matrix = c_ahp['norm_matrix']
        weights_list = c_ahp['weights_list']
        
        # 1. Matriks Awal
        ws2.cell(row=3, column=1, value="Kriteria").fill = header_fill
        ws2.cell(row=3, column=1).font = header_font
        for j, it in enumerate(items, 2):
            cell = ws2.cell(row=3, column=j, value=it['kode'])
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")
            
        for i, it in enumerate(items):
            ws2.cell(row=4+i, column=1, value=f"{it['kode']} - {it['nama']}").font = bold_font
            for j in range(len(items)):
                cell = ws2.cell(row=4+i, column=2+j, value=round(matrix[i][j], 4))
                cell.border = thin_border
                cell.alignment = Alignment(horizontal="right")
                
        # Jumlah
        sum_row = 4 + len(items)
        ws2.cell(row=sum_row, column=1, value="Jumlah Kolom").font = bold_font
        ws2.cell(row=sum_row, column=1).fill = accent_fill
        for j in range(len(items)):
            cell = ws2.cell(row=sum_row, column=2+j, value=round(col_sums[j], 4))
            cell.border = thin_border
            cell.font = bold_font
            cell.fill = accent_fill
            cell.alignment = Alignment(horizontal="right")
            
        # 2. Matriks Normalisasi & Bobot
        start_norm = sum_row + 3
        ws2.cell(row=start_norm, column=1, value="MATRIKS NORMALISASI DAN BOBOT PRIORITAS").font = title_font
        
        ws2.cell(row=start_norm+2, column=1, value="Kriteria").fill = sub_fill
        ws2.cell(row=start_norm+2, column=1).font = header_font
        for j, it in enumerate(items, 2):
            cell = ws2.cell(row=start_norm+2, column=j, value=it['kode'])
            cell.fill = sub_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")
            
        w_col = len(items) + 2
        p_col = len(items) + 3
        ws2.cell(row=start_norm+2, column=w_col, value="Bobot Prioritas (W)").fill = header_fill
        ws2.cell(row=start_norm+2, column=w_col).font = header_font
        ws2.cell(row=start_norm+2, column=p_col, value="Persentase").fill = header_fill
        ws2.cell(row=start_norm+2, column=p_col).font = header_font
        
        for i, it in enumerate(items):
            curr_row = start_norm + 3 + i
            ws2.cell(row=curr_row, column=1, value=it['kode']).font = bold_font
            for j in range(len(items)):
                cell = ws2.cell(row=curr_row, column=2+j, value=round(norm_matrix[i][j], 4))
                cell.border = thin_border
                cell.alignment = Alignment(horizontal="right")
            # Bobot
            cell_w = ws2.cell(row=curr_row, column=w_col, value=round(weights_list[i]['bobot'], 4))
            cell_w.font = bold_font
            cell_w.border = thin_border
            cell_w.alignment = Alignment(horizontal="right")
            cell_w.fill = accent_fill
            # Persen
            cell_p = ws2.cell(row=curr_row, column=p_col, value=f"{weights_list[i]['persentase']}%")
            cell_p.font = bold_font
            cell_p.border = thin_border
            cell_p.alignment = Alignment(horizontal="right")
            
        # 3. Uji Konsistensi
        start_cr = start_norm + 4 + len(items) + 1
        ws2.cell(row=start_cr, column=1, value="HASIL UJI KONSISTENSI (CONSISTENCY CHECK)").font = title_font
        
        cr_params = [
            ("Ukuran Matriks (n)", c_ahp['n']),
            ("Lambda Maksimum (λ max)", c_ahp['lambda_max']),
            ("Consistency Index (CI)", c_ahp['ci']),
            ("Random Index (RI)", c_ahp['ri']),
            ("Consistency Ratio (CR)", c_ahp['cr']),
            ("Status Konsistensi", c_ahp['status'])
        ]
        
        for idx, (lbl, val) in enumerate(cr_params):
            r = start_cr + 2 + idx
            ws2.cell(row=r, column=1, value=lbl).font = bold_font
            c_val = ws2.cell(row=r, column=2, value=val)
            c_val.font = bold_font
            if lbl == "Status Konsistensi":
                c_val.fill = success_fill if c_ahp['is_consistent'] else PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
                
    # ================= SHEET 3: SINTESIS BOBOT =================
    ws3 = wb.create_sheet(title="Matriks Sintesis")
    ws3.views.sheetView[0].showGridLines = True
    
    ws3["A1"] = "MATRIKS BOBOT LOKAL ALTERNATIF DAN SINTESIS AKHIR"
    ws3["A1"].font = title_font
    
    crit_list = calc_data['criteria']
    alt_list = calc_data['alternatives']
    
    if crit_list and alt_list:
        # Headers
        ws3.cell(row=3, column=1, value="Alternatif").fill = header_fill
        ws3.cell(row=3, column=1).font = header_font
        
        for col_j, c in enumerate(crit_list, 2):
            w_c = calc_data['criteria_ahp']['weights'].get(c['id'], 0.0) if calc_data['criteria_ahp'] else 0.0
            cell = ws3.cell(row=3, column=col_j, value=f"{c['kode']} (W={round(w_c, 3)})")
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")
            
        skor_col = len(crit_list) + 2
        rank_col = len(crit_list) + 3
        ws3.cell(row=3, column=skor_col, value="Skor Akhir").fill = sub_fill
        ws3.cell(row=3, column=skor_col).font = header_font
        ws3.cell(row=3, column=rank_col, value="Peringkat").fill = sub_fill
        ws3.cell(row=3, column=rank_col).font = header_font
        
        # Rows
        for row_i, alt in enumerate(calc_data['final_rankings'], 4):
            ws3.cell(row=row_i, column=1, value=f"{alt['kode']} - {alt['nama']}").font = bold_font
            ws3.cell(row=row_i, column=1).border = thin_border
            
            for col_j, c in enumerate(crit_list, 2):
                cid = c['id']
                b_down = alt['breakdown'].get(cid, {})
                local_w = b_down.get('local_weight', 0.0)
                cell = ws3.cell(row=row_i, column=col_j, value=round(local_w, 4))
                cell.border = thin_border
                cell.alignment = Alignment(horizontal="right")
                
            cell_skor = ws3.cell(row=row_i, column=skor_col, value=alt['skor_akhir'])
            cell_skor.border = thin_border
            cell_skor.font = bold_font
            cell_skor.alignment = Alignment(horizontal="right")
            cell_skor.fill = accent_fill
            
            cell_rank = ws3.cell(row=row_i, column=rank_col, value=alt['ranking'])
            cell_rank.border = thin_border
            cell_rank.font = bold_font
            cell_rank.alignment = Alignment(horizontal="center")
            if alt['ranking'] == 1:
                cell_rank.fill = success_fill

    # Auto-adjust column widths
    for sheet in [ws1, ws2, ws3]:
        for col in sheet.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                val_str = str(cell.value or '')
                if len(val_str) > max_len and len(val_str) < 50:
                    max_len = len(val_str)
            sheet.column_dimensions[col_letter].width = max(max_len + 4, 12)
            
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
