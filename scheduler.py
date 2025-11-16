"""
Scheduler menggunakan algoritma HEFT untuk task scheduling
Berinteraksi dengan server-server VM untuk eksekusi task
"""

import os
import sys
import requests
import time
import csv
from typing import List, Dict, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
from heft_algorithm import HEFTAlgorithm, Task, ScheduleEvent

# Load environment variables
load_dotenv()


@dataclass
class ServerConfig:
    """Konfigurasi server VM"""
    ip: str
    port: int
    id: int


class TaskScheduler:
    """
    Task Scheduler menggunakan algoritma HEFT
    """
    
    def __init__(self):
        """Inisialisasi scheduler dengan konfigurasi dari .env"""
        self.servers = self._load_server_config()
        self.processors = [server.id for server in self.servers]
        self.communication_matrix = self._initialize_communication_matrix()
        
    def _load_server_config(self) -> List[ServerConfig]:
        """Load konfigurasi server dari environment variables"""
        servers = []
        port = int(os.getenv('VM_PORT', 5000))
        
        vm_configs = [
            ('VM1_IP', 1),
            ('VM2_IP', 2),
            ('VM3_IP', 3),
            ('VM4_IP', 4)
        ]
        
        for vm_ip_env, server_id in vm_configs:
            ip = os.getenv(vm_ip_env)
            if ip:
                servers.append(ServerConfig(ip=ip, port=port, id=server_id))
        
        if not servers:
            raise ValueError("Tidak ada server yang dikonfigurasi. Pastikan file .env sudah diisi dengan benar.")
        
        print(f"Loaded {len(servers)} server(s): {[s.ip for s in servers]}")
        return servers
    
    def _initialize_communication_matrix(self) -> Dict[tuple, float]:
        """
        Inisialisasi communication matrix antar processor
        Default: uniform communication cost
        """
        matrix = {}
        for from_proc in self.processors:
            for to_proc in self.processors:
                if from_proc != to_proc:
                    # Default communication cost (dapat disesuaikan)
                    matrix[(from_proc, to_proc)] = 1.0
        return matrix
    
    def _load_dataset(self, filename: str = 'dataset.txt') -> List[int]:
        """
        Load dataset dari file
        
        Args:
            filename: Nama file dataset
            
        Returns:
            List of task values
        """
        if not os.path.exists(filename):
            raise FileNotFoundError(f"File {filename} tidak ditemukan. Buat file dataset.txt terlebih dahulu.")
        
        with open(filename, 'r') as f:
            tasks = [int(line.strip()) for line in f if line.strip()]
        
        print(f"Loaded {len(tasks)} tasks from {filename}")
        return tasks
    
    def _create_task_dag(self, task_values: List[int]) -> List[Task]:
        """
        Membuat DAG (Directed Acyclic Graph) dari task values
        Untuk contoh sederhana, kita buat linear DAG atau dapat disesuaikan
        
        Args:
            task_values: List of task values dari dataset
            
        Returns:
            List of Task objects
        """
        tasks = []
        num_tasks = len(task_values)
        
        # Buat linear DAG: task i bergantung pada task i-1
        for i, value in enumerate(task_values):
            predecessors = [i - 1] if i > 0 else []
            successors = [i + 1] if i < num_tasks - 1 else []
            
            # Computation cost untuk setiap processor
            # Rumus: endpoint² * 10000 (dimana endpoint adalah task value)
            base_cost = (value ** 2) * 10000
            computation_cost = {}
            for server in self.servers:
                computation_cost[server.id] = base_cost
            
            task = Task(
                id=i,
                computation_cost=computation_cost,
                predecessors=predecessors,
                successors=successors
            )
            tasks.append(task)
        
        return tasks
    
    def _execute_task_on_server(self, server: ServerConfig, task_value: int) -> Dict:
        """
        Mengirim request ke server untuk execute task
        
        Args:
            server: ServerConfig object
            task_value: Nilai task yang akan dieksekusi
            
        Returns:
            Response dari server
        """
        url = f"http://{server.ip}:{server.port}/execute"
        
        try:
            response = requests.post(
                url,
                json={'value': task_value},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error executing task on server {server.ip}: {e}")
            return {'error': str(e), 'execution_time': None}
    
    def _execute_schedule(self, schedule: Dict[int, ScheduleEvent], 
                         task_values: List[int]) -> Dict:
        """
        Mengeksekusi schedule yang telah dibuat
        
        Args:
            schedule: Dictionary mapping task_id -> ScheduleEvent
            task_values: List of task values
            
        Returns:
            Dictionary berisi hasil eksekusi
        """
        # Sort schedule berdasarkan start_time
        sorted_schedule = sorted(
            schedule.items(),
            key=lambda x: x[1].start_time
        )
        
        execution_results = {}
        actual_start_times = {}
        actual_finish_times = {}
        
        print("\n=== Eksekusi Schedule ===")
        
        for task_id, event in sorted_schedule:
            task_value = task_values[task_id]
            server = next(s for s in self.servers if s.id == event.processor_id)
            
            # Wait sampai start_time
            current_time = time.time()
            wait_time = max(0, event.start_time - current_time)
            if wait_time > 0:
                print(f"Task {task_id} menunggu {wait_time:.2f} detik...")
                time.sleep(wait_time)
            
            # Execute task
            print(f"Task {task_id} (value={task_value}) dieksekusi di Server {server.id} ({server.ip})")
            start_time = time.time()
            
            result = self._execute_task_on_server(server, task_value)
            
            finish_time = time.time()
            execution_time = finish_time - start_time
            
            actual_start_times[task_id] = start_time
            actual_finish_times[task_id] = finish_time
            
            execution_results[task_id] = {
                'task_value': task_value,
                'server_id': server.id,
                'server_ip': server.ip,
                'scheduled_start': event.start_time,
                'scheduled_finish': event.finish_time,
                'actual_start': start_time,
                'actual_finish': finish_time,
                'execution_time': execution_time,
                'server_response': result
            }
            
            print(f"  -> Selesai dalam {execution_time:.2f} detik")
        
        return {
            'execution_results': execution_results,
            'actual_start_times': actual_start_times,
            'actual_finish_times': actual_finish_times
        }
    
    def _save_results_to_csv(self, schedule: Dict[int, ScheduleEvent],
                            execution_results: Dict, task_values: List[int],
                            filename: str = 'result.csv'):
        """
        Menyimpan hasil scheduling ke CSV
        
        Args:
            schedule: Dictionary mapping task_id -> ScheduleEvent
            execution_results: Hasil eksekusi
            task_values: List of task values
            filename: Nama file output
        """
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Task ID',
                'Task Value',
                'Processor ID',
                'Scheduled Start',
                'Scheduled Finish',
                'Actual Start',
                'Actual Finish',
                'Execution Time',
                'Makespan'
            ])
            
            makespan = max(event.finish_time for event in schedule.values())
            
            for task_id in sorted(schedule.keys()):
                event = schedule[task_id]
                exec_result = execution_results.get('execution_results', {}).get(task_id, {})
                
                writer.writerow([
                    task_id,
                    task_values[task_id],
                    event.processor_id,
                    f"{event.start_time:.2f}",
                    f"{event.finish_time:.2f}",
                    f"{exec_result.get('actual_start', 0):.2f}",
                    f"{exec_result.get('actual_finish', 0):.2f}",
                    f"{exec_result.get('execution_time', 0):.2f}",
                    f"{makespan:.2f}"
                ])
        
        print(f"\nHasil disimpan ke {filename}")
    
    def run(self, dataset_file: str = 'dataset.txt'):
        """
        Menjalankan scheduler dengan dataset
        
        Args:
            dataset_file: Nama file dataset
        """
        print("=" * 60)
        print("HEFT Task Scheduler")
        print("=" * 60)
        
        # Load dataset
        task_values = self._load_dataset(dataset_file)
        
        # Buat DAG dari tasks
        tasks = self._create_task_dag(task_values)
        
        # Inisialisasi HEFT algorithm
        heft = HEFTAlgorithm(
            tasks=tasks,
            processors=self.processors,
            communication_matrix=self.communication_matrix
        )
        
        # Jalankan scheduling
        print("\n=== Phase 1: Task Prioritization ===")
        schedule = heft.schedule_tasks()
        
        # Tampilkan hasil scheduling
        print("\n=== Hasil Scheduling ===")
        summary = heft.get_schedule_summary()
        print(f"Makespan: {summary['makespan']:.2f}")
        print(f"Total Tasks: {summary['total_tasks']}")
        
        print("\n=== Detail Schedule ===")
        for task_id in sorted(schedule.keys()):
            event = schedule[task_id]
            print(f"Task {task_id}: Processor {event.processor_id}, "
                  f"Start={event.start_time:.2f}, Finish={event.finish_time:.2f}")
        
        print("\n=== Processor Loads ===")
        for proc_id, loads in summary['processor_loads'].items():
            total_time = sum(load['duration'] for load in loads)
            print(f"Processor {proc_id}: {len(loads)} tasks, Total time: {total_time:.2f}")
        
        # Eksekusi schedule (jika server tersedia)
        print("\n=== Eksekusi Schedule ===")
        try:
            execution_results = self._execute_schedule(schedule, task_values)
            
            # Simpan hasil ke CSV
            self._save_results_to_csv(schedule, execution_results, task_values)
            
            # Hitung parameter analisis
            print("\n=== Parameter Analisis ===")
            actual_makespan = max(
                exec_result.get('actual_finish', 0)
                for exec_result in execution_results.get('execution_results', {}).values()
            )
            if actual_makespan > 0:
                print(f"Actual Makespan: {actual_makespan:.2f}")
                print(f"Scheduled Makespan: {summary['makespan']:.2f}")
                print(f"Deviation: {abs(actual_makespan - summary['makespan']):.2f}")
        except Exception as e:
            print(f"Error saat eksekusi: {e}")
            print("Menyimpan schedule tanpa hasil eksekusi...")
            self._save_results_to_csv(schedule, {}, task_values)


def main():
    """Main function"""
    try:
        scheduler = TaskScheduler()
        scheduler.run()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

