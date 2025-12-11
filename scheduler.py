"""
Scheduler yang mendukung berbagai algoritma (HEFT, SHC, RR, FCFS)
untuk penentuan jadwal dengan eksekutor asinkron paralel.
"""

import asyncio
import httpx
import time
from datetime import datetime
import csv
import pandas as pd
import sys
import os
import argparse
from dotenv import load_dotenv
from collections import namedtuple
from typing import List, Dict, Optional
from dataclasses import dataclass

# Impor algoritma
from heft_algorithm import HEFTAlgorithm, Task as HeftTask, ScheduleEvent
from shc_algorithm import SHCAlgorithm
from rr_algorithm import RRAlgorithm
from fcfs_algorithm import FCFSAlgorithm

# --- Konfigurasi Lingkungan ---

load_dotenv()

VM_SPECS = {
    'vm1': {'ip': os.getenv("VM1_IP"), 'cpu': 1, 'ram_gb': 1},
    'vm2': {'ip': os.getenv("VM2_IP"), 'cpu': 2, 'ram_gb': 2},
    'vm3': {'ip': os.getenv("VM3_IP"), 'cpu': 4, 'ram_gb': 4},
    'vm4': {'ip': os.getenv("VM4_IP"), 'cpu': 8, 'ram_gb': 4},
}

VM_PORT = int(os.getenv('VM_PORT', 5000))
RESULTS_FILE_PREFIX = 'results_'

# Definisi Tipe Data
VM = namedtuple('VM', ['name', 'ip', 'cpu_cores', 'ram_gb'])
Task = namedtuple('Task', ['id', 'name', 'index', 'cpu_load'])

# --- Fungsi Helper & Definisi Task ---

def get_task_load(index: int):
    """Menghitung beban CPU berdasarkan indeks task."""
    cpu_load = (index * index * 10000)
    return cpu_load

def load_tasks(dataset_path: str) -> list[Task]:
    """Memuat daftar tugas dari file dataset."""
    if not os.path.exists(dataset_path):
        print(f"Error: File dataset '{dataset_path}' tidak ditemukan.", file=sys.stderr)
        sys.exit(1)
        
    tasks = []
    with open(dataset_path, 'r') as f:
        for i, line in enumerate(f):
            try:
                index = int(line.strip())
                if not 1 <= index <= 10:
                    print(f"Peringatan: Task index {index} di baris {i+1} di luar rentang (1-10).")
                    continue
                
                cpu_load = get_task_load(index)
                task_name = f"task-{index}-{i}"
                tasks.append(Task(
                    id=i,
                    name=task_name,
                    index=index,
                    cpu_load=cpu_load,
                ))
            except ValueError:
                print(f"Peringatan: Mengabaikan baris {i+1} yang tidak valid: '{line.strip()}'")
    
    print(f"Berhasil memuat {len(tasks)} tugas dari {dataset_path}")
    return tasks

# --- Kelas TaskScheduler ---

class TaskScheduler:
    """
    Menggunakan berbagai algoritma untuk *menghasilkan* penugasan (assignment)
    tugas ke VM.
    """
    
    def __init__(self):
        """Inisialisasi scheduler dengan konfigurasi dari .env"""
        self.vms = self._load_vms()
        self.processors = [vm.name for vm in self.vms]
        self.communication_matrix = self._initialize_communication_matrix()
        
    def _load_vms(self) -> List[VM]:
        """Load konfigurasi VM dari VM_SPECS."""
        vms = []
        for name, spec in VM_SPECS.items():
            ip = spec.get('ip')
            if ip:
                vms.append(VM(
                    name=name,
                    ip=ip,
                    cpu_cores=spec.get('cpu', 1),
                    ram_gb=spec.get('ram_gb', 1)
                ))
        
        if not vms:
            raise ValueError("Tidak ada server VM yang dikonfigurasi. Pastikan file .env sudah diisi dengan benar.")
        
        print(f"Loaded {len(vms)} VM(s): {[vm.name for vm in vms]}")
        return vms
    
    def _initialize_communication_matrix(self) -> Dict[tuple, float]:
        """Inisialisasi communication matrix antar processor (VM)."""
        matrix = {}
        for from_proc in self.processors:
            for to_proc in self.processors:
                if from_proc != to_proc:
                    matrix[(from_proc, to_proc)] = 1.0
        return matrix
    
    def _create_task_dag(self, tasks: List[Task]) -> List[HeftTask]:
        """Membuat DAG dengan struktur 'Parallel Chains'."""
        heft_tasks = []
        num_tasks = len(tasks)
        num_chains = 4 
        
        for i, task in enumerate(tasks):
            predecessors = [tasks[i - num_chains].id] if i >= num_chains else []
            successors = [tasks[i + num_chains].id] if i + num_chains < num_tasks else []
            
            computation_cost = {}
            for vm in self.vms:
                computation_cost[vm.name] = task.cpu_load / vm.cpu_cores
            
            heft_task_obj = HeftTask(
                id=task.id,
                computation_cost=computation_cost,
                predecessors=predecessors,
                successors=successors
            )
            heft_tasks.append(heft_task_obj)
        
        return heft_tasks
    
    def run_scheduler(self, tasks: List[Task], algorithm_name: str) -> Dict[int, str]:
        """
        Menjalankan algoritma scheduling yang dipilih.
        
        Args:
            tasks: List of Task
            algorithm_name: 'heft', 'shc', 'rr', or 'fcfs'
            
        Returns:
            Dictionary mapping {task_id: vm_name}
        """
        print("=" * 60)
        print(f"Menjalankan Task Scheduler: {algorithm_name.upper()}")
        print("=" * 60)
        
        # 1. Buat DAG/Task Objects yang dibutuhkan
        heft_tasks = self._create_task_dag(tasks)
        
        # 2. Inisialisasi Algorithm
        algo_instance = None
        if algorithm_name == 'heft':
            algo_instance = HEFTAlgorithm(
                tasks=heft_tasks,
                processors=self.processors,
                communication_matrix=self.communication_matrix
            )
        elif algorithm_name == 'shc':
            algo_instance = SHCAlgorithm(
                tasks=heft_tasks,
                processors=self.processors
            )
        elif algorithm_name == 'rr':
            algo_instance = RRAlgorithm(
                tasks=heft_tasks,
                processors=self.processors
            )
        elif algorithm_name == 'fcfs':
            algo_instance = FCFSAlgorithm(
                tasks=heft_tasks,
                processors=self.processors
            )
        else:
            raise ValueError(f"Algoritma tidak dikenal: {algorithm_name}")
        
        # 3. Jalankan scheduling
        print(f"\n=== Phase 1: Scheduling ({algorithm_name.upper()}) ===")
        schedule = algo_instance.schedule_tasks()
        
        # 4. Tampilkan hasil scheduling
        print(f"\n=== Hasil Scheduling ({algorithm_name.upper()}) ===")
        makespan = algo_instance.get_makespan()
        print(f"Perkiraan Makespan: {makespan:.2f}")
        
        # 5. Konversi schedule ke assignment
        assignment = {}
        for task_id, event in schedule.items():
            assignment[task_id] = event.processor_id
        
        print("\nPenugasan Tugas dari Scheduler (akan dieksekusi secara paralel):")
        # Tampilkan 10 pertama
        for task_id in sorted(assignment.keys())[:10]:
             print(f"  - Tugas {task_id} -> {assignment[task_id]}")
        if len(assignment) > 10:
            print("  - ... etc.")

        return assignment

# --- Eksekutor Tugas Asinkron ---

async def execute_task_on_vm(task: Task, vm: VM, client: httpx.AsyncClient, 
                             vm_semaphore: asyncio.Semaphore, results_list: list):
    """Mengirim request GET ke VM yang ditugaskan."""
    url = f"http://{vm.ip}:{VM_PORT}/task/{task.index}"
    task_start_time = None
    task_finish_time = None
    task_exec_time = -1.0
    task_wait_time = -1.0
    
    wait_start_mono = time.monotonic()
    
    try:
        async with vm_semaphore:
            task_wait_time = time.monotonic() - wait_start_mono
            print(f"Mengeksekusi {task.name} (idx: {task.id}) di {vm.name} (IP: {vm.ip})...")
            
            task_start_mono = time.monotonic()
            task_start_time = datetime.now()
            
            response = await client.get(url, timeout=300.0)
            response.raise_for_status()
            
            task_finish_time = datetime.now()
            task_exec_time = time.monotonic() - task_start_mono
            
            print(f"Selesai {task.name} (idx: {task.id}) di {vm.name}. Waktu: {task_exec_time:.4f}s")
            
    except Exception as e:
        print(f"Error pada {task.name} di {vm.name}: {e}", file=sys.stderr)
        
    finally:
        if task_start_time is None: task_start_time = datetime.now()
        if task_finish_time is None: task_finish_time = datetime.now()
            
        results_list.append({
            "index": task.id,
            "task_name": task.name,
            "vm_assigned": vm.name,
            "start_time": task_start_time,
            "exec_time": task_exec_time,
            "finish_time": task_finish_time,
            "wait_time": task_wait_time
        })

# --- Fungsi Paska-Proses & Metrik ---

def write_results_to_csv(results_list: list, algorithm_name: str):
    """Menyimpan hasil eksekusi ke file CSV."""
    if not results_list:
        print("Tidak ada hasil untuk ditulis ke CSV.", file=sys.stderr)
        return

    results_list.sort(key=lambda x: x['index'])
    headers = ["index", "task_name", "vm_assigned", "start_time", "exec_time", "finish_time", "wait_time"]
    
    formatted_results = []
    min_start = min(item['start_time'] for item in results_list)
    for r in results_list:
        new_r = r.copy()
        new_r['start_time'] = (r['start_time'] - min_start).total_seconds()
        new_r['finish_time'] = (r['finish_time'] - min_start).total_seconds()
        formatted_results.append(new_r)

    formatted_results.sort(key=lambda item: item['start_time'])
    
    filename = f"{RESULTS_FILE_PREFIX}{algorithm_name}.csv"

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(formatted_results)
        print(f"\nData hasil eksekusi disimpan ke {filename}")
    except IOError as e:
        print(f"Error menulis ke CSV {filename}: {e}", file=sys.stderr)

def calculate_and_print_metrics(results_list: list, vms: list[VM], total_schedule_time: float):
    """Menghitung dan menampilkan metrik kinerja."""
    try:
        df = pd.DataFrame(results_list)
    except pd.errors.EmptyDataError:
        print("Error: Hasil kosong, tidak ada metrik untuk dihitung.", file=sys.stderr)
        return
    except ImportError:
        print("Error: Library 'pandas' tidak ditemukan. Harap install pandas untuk menghitung metrik.", file=sys.stderr)
        return

    success_df = df[df['exec_time'] > 0].copy()
    if success_df.empty:
        print("Tidak ada tugas yang berhasil diselesaikan. Metrik tidak dapat dihitung.")
        return

    num_tasks = len(success_df)
    total_cpu_time = success_df['exec_time'].sum()
    total_wait_time = success_df['wait_time'].sum()
    avg_exec_time = success_df['exec_time'].mean()
    makespan = total_schedule_time
    throughput = num_tasks / makespan if makespan > 0 else 0
    
    # Calculate Relative Times
    min_start_time = success_df['start_time'].min()
    relative_start_times = (success_df['start_time'] - min_start_time).dt.total_seconds()
    relative_finish_times = (success_df['finish_time'] - min_start_time).dt.total_seconds()
    
    avg_start_time_rel = relative_start_times.mean()
    avg_finish_time_rel = relative_finish_times.mean()
    
    vm_exec_times = success_df.groupby('vm_assigned')['exec_time'].sum()
    max_load = vm_exec_times.max()
    min_load = vm_exec_times.min()
    avg_load = vm_exec_times.mean()
    imbalance_degree = (max_load - min_load) / avg_load if avg_load > 0 else 0
    
    total_cores = sum(vm.cpu_cores for vm in vms)
    total_available_cpu_time = makespan * total_cores
    resource_utilization = total_cpu_time / total_available_cpu_time if total_available_cpu_time > 0 else 0

    print("\n--- Hasil Metrik ---")
    print(f"Total tugas selesai   : {num_tasks}")
    print(f"Makespan              : {makespan:.4f} s")
    print(f"Throughput            : {throughput:.4f} tasks/s")
    print(f"Total CPU Time        : {total_cpu_time:.4f} s")
    print(f"Total Wait Time       : {total_wait_time:.4f} s")
    print(f"Avg Start Time (rel)  : {avg_start_time_rel:.4f} s")
    print(f"Avg Execution Time    : {avg_exec_time:.4f} s")
    print(f"Avg Finish Time (rel) : {avg_finish_time_rel:.4f} s")
    print(f"Imbalance Degree      : {imbalance_degree:.4f}")
    print(f"Resource Utilization  : {resource_utilization:.4%}")

# --- Fungsi Main ---

async def main():
    parser = argparse.ArgumentParser(description="Scheduler Task dengan berbagai algoritma.")
    parser.add_argument('--algo', type=str, default='heft', choices=['heft', 'shc', 'rr', 'fcfs'],
                        help='Algoritma scheduling yang digunakan (default: heft)')
    parser.add_argument('--dataset', type=str, default='random_simple.txt', choices=['random_simple.txt', 'low-high.txt', 'random_stratified.txt'],
                        help='Path ke file dataset tugas (default: random_simple.txt)')
    args = parser.parse_args()
    
    # 1. Inisialisasi
    tasks = load_tasks(args.dataset)
    if not tasks:
        print("Tidak ada tugas untuk dijadwalkan. Keluar.", file=sys.stderr)
        return
    tasks_dict = {task.id: task for task in tasks}

    # 2. Jalankan Algoritma Penjadwalan
    scheduler = TaskScheduler()
    vms = scheduler.vms
    vms_dict = {vm.name: vm for vm in vms}

    best_assignment = scheduler.run_scheduler(tasks, args.algo)
    
    # 3. Siapkan Eksekusi
    results_list = []
    vm_semaphores = {vm.name: asyncio.Semaphore(vm.cpu_cores) for vm in vms}
    
    async with httpx.AsyncClient() as client:
        all_task_coroutines = []
        for task_id, vm_name in best_assignment.items():
            if task_id not in tasks_dict:
                print(f"Peringatan: task_id {task_id} dari scheduler tidak ada di tasks_dict.")
                continue
            if vm_name not in vms_dict:
                print(f"Peringatan: vm_name {vm_name} dari scheduler tidak ada di vms_dict.")
                continue

            task = tasks_dict[task_id]
            vm = vms_dict[vm_name]
            sem = vm_semaphores[vm_name]
            
            all_task_coroutines.append(
                execute_task_on_vm(task, vm, client, sem, results_list)
            )
            
        print(f"\nMemulai eksekusi {len(all_task_coroutines)} tugas secara paralel...")
        
        # 4. Jalankan Semua Tugas
        schedule_start_time = time.monotonic()
        await asyncio.gather(*all_task_coroutines)
        schedule_end_time = time.monotonic()
        total_schedule_time = schedule_end_time - schedule_start_time
        
        print(f"\nSemua eksekusi tugas selesai dalam {total_schedule_time:.4f} detik.")
    
    # 5. Simpan Hasil dan Hitung Metrik
    write_results_to_csv(results_list, args.algo)
    calculate_and_print_metrics(results_list, vms, total_schedule_time)

if __name__ == "__main__":
    asyncio.run(main())