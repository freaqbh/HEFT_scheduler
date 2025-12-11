"""
Implementasi Algoritma FCFS (First-Come First-Served)
untuk Task Scheduling
"""

from typing import List, Dict, Tuple
from dataclasses import dataclass
from heft_algorithm import Task, ScheduleEvent

class FCFSAlgorithm:
    """
    Implementasi algoritma FCFS untuk task scheduling.
    Tasks dijadwalkan berdasarkan urutan kedatangan (ID/Index) ke processor pertama yang tersedia.
    """
    
    def __init__(self, tasks: List[Task], processors: List[int]):
        """
        Inisialisasi FCFS Algorithm
        
        Args:
            tasks: List of Task objects
            processors: List of processor IDs
        """
        self.tasks = sorted(tasks, key=lambda t: t.id) # Sort by ID (arrival order)
        self.processors = processors
        self.schedule: Dict[int, ScheduleEvent] = {}
        self.processor_availability: Dict[int, float] = {p: 0.0 for p in processors}
        
    def schedule_tasks(self) -> Dict[int, ScheduleEvent]:
        """
        Menjalankan algoritma FCFS
        
        Returns:
            Dictionary mapping task_id -> ScheduleEvent
        """
        for task in self.tasks:
            # Cari processor yang paling cepat available (Earliest Available Machine)
            # Dalam FCFS murni, kita biasanya assign ke resource yang free duluan.
            
            best_processor = self.processors[0]
            earliest_start = float('inf')
            
            # Simple load balancing: pilih processor dengan availability time terkecil
            best_processor = min(self.processors, key=lambda p: self.processor_availability[p])
            start_time = self.processor_availability[best_processor]
            
            # Hitung execution time
            # Note: Di FCFS biasanya kita tidak tahu cost di tiap processor,
            # tapi karena kita punya datanya, kita pakai cost di processor tsb.
            exec_time = task.computation_cost.get(best_processor, 0.0)
            if exec_time == 0.0 and task.computation_cost:
                 # Fallback jika tidak ada data spesifik, pakai rata-rata
                 exec_time = sum(task.computation_cost.values()) / len(task.computation_cost)

            finish_time = start_time + exec_time
            
            # Update schedule
            event = ScheduleEvent(
                task_id=task.id,
                processor_id=best_processor,
                start_time=start_time,
                finish_time=finish_time
            )
            self.schedule[task.id] = event
            self.processor_availability[best_processor] = finish_time
            
        return self.schedule

    def get_makespan(self) -> float:
        """Menghitung makespan"""
        if not self.schedule:
            return 0.0
        return max(event.finish_time for event in self.schedule.values())
