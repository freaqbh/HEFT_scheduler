"""
Implementasi Algoritma Round Robin (RR)
untuk Task Scheduling
"""

from typing import List, Dict
from heft_algorithm import Task, ScheduleEvent

class RRAlgorithm:
    """
    Implementasi algoritma Round Robin untuk task scheduling.
    Tasks didistribusikan secara bergilir ke setiap processor.
    """
    
    def __init__(self, tasks: List[Task], processors: List[int]):
        """
        Inisialisasi RR Algorithm
        
        Args:
            tasks: List of Task objects
            processors: List of processor IDs
        """
        self.tasks = sorted(tasks, key=lambda t: t.id)
        self.processors = processors
        self.schedule: Dict[int, ScheduleEvent] = {}
        self.processor_availability: Dict[int, float] = {p: 0.0 for p in processors}
        
    def schedule_tasks(self) -> Dict[int, ScheduleEvent]:
        """
        Menjalankan algoritma Round Robin
        
        Returns:
            Dictionary mapping task_id -> ScheduleEvent
        """
        num_processors = len(self.processors)
        
        for i, task in enumerate(self.tasks):
            # Pilih processor secara bergilir (Round Robin)
            processor_idx = i % num_processors
            processor_id = self.processors[processor_idx]
            
            start_time = self.processor_availability[processor_id]
            
            # Hitung execution time
            exec_time = task.computation_cost.get(processor_id, 0.0)
            if exec_time == 0.0 and task.computation_cost:
                 exec_time = sum(task.computation_cost.values()) / len(task.computation_cost)

            finish_time = start_time + exec_time
            
            # Update schedule
            event = ScheduleEvent(
                task_id=task.id,
                processor_id=processor_id,
                start_time=start_time,
                finish_time=finish_time
            )
            self.schedule[task.id] = event
            self.processor_availability[processor_id] = finish_time
            
        return self.schedule

    def get_makespan(self) -> float:
        """Menghitung makespan"""
        if not self.schedule:
            return 0.0
        return max(event.finish_time for event in self.schedule.values())
