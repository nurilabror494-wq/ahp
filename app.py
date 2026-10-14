"""
Aplikasi Web Sistem Pendukung Keputusan (SPK) AHP (Analytical Hierarchy Process)
Framework: Flask
Database: SQLite
"""

import os
from functools import wraps
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for, 
    session, flash, jsonify, send_file, Response, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash
import io
import csv

from database import get_db, init_db, seed_default_data
from ahp_engine import SAATY_SCALE
from services import (
    get_active_decision_id, get_decision_details, 
    execute_ahp_calculation, generate_excel_report
)

app = Flask(__name__)
app.secret_key = "ahp_decision_support_system_secret_key_2026"

# Inisialisasi DB saat startup
with app.app_context():
    init_db()
    seed_default_data()

# Handler statis eksplisit untuk Vercel Serverless & Local
@app.route('/static/<path:filename>')
def custom_static(filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidate_dirs = [
        os.path.join(base_dir, 'static'),
        os.path.join(base_dir, 'public', 'static'),
        os.path.join(base_dir, 'public'),
    ]
    for d in candidate_dirs:
        if os.path.isfile(os.path.join(d, filename)):
            return send_from_directory(d, filename)
    return "Asset not found", 404

# ----------------- DECORATORS & CONTEXT PROCESSORS -----------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Silakan login terlebih dahulu untuk mengakses sistem.", "warning")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Silakan login terlebih dahulu.", "warning")
            return redirect(url_for('login'))
        if session.get('user_role') != 'admin':
            flash("Akses ditolak. Fitur ini hanya untuk pengguna dengan role Administrator.", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_global_data():
    """Menyediakan data global di setiap template Jinja2."""
    user = None
    active_decision = None
    all_decisions = []
    
    if 'user_id' in session:
        conn = get_db()
        cursor = conn.cursor()
        user = cursor.execute("SELECT id, nama, email, role FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        
        # Ambil daftar semua keputusan
        all_decisions = cursor.execute("SELECT * FROM decisions ORDER BY id DESC").fetchall()
        
        # Ambil keputusan aktif
        act_id = get_active_decision_id(conn, session)
        if act_id:
            active_decision = cursor.execute("SELECT * FROM decisions WHERE id = ?", (act_id,)).fetchone()
            
        conn.close()
        
    return {
        "current_user": user,
        "active_decision": active_decision,
        "all_decisions": all_decisions,
        "saaty_scale": SAATY_SCALE,
        "now_year": datetime.now().year
    }

# ----------------- AUTH ROUTES -----------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        conn = get_db()
        user = conn.cursor().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['nama']
            session['user_role'] = user['role']
            session['user_email'] = user['email']
            flash(f"Selamat datang kembali, {user['nama']}!", "success")
            
            next_url = request.args.get('next')
            return redirect(next_url or url_for('dashboard'))
        else:
            flash("Email atau password yang Anda masukkan salah.", "danger")
            
    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Anda telah berhasil logout.", "info")
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        nama = request.form.get('nama', '').strip()
        email = request.form.get('email', '').strip()
        new_password = request.form.get('new_password', '')
        
        if not nama or not email:
            flash("Nama dan email wajib diisi.", "warning")
        else:
            try:
                if new_password:
                    hashed = generate_password_hash(new_password)
                    cursor.execute(
                        "UPDATE users SET nama = ?, email = ?, password = ? WHERE id = ?",
                        (nama, email, hashed, session['user_id'])
                    )
                else:
                    cursor.execute(
                        "UPDATE users SET nama = ?, email = ? WHERE id = ?",
                        (nama, email, session['user_id'])
                    )
                conn.commit()
                session['user_name'] = nama
                session['user_email'] = email
                flash("Profil Anda berhasil diperbarui.", "success")
            except Exception as e:
                flash(f"Gagal memperbarui profil: {str(e)}", "danger")
                
    user = cursor.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    conn.close()
    return render_template('auth/profile.html', user=user)

# ----------------- DASHBOARD -----------------

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    act_id = get_active_decision_id(conn, session)
    
    if not act_id:
        conn.close()
        return render_template('dashboard/no_decision.html')
        
    calc_data = execute_ahp_calculation(conn, act_id)
    decision = get_decision_details(conn, act_id)
    conn.close()
    
    return render_template(
        'dashboard/index.html',
        decision=decision,
        calc=calc_data
    )

# ----------------- MULTI-KEPUTUSAN (STUDI KASUS) -----------------

@app.route('/decisions')
@login_required
def decisions_index():
    conn = get_db()
    decisions = conn.cursor().execute("""
        SELECT d.*, u.nama as pembuat,
               (SELECT COUNT(*) FROM criteria WHERE decision_id = d.id) as total_kriteria,
               (SELECT COUNT(*) FROM alternatives WHERE decision_id = d.id) as total_alternatif
        FROM decisions d
        LEFT JOIN users u ON d.user_id = u.id
        ORDER BY d.id DESC
    """).fetchall()
    conn.close()
    return render_template('decisions/index.html', decisions=decisions)

@app.route('/decisions/create', methods=['POST'])
@login_required
def decisions_create():
    nama = request.form.get('nama_keputusan', '').strip()
    tujuan = request.form.get('tujuan', '').strip()
    deskripsi = request.form.get('deskripsi', '').strip()
    tanggal = request.form.get('tanggal', datetime.now().strftime('%Y-%m-%d'))
    
    if not nama or not tujuan:
        flash("Nama keputusan dan tujuan wajib diisi.", "warning")
        return redirect(url_for('decisions_index'))
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO decisions (user_id, nama_keputusan, tujuan, deskripsi, tanggal)
        VALUES (?, ?, ?, ?, ?)
    """, (session['user_id'], nama, tujuan, deskripsi, tanggal))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    session['active_decision_id'] = new_id
    flash(f"Studi kasus keputusan '{nama}' berhasil dibuat dan diaktifkan.", "success")
    return redirect(url_for('kriteria_index'))

@app.route('/decisions/<int:dec_id>/activate')
@login_required
def decisions_activate(dec_id):
    conn = get_db()
    dec = conn.cursor().execute("SELECT id, nama_keputusan FROM decisions WHERE id = ?", (dec_id,)).fetchone()
    conn.close()
    
    if dec:
        session['active_decision_id'] = dec['id']
        flash(f"Studi kasus aktif beralih ke '{dec['nama_keputusan']}'.", "info")
    else:
        flash("Keputusan tidak ditemukan.", "danger")
        
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/decisions/<int:dec_id>/edit', methods=['POST'])
@login_required
def decisions_edit(dec_id):
    nama = request.form.get('nama_keputusan', '').strip()
    tujuan = request.form.get('tujuan', '').strip()
    deskripsi = request.form.get('deskripsi', '').strip()
    tanggal = request.form.get('tanggal', '')
    
    conn = get_db()
    conn.cursor().execute("""
        UPDATE decisions 
        SET nama_keputusan = ?, tujuan = ?, deskripsi = ?, tanggal = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (nama, tujuan, deskripsi, tanggal, dec_id))
    conn.commit()
    conn.close()
    
    flash("Data studi kasus berhasil diperbarui.", "success")
    return redirect(url_for('decisions_index'))

@app.route('/decisions/<int:dec_id>/delete', methods=['POST'])
@login_required
def decisions_delete(dec_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM decisions WHERE id = ?", (dec_id,))
    conn.commit()
    
    # Jika yang dihapus adalah yang aktif di session, ganti aktifnya
    if session.get('active_decision_id') == dec_id:
        first = cursor.execute("SELECT id FROM decisions ORDER BY id ASC LIMIT 1").fetchone()
        session['active_decision_id'] = first['id'] if first else None
        
    conn.close()
    flash("Studi kasus berhasil dihapus beserta seluruh kriteria dan alternatifnya.", "success")
    return redirect(url_for('decisions_index'))

# ----------------- MANAJEMEN KRITERIA -----------------

@app.route('/kriteria')
@login_required
def kriteria_index():
    conn = get_db()
    act_id = get_active_decision_id(conn, session)
    if not act_id:
        flash("Silakan buat atau pilih studi kasus keputusan terlebih dahulu.", "info")
        return redirect(url_for('decisions_index'))
        
    criteria = conn.cursor().execute("""
        SELECT c.*, cw.bobot
        FROM criteria c
        LEFT JOIN criteria_weights cw ON (cw.criteria_id = c.id AND cw.decision_id = c.decision_id)
        WHERE c.decision_id = ?
        ORDER BY c.id ASC
    """, (act_id,)).fetchall()
    
    calc_data = execute_ahp_calculation(conn, act_id)
    conn.close()
    return render_template('kriteria/index.html', criteria=criteria, calc=calc_data)

@app.route('/kriteria/create', methods=['POST'])
@login_required
def kriteria_create():
    conn = get_db()
    act_id = get_active_decision_id(conn, session)
    if not act_id:
        flash("Pilih studi kasus terlebih dahulu.", "warning")
        return redirect(url_for('decisions_index'))
        
    kode = request.form.get('kode', '').strip().upper()
    nama = request.form.get('nama', '').strip()
    deskripsi = request.form.get('deskripsi', '').strip()
    
    if not kode or not nama:
        flash("Kode dan Nama Kriteria wajib diisi.", "warning")
        return redirect(url_for('kriteria_index'))
        
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO criteria (decision_id, kode, nama, deskripsi)
        VALUES (?, ?, ?, ?)
    """, (act_id, kode, nama, deskripsi))
    conn.commit()
    
    # Recalculate
    execute_ahp_calculation(conn, act_id)
    conn.close()
    
    flash(f"Kriteria [{kode}] {nama} berhasil ditambahkan.", "success")
    return redirect(url_for('kriteria_index'))

@app.route('/kriteria/<int:c_id>/edit', methods=['POST'])
@login_required
def kriteria_edit(c_id):
    kode = request.form.get('kode', '').strip().upper()
    nama = request.form.get('nama', '').strip()
    deskripsi = request.form.get('deskripsi', '').strip()
    
    conn = get_db()
    conn.cursor().execute("""
        UPDATE criteria SET kode = ?, nama = ?, deskripsi = ? WHERE id = ?
    """, (kode, nama, deskripsi, c_id))
    conn.commit()
    
    act_id = get_active_decision_id(conn, session)
    execute_ahp_calculation(conn, act_id)
    conn.close()
    
    flash("Kriteria berhasil diperbarui.", "success")
    return redirect(url_for('kriteria_index'))

@app.route('/kriteria/<int:c_id>/delete', methods=['POST'])
@login_required
def kriteria_delete(c_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM criteria WHERE id = ?", (c_id,))
    conn.commit()
    
    act_id = get_active_decision_id(conn, session)
    execute_ahp_calculation(conn, act_id)
    conn.close()
    
    flash("Kriteria berhasil dihapus.", "success")
    return redirect(url_for('kriteria_index'))

# ----------------- MANAJEMEN ALTERNATIF -----------------

@app.route('/alternatif')
@login_required
def alternatif_index():
    conn = get_db()
    act_id = get_active_decision_id(conn, session)
    if not act_id:
        flash("Silakan pilih studi kasus terlebih dahulu.", "info")
        return redirect(url_for('decisions_index'))
        
    alternatives = conn.cursor().execute("""
        SELECT a.*, s.skor_akhir, s.ranking
        FROM alternatives a
        LEFT JOIN alternative_scores s ON (s.alternative_id = a.id AND s.decision_id = a.decision_id)
        WHERE a.decision_id = ?
        ORDER BY s.ranking ASC, a.id ASC
    """, (act_id,)).fetchall()
    
    calc_data = execute_ahp_calculation(conn, act_id)
    conn.close()
    return render_template('alternatif/index.html', alternatives=alternatives, calc=calc_data)

@app.route('/alternatif/create', methods=['POST'])
@login_required
def alternatif_create():
    conn = get_db()
    act_id = get_active_decision_id(conn, session)
    if not act_id:
        flash("Pilih studi kasus terlebih dahulu.", "warning")
        return redirect(url_for('decisions_index'))
        
    kode = request.form.get('kode', '').strip().upper()
    nama = request.form.get('nama', '').strip()
    deskripsi = request.form.get('deskripsi', '').strip()
    
    if not kode or not nama:
        flash("Kode dan Nama Alternatif wajib diisi.", "warning")
        return redirect(url_for('alternatif_index'))
        
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alternatives (decision_id, kode, nama, deskripsi)
        VALUES (?, ?, ?, ?)
    """, (act_id, kode, nama, deskripsi))
    conn.commit()
    
    execute_ahp_calculation(conn, act_id)
    conn.close()
    
    flash(f"Alternatif [{kode}] {nama} berhasil ditambahkan.", "success")
    return redirect(url_for('alternatif_index'))

@app.route('/alternatif/<int:a_id>/edit', methods=['POST'])
@login_required
def alternatif_edit(a_id):
    kode = request.form.get('kode', '').strip().upper()
    nama = request.form.get('nama', '').strip()
    deskripsi = request.form.get('deskripsi', '').strip()
    
    conn = get_db()
    conn.cursor().execute("""
        UPDATE alternatives SET kode = ?, nama = ?, deskripsi = ? WHERE id = ?
    """, (kode, nama, deskripsi, a_id))
    conn.commit()
    
    act_id = get_active_decision_id(conn, session)
    execute_ahp_calculation(conn, act_id)
    conn.close()
    
    flash("Alternatif berhasil diperbarui.", "success")
    return redirect(url_for('alternatif_index'))

@app.route('/alternatif/<int:a_id>/delete', methods=['POST'])
@login_required
def alternatif_delete(a_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM alternatives WHERE id = ?", (a_id,))
    conn.commit()
    
    act_id = get_active_decision_id(conn, session)
    execute_ahp_calculation(conn, act_id)
    conn.close()
    
    flash("Alternatif berhasil dihapus.", "success")
    return redirect(url_for('alternatif_index'))

# ----------------- HIERARKI AHP -----------------

@app.route('/hierarki')
@login_required
def hierarki_index():
    conn = get_db()
    act_id = get_active_decision_id(conn, session)
    calc_data = execute_ahp_calculation(conn, act_id)
    decision = get_decision_details(conn, act_id)
    conn.close()
    return render_template('hierarki/index.html', decision=decision, calc=calc_data)

# ----------------- PERBANDINGAN BERPASANGAN -----------------

@app.route('/perbandingan/kriteria', methods=['GET', 'POST'])
@login_required
def perbandingan_kriteria():
    conn = get_db()
    act_id = get_active_decision_id(conn, session)
    cursor = conn.cursor()
    
    criteria = cursor.execute("SELECT * FROM criteria WHERE decision_id = ? ORDER BY id ASC", (act_id,)).fetchall()
    crit_list = [dict(c) for c in criteria]
    n = len(crit_list)
    
    if request.method == 'POST':
        # Simpan nilai perbandingan
        for i in range(n):
            for j in range(i + 1, n):
                c1_id = crit_list[i]['id']
                c2_id = crit_list[j]['id']
                field_fav = f"fav_{c1_id}_{c2_id}"
                field_val = f"val_{c1_id}_{c2_id}"
                
                fav = request.form.get(field_fav, 'c1')
                val = float(request.form.get(field_val, 1.0))
                
                # Jika elemen 2 lebih disukai daripada elemen 1, nilainya 1 / val
                stored_val = val if fav == 'c1' else (1.0 / val if val != 0 else 1.0)
                
                cursor.execute("""
                    INSERT INTO criteria_comparisons (decision_id, criteria_id_1, criteria_id_2, nilai)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(decision_id, criteria_id_1, criteria_id_2) DO UPDATE SET nilai = excluded.nilai
                """, (act_id, c1_id, c2_id, stored_val))
                
        conn.commit()
        execute_ahp_calculation(conn, act_id)
        flash("Perbandingan berpasangan kriteria berhasil disimpan dan dihitung.", "success")
        return redirect(url_for('perhitungan_index'))
        
    # Ambil perbandingan yang sudah ada
    comps = cursor.execute("SELECT * FROM criteria_comparisons WHERE decision_id = ?", (act_id,)).fetchall()
    comp_map = {(c['criteria_id_1'], c['criteria_id_2']): c['nilai'] for c in comps}
    
    # Susun pasangan untuk formulir input
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            c1 = crit_list[i]
            c2 = crit_list[j]
            raw_val = comp_map.get((c1['id'], c2['id']), 1.0)
            
            fav = 'c1' if raw_val >= 1.0 else 'c2'
            display_val = raw_val if raw_val >= 1.0 else round(1.0 / raw_val, 2)
            if display_val < 1:
                display_val = 1
            if display_val > 9:
                display_val = 9
                
            pairs.append({
                "c1": c1,
                "c2": c2,
                "fav": fav,
                "val": int(round(display_val)),
                "raw_val": raw_val
            })
            
    calc_data = execute_ahp_calculation(conn, act_id)
    conn.close()
    return render_template('perbandingan/kriteria.html', criteria=crit_list, pairs=pairs, calc=calc_data)

@app.route('/perbandingan/alternatif', methods=['GET', 'POST'])
@login_required
def perbandingan_alternatif():
    conn = get_db()
    act_id = get_active_decision_id(conn, session)
    cursor = conn.cursor()
    
    criteria = cursor.execute("SELECT * FROM criteria WHERE decision_id = ? ORDER BY id ASC", (act_id,)).fetchall()
    alternatives = cursor.execute("SELECT * FROM alternatives WHERE decision_id = ? ORDER BY id ASC", (act_id,)).fetchall()
    
    crit_list = [dict(c) for c in criteria]
    alt_list = [dict(a) for a in alternatives]
    
    if not crit_list:
        flash("Tambahkan kriteria terlebih dahulu.", "warning")
        return redirect(url_for('kriteria_index'))
    if not alt_list:
        flash("Tambahkan alternatif terlebih dahulu.", "warning")
        return redirect(url_for('alternatif_index'))
        
    # Pilih kriteria aktif untuk perbandingan
    selected_cid = request.args.get('criteria_id', type=int)
    if not selected_cid or not any(c['id'] == selected_cid for c in crit_list):
        selected_cid = crit_list[0]['id']
        
    current_crit = next(c for c in crit_list if c['id'] == selected_cid)
    
    if request.method == 'POST':
        c_id = int(request.form.get('criteria_id'))
        m = len(alt_list)
        for i in range(m):
            for j in range(i + 1, m):
                a1_id = alt_list[i]['id']
                a2_id = alt_list[j]['id']
                field_fav = f"fav_{a1_id}_{a2_id}"
                field_val = f"val_{a1_id}_{a2_id}"
                
                fav = request.form.get(field_fav, 'a1')
                val = float(request.form.get(field_val, 1.0))
                
                stored_val = val if fav == 'a1' else (1.0 / val if val != 0 else 1.0)
                
                cursor.execute("""
                    INSERT INTO alternative_comparisons (decision_id, criteria_id, alternative_id_1, alternative_id_2, nilai)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(decision_id, criteria_id, alternative_id_1, alternative_id_2) DO UPDATE SET nilai = excluded.nilai
                """, (act_id, c_id, a1_id, a2_id, stored_val))
                
        conn.commit()
        execute_ahp_calculation(conn, act_id)
        flash(f"Perbandingan alternatif untuk kriteria [{current_crit['kode']}] berhasil disimpan.", "success")
        return redirect(url_for('perbandingan_alternatif', criteria_id=c_id))
        
    # Ambil perbandingan alternatif untuk kriteria terpilih
    alt_comps = cursor.execute("""
        SELECT * FROM alternative_comparisons WHERE decision_id = ? AND criteria_id = ?
    """, (act_id, selected_cid)).fetchall()
    comp_map = {(c['alternative_id_1'], c['alternative_id_2']): c['nilai'] for c in alt_comps}
    
    pairs = []
    m = len(alt_list)
    for i in range(m):
        for j in range(i + 1, m):
            a1 = alt_list[i]
            a2 = alt_list[j]
            raw_val = comp_map.get((a1['id'], a2['id']), 1.0)
            
            fav = 'a1' if raw_val >= 1.0 else 'a2'
            display_val = raw_val if raw_val >= 1.0 else round(1.0 / raw_val, 2)
            if display_val < 1:
                display_val = 1
            if display_val > 9:
                display_val = 9
                
            pairs.append({
                "a1": a1,
                "a2": a2,
                "fav": fav,
                "val": int(round(display_val)),
                "raw_val": raw_val
            })
            
    calc_data = execute_ahp_calculation(conn, act_id)
    current_crit_ahp = calc_data['alt_ahp_by_criteria'].get(selected_cid)
    
    conn.close()
    return render_template(
        'perbandingan/alternatif.html',
        criteria=crit_list,
        alternatives=alt_list,
        selected_cid=selected_cid,
        current_crit=current_crit,
        pairs=pairs,
        current_crit_ahp=current_crit_ahp
    )

# ----------------- PROSES PERHITUNGAN AHP -----------------

@app.route('/perhitungan')
@login_required
def perhitungan_index():
    conn = get_db()
    act_id = get_active_decision_id(conn, session)
    calc_data = execute_ahp_calculation(conn, act_id)
    decision = get_decision_details(conn, act_id)
    conn.close()
    return render_template('perhitungan/index.html', decision=decision, calc=calc_data)

# ----------------- HASIL PERANGKINGAN -----------------

@app.route('/perangkingan')
@login_required
def perangkingan_index():
    conn = get_db()
    act_id = get_active_decision_id(conn, session)
    calc_data = execute_ahp_calculation(conn, act_id)
    decision = get_decision_details(conn, act_id)
    conn.close()
    return render_template('perangkingan/index.html', decision=decision, calc=calc_data)

# ----------------- LAPORAN & EKSPOR -----------------

@app.route('/laporan')
@login_required
def laporan_index():
    conn = get_db()
    act_id = get_active_decision_id(conn, session)
    calc_data = execute_ahp_calculation(conn, act_id)
    decision = get_decision_details(conn, act_id)
    conn.close()
    return render_template('laporan/index.html', decision=decision, calc=calc_data)

@app.route('/laporan/excel')
@login_required
def laporan_excel():
    conn = get_db()
    act_id = get_active_decision_id(conn, session)
    decision = get_decision_details(conn, act_id)
    
    excel_buffer = generate_excel_report(conn, act_id)
    conn.close()
    
    filename = f"Laporan_SPK_AHP_{decision['nama_keputusan'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(
        excel_buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )

@app.route('/laporan/csv')
@login_required
def laporan_csv():
    conn = get_db()
    act_id = get_active_decision_id(conn, session)
    decision = get_decision_details(conn, act_id)
    calc_data = execute_ahp_calculation(conn, act_id)
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(["LAPORAN PERANGKINGAN AHP"])
    writer.writerow(["Studi Kasus", decision['nama_keputusan'] if decision else ''])
    writer.writerow(["Tujuan", decision['tujuan'] if decision else ''])
    writer.writerow(["Tanggal", decision['tanggal'] if decision else ''])
    writer.writerow([])
    writer.writerow(["Ranking", "Kode", "Nama Alternatif", "Skor Akhir", "Persentase"])
    
    for alt in calc_data['final_rankings']:
        writer.writerow([
            alt['ranking'],
            alt['kode'],
            alt['nama'],
            alt['skor_akhir'],
            f"{round(alt['skor_akhir'] * 100, 2)}%"
        ])
        
    output.seek(0)
    filename = f"Ranking_AHP_{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

# ----------------- MANAJEMEN PENGGUNA (ADMIN ONLY) -----------------

@app.route('/users')
@admin_required
def users_index():
    conn = get_db()
    users = conn.cursor().execute("SELECT * FROM users ORDER BY id ASC").fetchall()
    conn.close()
    return render_template('users/index.html', users=users)

@app.route('/users/create', methods=['POST'])
@admin_required
def users_create():
    nama = request.form.get('nama', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    role = request.form.get('role', 'pengguna')
    
    if not nama or not email or not password:
        flash("Semua field wajib diisi.", "warning")
        return redirect(url_for('users_index'))
        
    conn = get_db()
    cursor = conn.cursor()
    try:
        hashed = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (nama, email, password, role) VALUES (?, ?, ?, ?)",
            (nama, email, hashed, role)
        )
        conn.commit()
        flash(f"Pengguna '{nama}' ({email}) berhasil didaftarkan.", "success")
    except Exception as e:
        flash(f"Gagal menambahkan pengguna: {str(e)}", "danger")
    finally:
        conn.close()
        
    return redirect(url_for('users_index'))

@app.route('/users/<int:u_id>/edit', methods=['POST'])
@admin_required
def users_edit(u_id):
    nama = request.form.get('nama', '').strip()
    email = request.form.get('email', '').strip()
    role = request.form.get('role', 'pengguna')
    new_password = request.form.get('new_password', '')
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        if new_password:
            hashed = generate_password_hash(new_password)
            cursor.execute(
                "UPDATE users SET nama = ?, email = ?, role = ?, password = ? WHERE id = ?",
                (nama, email, role, hashed, u_id)
            )
        else:
            cursor.execute(
                "UPDATE users SET nama = ?, email = ?, role = ? WHERE id = ?",
                (nama, email, role, u_id)
            )
        conn.commit()
        flash("Data pengguna berhasil diperbarui.", "success")
    except Exception as e:
        flash(f"Gagal memperbarui pengguna: {str(e)}", "danger")
    finally:
        conn.close()
        
    return redirect(url_for('users_index'))

@app.route('/users/<int:u_id>/delete', methods=['POST'])
@admin_required
def users_delete(u_id):
    if u_id == session.get('user_id'):
        flash("Anda tidak dapat menghapus akun Anda sendiri saat sedang login.", "warning")
        return redirect(url_for('users_index'))
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (u_id,))
    conn.commit()
    conn.close()
    
    flash("Pengguna berhasil dihapus.", "success")
    return redirect(url_for('users_index'))

# ----------------- MAIN ENTRYPOINT -----------------

if __name__ == '__main__':
    print("=" * 60)
    print(" SISTEM PENDUKUNG KEPUTUSAN AHP (ANALYTICAL HIERARCHY PROCESS)")
    print(" Server berjalan di: http://127.0.0.1:5000")
    print(" Akun Demo:")
    print(" - Admin: admin@ahp.com | Password: admin123")
    print(" - User:  user@ahp.com  | Password: user123")
    print("=" * 60)
    app.run(host='127.0.0.1', port=5000, debug=True)
