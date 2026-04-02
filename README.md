#Struktur

```
queue-app/
├── backend/
│   ├── app.py            ← Flask API (Queue manual + SQLite)
│   └── requirements.txt
└── frontend/
    └── index.html        ← Visualisasi Queue (buka di browser, css & js inline)
```

---

#Cara Menjalankan

#1. Backend (Flask — port 5000)

```bash
cd queue-app/backend
pip install -r requirements.txt
python app.py
```

#2. Frontend

Buka file `frontend/index.html` langsung di Chrome.

---

#API Endpoints

| Method | URL | Keterangan |
|--------|-----|------------|
| GET    | /api/antrian | Traversal — tampilkan semua antrian |
| POST   | /api/antrian | Enqueue — tambah nasabah |
| DELETE | /api/antrian | Dequeue — layani nasabah terdepan |
| GET    | /api/antrian/peek | Peek — cek terdepan |
| GET    | /api/antrian/cari?nama=xxx | Search — cari nasabah |
| GET    | /api/riwayat | Riwayat dari database |
| GET    | /api/statistik | Statistik keseluruhan |
| GET    | /api/harga | Daftar harga sampah |

---

# Fitur Frontend

- **Visualisasi Queue** animasi node dengan pointer head/tail
- **Diagram Pointer** head → ... → tail → NULL
- **Log Operasi** real-time setiap operasi dicatat
- **Statistik** jumlah antrian, dilayani, total nilai
- **Estimasi nilai** otomatis saat input berat
- Auto-refresh setiap 5 detik
