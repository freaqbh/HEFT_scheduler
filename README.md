# HEFT Task Scheduler

Implementasi algoritma **HEFT (Heterogeneous Earliest Finish Time)** untuk task scheduling pada sistem heterogen. Proyek ini dibuat untuk keperluan mata kuliah **Strategi Optimasi Komputasi Awan (SOKA)**.

## Tentang Algoritma HEFT

HEFT adalah algoritma heuristik untuk penjadwalan tugas pada sistem heterogen yang terdiri dari dua fase utama:

1. **Task Prioritization**: Menghitung upward rank untuk setiap task berdasarkan estimasi waktu penyelesaian dan komunikasi dengan task penerusnya.

2. **Processor Selection**: Memilih processor yang memberikan earliest finish time (EFT) untuk setiap task, dengan mempertimbangkan waktu eksekusi dan komunikasi.

### Kelebihan HEFT:
- Mempertimbangkan komunikasi antar task
- Efektif untuk sistem heterogen
- Kompleksitas waktu O(v² × p) dimana v adalah jumlah task dan p adalah jumlah processor
- Menghasilkan schedule yang baik untuk DAG (Directed Acyclic Graph)

## Struktur Proyek

```
.
├── heft_algorithm.py      # Implementasi algoritma HEFT
├── scheduler.py           # Scheduler utama yang menggunakan HEFT
├── requirements.txt       # Dependencies Python
├── .env.example          # Contoh konfigurasi environment variables
├── README.md             # Dokumentasi
└── dataset.txt           # File dataset input (buat sendiri)
```

## Prerequisites

1. **Python 3.8+**
2. **uv** sebagai dependency manager (atau pip)
3. **Docker** (untuk menjalankan server)
4. **VPN/Wifi ITS** (untuk mengakses server VM)

## Instalasi

### 1. Install uv (jika belum ada)

Lihat dokumentasi di [https://github.com/astral-sh/uv](https://github.com/astral-sh/uv)

### 2. Install Dependencies

Menggunakan uv:
```bash
uv sync
```

Atau menggunakan pip:
```bash
pip install -r requirements.txt
```

### 3. Konfigurasi Environment Variables

Buat file `.env` berdasarkan `.env.example`:

```bash
cp .env.example .env
```

Edit file `.env` dan isi dengan IP address server VM:

```env
VM1_IP="192.168.x.x"
VM2_IP="192.168.x.x"
VM3_IP="192.168.x.x"
VM4_IP="192.168.x.x"

VM_PORT=5000
```

### 4. Setup Server

Jalankan server menggunakan Docker Compose:

```bash
docker compose build --no-cache
docker compose up -d
```

Pastikan server berjalan di semua VM yang dikonfigurasi.

### 5. Buat Dataset

Buat file `dataset.txt` berisi angka 1-10 (satu angka per baris). Contoh:

```
6
5
8
2
10
3
4
4
7
3
9
1
7
9
1
8
2
5
6
10
```

## Penggunaan

### Menjalankan Scheduler

Pastikan Anda terhubung ke **VPN/Wifi ITS** sebelum menjalankan scheduler.

Menggunakan uv:
```bash
uv run scheduler.py
```

Atau menggunakan Python langsung:
```bash
python scheduler.py
```

### Output

Setelah scheduler berjalan, akan menghasilkan:

1. **Console Output**: Menampilkan:
   - Task prioritization (upward ranks)
   - Hasil scheduling (processor assignment, start/finish time)
   - Processor loads
   - Parameter analisis (makespan, deviation)

2. **result.csv**: File CSV berisi detail schedule dan hasil eksekusi:
   - Task ID
   - Task Value
   - Processor ID
   - Scheduled Start/Finish Time
   - Actual Start/Finish Time
   - Execution Time
   - Makespan

## Contoh Output

```
============================================================
HEFT Task Scheduler
============================================================
Loaded 4 server(s): ['192.168.x.x', '192.168.x.x', ...]
Loaded 20 tasks from dataset.txt

=== Phase 1: Task Prioritization ===

=== Hasil Scheduling ===
Makespan: 45.20
Total Tasks: 20

=== Detail Schedule ===
Task 0: Processor 2, Start=0.00, Finish=4.80
Task 1: Processor 2, Start=4.80, Finish=9.60
...

=== Processor Loads ===
Processor 1: 5 tasks, Total time: 25.00
Processor 2: 8 tasks, Total time: 38.40
Processor 3: 4 tasks, Total time: 18.00
Processor 4: 3 tasks, Total time: 13.50

=== Eksekusi Schedule ===
Task 0 (value=6) dieksekusi di Server 2 (192.168.x.x)
  -> Selesai dalam 4.85 detik
...

=== Parameter Analisis ===
Actual Makespan: 46.50
Scheduled Makespan: 45.20
Deviation: 1.30

Hasil disimpan ke result.csv
```

## Algoritma HEFT - Detail Implementasi

### Phase 1: Task Prioritization

Menghitung **upward rank** untuk setiap task:

```
rank(t) = w̄(t) + max(rank(succ(t)) + c̄(t, succ(t)))
```

Dimana:
- `w̄(t)` = average computation cost task t
- `rank(succ(t))` = upward rank dari successor task
- `c̄(t, succ(t))` = average communication cost dari t ke successor

### Phase 2: Processor Selection

Untuk setiap task (diurutkan berdasarkan rank descending):
1. Hitung **Earliest Start Time (EST)** untuk setiap processor
2. Hitung **Earliest Finish Time (EFT)** = EST + execution_time
3. Pilih processor dengan EFT terkecil

## Kustomisasi

### Mengubah Communication Cost

Edit `_initialize_communication_matrix()` di `scheduler.py`:

```python
def _initialize_communication_matrix(self) -> Dict[tuple, float]:
    matrix = {}
    for from_proc in self.processors:
        for to_proc in self.processors:
            if from_proc != to_proc:
                # Custom communication cost
                matrix[(from_proc, to_proc)] = your_custom_cost
    return matrix
```

### Mengubah Task DAG Structure

Edit `_create_task_dag()` di `scheduler.py` untuk membuat struktur DAG yang berbeda (bukan linear).

### Mengubah Computation Cost

Edit bagian `computation_cost` di `_create_task_dag()` untuk mengatur cost setiap task pada setiap processor.

## Troubleshooting

### Error: "Tidak ada server yang dikonfigurasi"
- Pastikan file `.env` sudah dibuat dan diisi dengan benar
- Pastikan semua variabel VM1_IP sampai VM4_IP sudah diisi

### Error: "File dataset.txt tidak ditemukan"
- Buat file `dataset.txt` di direktori yang sama dengan `scheduler.py`
- Pastikan format file benar (satu angka per baris)

### Error saat eksekusi ke server
- Pastikan VPN/Wifi ITS sudah terhubung
- Pastikan server sudah berjalan di semua VM
- Cek koneksi ke server dengan ping atau curl

### Server tidak merespons
- Pastikan Docker Compose sudah berjalan (`docker compose ps`)
- Cek log server (`docker compose logs`)
- Pastikan port 5000 tidak terblokir firewall

## Referensi

- Repository referensi: [SOKA-Task-Scheduling-Server-Test](https://github.com/lab-kcks/SOKA-Task-Scheduling-Server-Test)
- Topcuoglu, H., Hariri, S., & Wu, M. Y. (2002). Performance-effective and low-complexity task scheduling for heterogeneous computing. IEEE transactions on parallel and distributed systems, 13(3), 260-274.

## Lisensi

Proyek ini dibuat untuk keperluan akademik mata kuliah SOKA.

