"""
=============================================================
  SISTEM ANTRIAN SETORAN SAMPAH - BANK SAMPAH DIGITAL
  Backend: Python Flask + SQLite
  Struktur Data: QUEUE (implementasi manual)
=============================================================
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3, os
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB_PATH = "antrian.db"

# ══════════════════════════════════════════════════════════════
#  IMPLEMENTASI QUEUE MANUAL (tanpa library bawaan)
# ══════════════════════════════════════════════════════════════

class Node:
    """Satu elemen (nasabah) dalam antrian."""
    def __init__(self, data):
        self.data = data
        self.next = None


class AntrianQueue:
    """
    Queue berbasis Linked List — FIFO.
    Digunakan sebagai struktur data in-memory
    untuk antrian aktif saat server berjalan.
    """
    def __init__(self):
        self.head   = None
        self.tail   = None
        self.ukuran = 0

    def enqueue(self, data):
        """Tambah nasabah ke belakang antrian. O(1)"""
        node = Node(data)
        if self.tail is None:
            self.head = self.tail = node
        else:
            self.tail.next = node
            self.tail = node
        self.ukuran += 1

    def dequeue(self):
        """Ambil nasabah terdepan. O(1)"""
        if self.is_empty():
            return None
        data = self.head.data
        self.head = self.head.next
        if self.head is None:
            self.tail = None
        self.ukuran -= 1
        return data

    def peek(self):
        """Lihat nasabah terdepan tanpa menghapus. O(1)"""
        return self.head.data if self.head else None

    def traversal(self):
        """Daftar semua nasabah dalam antrian. O(n)"""
        result = []
        current = self.head
        posisi = 1
        while current:
            d = dict(current.data)
            d['posisi'] = posisi
            result.append(d)
            current = current.next
            posisi += 1
        return result

    def cari(self, nama):
        """Cari nasabah berdasarkan nama. O(n)"""
        result = []
        current = self.head
        posisi = 1
        while current:
            if nama.lower() in current.data['nama'].lower():
                d = dict(current.data)
                d['posisi'] = posisi
                result.append(d)
            current = current.next
            posisi += 1
        return result

    def is_empty(self):
        return self.ukuran == 0


# Instance Queue global (in-memory, aktif selama server jalan)
antrian = AntrianQueue()


# ══════════════════════════════════════════════════════════════
#  DATABASE SQLITE — untuk menyimpan riwayat permanen
# ══════════════════════════════════════════════════════════════

HARGA_SAMPAH = {
    "Plastik"          : 3000,
    "Kardus"           : 1500,
    "Kertas HVS"       : 2000,
    "Kaleng Aluminium" : 8000,
    "Besi/Logam"       : 4000,
    "Kaca/Botol"       :  500,
    "Minyak Jelantah"  : 4500,
    "Elektronik"       : 10000,
}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS antrian_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            no_antrian      INTEGER NOT NULL,
            nama            TEXT NOT NULL,
            jenis_sampah    TEXT NOT NULL,
            berat_kg        REAL NOT NULL,
            harga_per_kg    REAL NOT NULL,
            estimasi_nilai  REAL NOT NULL,
            status          TEXT DEFAULT 'menunggu',
            waktu_daftar    TEXT DEFAULT (datetime('now','localtime')),
            waktu_dilayani  TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("Database siap!")


def ok(data=None, message="OK", code=200):
    res = {"success": True, "message": message}
    if data is not None:
        res["data"] = data
    return jsonify(res), code

def err(message, code=400):
    return jsonify({"success": False, "message": message}), code


# ══════════════════════════════════════════════════════════════
#  ENDPOINTS
# ══════════════════════════════════════════════════════════════

@app.route("/")
def root():
    return ok({"name": "Antrian Bank Sampah API", "status": "running"})


# ── GET /api/harga — Daftar harga sampah ─────────────────────
@app.route("/api/harga")
def get_harga():
    data = [
        {"jenis": k, "harga_per_kg": v}
        for k, v in HARGA_SAMPAH.items()
    ]
    return ok(data)


# ── POST /api/antrian — Enqueue (daftarkan nasabah) ──────────
@app.route("/api/antrian", methods=["POST"])
def enqueue():
    d = request.get_json() or {}
    nama         = (d.get("nama") or "").strip()
    jenis_sampah = (d.get("jenis_sampah") or "").strip()
    berat_kg     = d.get("berat_kg", 0)

    if not nama:
        return err("Nama nasabah wajib diisi.")
    if jenis_sampah not in HARGA_SAMPAH:
        return err(f"Jenis sampah tidak valid. Pilih: {', '.join(HARGA_SAMPAH.keys())}")
    try:
        berat_kg = float(berat_kg)
        if berat_kg <= 0:
            return err("Berat harus lebih dari 0.")
    except (ValueError, TypeError):
        return err("Berat harus berupa angka.")

    harga_per_kg   = HARGA_SAMPAH[jenis_sampah]
    estimasi_nilai = berat_kg * harga_per_kg

    # Simpan ke DB untuk mendapatkan ID/nomor antrian
    conn = get_db()
    c = conn.cursor()
    # Hitung nomor antrian hari ini
    no_antrian = conn.execute(
        "SELECT COUNT(*)+1 FROM antrian_log WHERE date(waktu_daftar)=date('now','localtime')"
    ).fetchone()[0]

    c.execute("""
        INSERT INTO antrian_log (no_antrian, nama, jenis_sampah, berat_kg, harga_per_kg, estimasi_nilai)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (no_antrian, nama, jenis_sampah, berat_kg, harga_per_kg, estimasi_nilai))
    conn.commit()
    db_id = c.lastrowid

    # Simpan ke Queue in-memory
    data_nasabah = {
        "id"             : db_id,
        "no_antrian"     : no_antrian,
        "nama"           : nama,
        "jenis_sampah"   : jenis_sampah,
        "berat_kg"       : berat_kg,
        "harga_per_kg"   : harga_per_kg,
        "estimasi_nilai" : estimasi_nilai,
        "waktu_daftar"   : datetime.now().strftime("%H:%M:%S"),
        "status"         : "menunggu",
    }
    antrian.enqueue(data_nasabah)
    conn.close()

    return ok(data_nasabah, f"Nasabah '{nama}' berhasil masuk antrian nomor {no_antrian}.", 201)


# ── DELETE /api/antrian — Dequeue (layani nasabah terdepan) ──
@app.route("/api/antrian", methods=["DELETE"])
def dequeue():
    if antrian.is_empty():
        return err("Antrian kosong, tidak ada nasabah yang bisa dilayani.", 404)

    data = antrian.dequeue()

    # Update status di DB
    conn = get_db()
    conn.execute("""
        UPDATE antrian_log
        SET status='dilayani', waktu_dilayani=datetime('now','localtime')
        WHERE id=?
    """, (data["id"],))
    conn.commit()
    conn.close()

    data["status"] = "dilayani"
    data["waktu_dilayani"] = datetime.now().strftime("%H:%M:%S")

    sisa = antrian.ukuran
    berikutnya = antrian.peek()

    return ok({
        "dilayani"   : data,
        "sisa_antrian": sisa,
        "nasabah_berikutnya": berikutnya,
    }, f"Nasabah '{data['nama']}' berhasil dilayani.")


# ── GET /api/antrian — Traversal (tampilkan antrian aktif) ───
@app.route("/api/antrian")
def get_antrian():
    semua  = antrian.traversal()
    depan  = antrian.peek()
    return ok({
        "antrian"     : semua,
        "jumlah"      : antrian.ukuran,
        "terdepan"    : depan,
        "is_empty"    : antrian.is_empty(),
    })


# ── GET /api/antrian/peek — Peek ─────────────────────────────
@app.route("/api/antrian/peek")
def peek():
    data = antrian.peek()
    if data is None:
        return ok(None, "Antrian kosong.")
    return ok(data, f"Nasabah terdepan: {data['nama']}")


# ── GET /api/antrian/cari?nama=xxx — Pencarian ───────────────
@app.route("/api/antrian/cari")
def cari():
    nama = request.args.get("nama", "").strip()
    if not nama:
        return err("Parameter 'nama' wajib diisi.")
    hasil = antrian.cari(nama)
    return ok({
        "keyword": nama,
        "hasil"  : hasil,
        "jumlah" : len(hasil),
    })


# ── GET /api/riwayat — Riwayat dari DB ───────────────────────
@app.route("/api/riwayat")
def riwayat():
    limit  = request.args.get("limit", 50)
    status = request.args.get("status", "")
    conn   = get_db()
    query  = "SELECT * FROM antrian_log WHERE 1=1"
    params = []
    if status:
        query += " AND status=?"; params.append(status)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(int(limit))
    rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    total_nilai = conn.execute(
        "SELECT COALESCE(SUM(estimasi_nilai),0) FROM antrian_log WHERE status='dilayani'"
    ).fetchone()[0]
    total_berat = conn.execute(
        "SELECT COALESCE(SUM(berat_kg),0) FROM antrian_log WHERE status='dilayani'"
    ).fetchone()[0]
    conn.close()
    return ok({
        "riwayat"    : rows,
        "total_nilai": total_nilai,
        "total_berat": total_berat,
    })


# ── GET /api/statistik ────────────────────────────────────────
@app.route("/api/statistik")
def statistik():
    conn = get_db()
    total      = conn.execute("SELECT COUNT(*) v FROM antrian_log").fetchone()["v"]
    dilayani   = conn.execute("SELECT COUNT(*) v FROM antrian_log WHERE status='dilayani'").fetchone()["v"]
    menunggu_db= conn.execute("SELECT COUNT(*) v FROM antrian_log WHERE status='menunggu'").fetchone()["v"]
    total_nilai= conn.execute("SELECT COALESCE(SUM(estimasi_nilai),0) v FROM antrian_log WHERE status='dilayani'").fetchone()["v"]
    total_berat= conn.execute("SELECT COALESCE(SUM(berat_kg),0) v FROM antrian_log WHERE status='dilayani'").fetchone()["v"]

    per_jenis = {}
    for row in conn.execute("SELECT jenis_sampah, COUNT(*) jumlah, SUM(berat_kg) berat FROM antrian_log GROUP BY jenis_sampah"):
        per_jenis[row["jenis_sampah"]] = {"jumlah": row["jumlah"], "berat": row["berat"]}

    conn.close()
    return ok({
        "total_terdaftar" : total,
        "total_dilayani"  : dilayani,
        "sedang_menunggu" : antrian.ukuran,
        "total_nilai"     : total_nilai,
        "total_berat"     : total_berat,
        "per_jenis_sampah": per_jenis,
    })


# ── DELETE /api/reset — Reset antrian in-memory ──────────────
@app.route("/api/reset", methods=["DELETE"])
def reset():
    global antrian
    antrian = AntrianQueue()
    return ok(None, "Antrian berhasil direset.")


# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    init_db()
    print("╔══════════════════════════════════════════╗")
    print("║  🌿 Antrian Bank Sampah API               ║")
    print("║  http://localhost:5000                    ║")
    print("╚══════════════════════════════════════════╝")
    app.run(debug=True, port=5000)
