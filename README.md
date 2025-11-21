# HEFT Task Scheduler pada Sistem Heterogen

Proyek ini mengimplementasikan algoritma **HEFT (Heterogeneous Earliest Finish Time)** untuk menjadwalkan dan mengeksekusi tugas secara asinkron pada klaster simulasi server (VM) yang heterogen. Sistem dirancang untuk meminimalkan *makespan* (total waktu penyelesaian) dengan memanfaatkan perbedaan kapasitas komputasi antar node.

## 🚀 Fitur Utama

  * **Algoritma HEFT:** Menghitung prioritas tugas (*upward rank*) dan menugaskan tugas ke prosesor yang memberikan waktu selesai paling awal (*Earliest Finish Time*).
  * **Parallel Chain DAG:** Menggunakan struktur *Directed Acyclic Graph* (DAG) berbentuk rantai paralel untuk memungkinkan eksekusi simultan, menghindari *blocking* yang terjadi pada struktur linear.
  * **Komputasi Heterogen:** Menangani VM dengan spesifikasi CPU yang berbeda (1, 2, 4, dan 8 core).
  * **Eksekusi Asinkron:** Menggunakan `asyncio` dan `httpx` untuk eksekusi tugas non-blocking secara paralel.
  * **Analisis Metrik:** Menghasilkan laporan performa mendetail (Makespan, Throughput, Imbalance Degree, Resource Utilization).

## 🛠️ Arsitektur Sistem

Sistem terdiri dari 4 Virtual Machine (VM) dengan spesifikasi heterogen. Biaya komputasi (*computation cost*) sebuah tugas berbanding terbalik dengan jumlah core CPU VM.

| VM ID | Kapasitas CPU | Peran |
| :--- | :--- | :--- |
| **VM1** | 1 Core | *Low-power node* (Tugas ringan) |
| **VM2** | 2 Cores | *Medium node* |
| **VM3** | 4 Cores | *High-performance node* |
| **VM4** | 8 Cores | *Ultra-performance node* (Menangani tugas terberat) |

**Rumus Beban Tugas:**

```python
Computation Cost = (Task_Index² * 10000) / VM_CPU_Cores
```

Semakin besar indeks tugas, semakin berat beban komputasinya, namun akan dieksekusi lebih cepat di VM dengan core lebih banyak.

## 📊 Hasil Analisis Performa

Berikut adalah hasil evaluasi kinerja sistem berdasarkan rata-rata dari **10 kali percobaan**. Data ini menunjukkan efisiensi algoritma HEFT dalam memetakan tugas berat ke VM yang kuat (VM4) dan tugas ringan ke VM lainnya.

| Parameter | Rata-Rata Nilai | Satuan | Deskripsi |
| :--- | :--- | :--- | :--- |
| **Makespan** | **29.0936** | detik | Total waktu yang dibutuhkan untuk menyelesaikan seluruh batch tugas. |
| **Throughput** | **0.67458** | tugas/detik | Kecepatan rata-rata penyelesaian tugas per satuan waktu. |
| **Total CPU Time** | **226.1446** | detik | Akumulasi waktu pemrosesan efektif oleh seluruh CPU. |
| **Total Wait Time** | **75.60622** | detik | Total waktu tugas menunggu dalam antrian semaphore sebelum dieksekusi. |
| **Avg Start Time (rel)** | **2.7937** | detik | Rata-rata waktu dimulainya tugas relatif terhadap awal jadwal. |
| **Avg Execution Time** | **11.31088** | detik | Rata-rata durasi eksekusi satu tugas. |
| **Avg Finish Time (rel)** | **13.98288** | detik | Rata-rata waktu penyelesaian tugas. |
| **Imbalance Degree** | **1.8790** | - | Tingkat ketidakseimbangan beban antar VM. Nilai \> 0 wajar pada HEFT karena VM kuat (VM4) sengaja diberi beban lebih banyak. |
| **Resource Utilization** | **51.35%** | % | Persentase penggunaan sumber daya CPU selama makespan. |

### Analisis Hasil

1.  **Efisiensi Makespan:** Dengan makespan rata-rata \~29 detik untuk total beban kerja yang besar, HEFT berhasil meminimalkan waktu total dengan memprioritaskan jalur kritis ke VM4 (8 Core).
2.  **Resource Utilization (51.35%):** Angka ini menunjukkan karakteristik alami sistem heterogen menggunakan HEFT. VM dengan core rendah (VM1/VM2) mungkin selesai lebih cepat atau menunggu (idle) sementara VM4 menyelesaikan tugas-tugas berat yang berada di *critical path*.
3.  **Imbalance Degree (1.88):** Menunjukkan distribusi beban yang tidak merata secara volume, namun **efisien secara waktu**. VM4 menangani porsi komputasi terbesar, yang merupakan perilaku yang diharapkan dari algoritma HEFT.

## ⚙️ Instalasi & Penggunaan

### 1\. Prasyarat

  * Python 3.8+
  * Akses ke server/VM (atau simulasi lokal)

### 2\. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3\. Konfigurasi Environment

Buat file `.env` dan sesuaikan IP address VM:

```env
VM1_IP="192.168.1.x"
VM2_IP="192.168.1.x"
VM3_IP="192.168.1.x"
VM4_IP="192.168.1.x"
VM_PORT=5000
```

### 4\. Menjalankan Scheduler

Pastikan server (node worker) telah berjalan, kemudian jalankan scheduler:

```bash
python scheduler.py
```

## 📂 Struktur Proyek

```
.
├── heft_algorithm.py    # Core logic: Class HEFTAlgorithm, Task, ScheduleEvent
├── scheduler.py         # Main: Async executor, DAG creation, Metrics calculation
├── dataset.txt          # Input data (daftar indeks tugas)
├── requirements.txt     # Daftar library Python (httpx, pandas, numpy, dll)
├── result.csv           # (Generated) Log detail eksekusi per tugas
└── README.md            # Dokumentasi proyek
```

## 📝 Catatan Implementasi DAG

Untuk mengatasi limitasi eksekusi serial, proyek ini menggunakan strategi **Parallel Chains DAG**.
Tugas dibagi menjadi 4 rantai independen (modulo 4) yang memungkinkan:

  * Task 0, 4, 8... -\> Chain 1
  * Task 1, 5, 9... -\> Chain 2
  * dst.

Strategi ini memaksa algoritma HEFT untuk melihat peluang paralelisme sejak detik pertama (t=0), sehingga VM1, VM2, VM3, dan VM4 dapat bekerja secara bersamaan tanpa saling menunggu di awal eksekusi.
