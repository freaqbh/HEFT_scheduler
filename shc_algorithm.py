import random
import copy
from typing import List, Dict, Tuple
from heft_algorithm import Task, ScheduleEvent

class SHCAlgorithm:
    """
    Implementasi algoritma Stochastic Hill Climbing untuk task scheduling.
    Mencari solusi optimal lokal dengan melakukan mutasi acak pada assignment.
    """
    
    def __init__(self, tasks: List[Task], processors: List[int], max_iterations: int = 1000):
        """
        Inisialisasi SHC Algorithm
        
        Args:
            tasks: List of Task objects
            processors: List of processor IDs
            max_iterations: Jumlah iterasi maksimum untuk pencarian solusi
        """
        self.tasks = tasks
        self.processors = processors
        self.max_iterations = max_iterations
        self.best_schedule: Dict[int, ScheduleEvent] = {}
        self.best_makespan = float('inf')
        
    def _calculate_schedule_makespan(self, assignment: Dict[int, int]) -> Tuple[float, Dict[int, ScheduleEvent]]:
        """
        Menghitung makespan untuk assignment tertentu
        
        Args:
            assignment: Dict mapping task_id -> processor_id
            
        Returns:
            Tuple (makespan, schedule_events)
        """
        schedule = {}
        processor_availability = {p: 0.0 for p in self.processors}
        
        # Sort tasks by ID to ensure deterministic order for evaluation
        sorted_tasks = sorted(self.tasks, key=lambda t: t.id)
        
        for task in sorted_tasks:
            processor_id = assignment[task.id]
            start_time = processor_availability[processor_id]
            
            exec_time = task.computation_cost.get(processor_id, 0.0)
            if exec_time == 0.0 and task.computation_cost:
                 exec_time = sum(task.computation_cost.values()) / len(task.computation_cost)
            
            finish_time = start_time + exec_time
            
            event = ScheduleEvent(
                task_id=task.id,
                processor_id=processor_id,
                start_time=start_time,
                finish_time=finish_time
            )
            schedule[task.id] = event
            processor_availability[processor_id] = finish_time
            
        makespan = max(processor_availability.values())
        return makespan, schedule

    def schedule_tasks(self) -> Dict[int, ScheduleEvent]:
        """
        Menjalankan algoritma SHC
        
        Returns:
            Dictionary mapping task_id -> ScheduleEvent (Best Solution Found)
        """
        # 1. Initial Solution: Random Assignment
        current_assignment = {task.id: random.choice(self.processors) for task in self.tasks}
        current_makespan, current_schedule = self._calculate_schedule_makespan(current_assignment)
        
        self.best_schedule = current_schedule
        self.best_makespan = current_makespan
        
        # 2. Hill Climbing Loop
        for _ in range(self.max_iterations):
            # Generate Neighbor: Mutasi satu task ke processor lain
            neighbor_assignment = current_assignment.copy()
            
            # Pilih random task dan random processor baru
            random_task = random.choice(self.tasks)
            new_processor = random.choice(self.processors)
            
            neighbor_assignment[random_task.id] = new_processor
            
            # Evaluasi Neighbor
            neighbor_makespan, neighbor_schedule = self._calculate_schedule_makespan(neighbor_assignment)
            
            # Jika lebih baik atau sama, pindah ke neighbor (Stochastic part could be added here, e.g. accept worse with prob)
            # Untuk simple Hill Climbing, kita hanya terima jika lebih baik atau sama
            if neighbor_makespan <= current_makespan:
                current_assignment = neighbor_assignment
                current_makespan = neighbor_makespan
                current_schedule = neighbor_schedule
                
                # Update global best
                if current_makespan < self.best_makespan:
                    self.best_makespan = current_makespan
                    self.best_schedule = current_schedule
        
        return self.best_schedule

    def get_makespan(self) -> float:
        """Menghitung makespan terbaik yang ditemukan"""
        return self.best_makespan
