"""
Implementasi Algoritma HEFT (Heterogeneous Earliest Finish Time)
untuk Task Scheduling pada Sistem Heterogen
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import math


@dataclass
class Task:
    """Representasi task dalam DAG"""
    id: int
    computation_cost: Dict[int, float]  # {processor_id: execution_time}
    predecessors: List[int]  # List of task IDs yang harus selesai sebelum task ini
    successors: List[int]  # List of task IDs yang bergantung pada task ini


@dataclass
class ScheduleEvent:
    """Representasi event scheduling"""
    task_id: int
    processor_id: int
    start_time: float
    finish_time: float


class HEFTAlgorithm:
    """
    Implementasi algoritma HEFT untuk task scheduling pada sistem heterogen
    """
    
    def __init__(self, tasks: List[Task], processors: List[int], 
                 communication_matrix: Optional[Dict[Tuple[int, int], float]] = None):
        """
        Inisialisasi HEFT Algorithm
        
        Args:
            tasks: List of Task objects
            processors: List of processor IDs
            communication_matrix: Dictionary mapping (from_proc, to_proc) -> communication_cost
        """
        self.tasks = {task.id: task for task in tasks}
        self.processors = processors
        self.communication_matrix = communication_matrix or {}
        self.schedule: Dict[int, ScheduleEvent] = {}  # task_id -> ScheduleEvent
        self.processor_availability: Dict[int, float] = {p: 0.0 for p in processors}
        self.avg_computation_cost: Dict[int, float] = {}
        self.upward_ranks: Dict[int, float] = {}
        
    def _calculate_average_computation_cost(self):
        """Menghitung rata-rata computation cost untuk setiap task"""
        for task_id, task in self.tasks.items():
            if task.computation_cost:
                self.avg_computation_cost[task_id] = sum(task.computation_cost.values()) / len(task.computation_cost)
            else:
                self.avg_computation_cost[task_id] = 0.0
    
    def _calculate_average_communication_cost(self, from_task_id: int, to_task_id: int) -> float:
        """
        Menghitung rata-rata communication cost antara dua task
        
        Args:
            from_task_id: ID task sumber
            to_task_id: ID task tujuan
            
        Returns:
            Average communication cost
        """
        if not self.communication_matrix:
            return 0.0
        
        # Jika ada communication cost spesifik antara processors
        total_cost = 0.0
        count = 0
        
        for from_proc in self.processors:
            for to_proc in self.processors:
                if from_proc != to_proc:
                    key = (from_proc, to_proc)
                    if key in self.communication_matrix:
                        total_cost += self.communication_matrix[key]
                        count += 1
        
        if count > 0:
            return total_cost / count
        return 0.0
    
    def _calculate_upward_rank(self, task_id: int) -> float:
        """
        Menghitung upward rank untuk task (recursive)
        
        Upward rank = avg_computation_cost + max(successor_rank + avg_communication_cost)
        
        Args:
            task_id: ID task yang akan dihitung rank-nya
            
        Returns:
            Upward rank value
        """
        if task_id in self.upward_ranks:
            return self.upward_ranks[task_id]
        
        task = self.tasks[task_id]
        
        # Base case: jika tidak ada successor
        if not task.successors:
            self.upward_ranks[task_id] = self.avg_computation_cost[task_id]
            return self.upward_ranks[task_id]
        
        # Recursive case: hitung max dari semua successor
        max_successor_rank = 0.0
        for successor_id in task.successors:
            successor_rank = self._calculate_upward_rank(successor_id)
            comm_cost = self._calculate_average_communication_cost(task_id, successor_id)
            max_successor_rank = max(max_successor_rank, successor_rank + comm_cost)
        
        self.upward_ranks[task_id] = self.avg_computation_cost[task_id] + max_successor_rank
        return self.upward_ranks[task_id]
    
    def _calculate_earliest_start_time(self, task_id: int, processor_id: int) -> float:
        """
        Menghitung earliest start time untuk task pada processor tertentu
        
        Args:
            task_id: ID task
            processor_id: ID processor
            
        Returns:
            Earliest start time
        """
        task = self.tasks[task_id]
        
        # EST = max(processor_availability, max(predecessor_finish_time + communication_cost))
        est = self.processor_availability[processor_id]
        
        # Cek semua predecessor
        for pred_id in task.predecessors:
            if pred_id in self.schedule:
                pred_event = self.schedule[pred_id]
                pred_finish_time = pred_event.finish_time
                
                # Jika predecessor di processor yang sama, tidak ada communication cost
                if pred_event.processor_id == processor_id:
                    comm_cost = 0.0
                else:
                    comm_key = (pred_event.processor_id, processor_id)
                    comm_cost = self.communication_matrix.get(comm_key, 0.0)
                
                est = max(est, pred_finish_time + comm_cost)
        
        return est
    
    def _calculate_earliest_finish_time(self, task_id: int, processor_id: int) -> float:
        """
        Menghitung earliest finish time untuk task pada processor tertentu
        
        Args:
            task_id: ID task
            processor_id: ID processor
            
        Returns:
            Earliest finish time
        """
        task = self.tasks[task_id]
        est = self._calculate_earliest_start_time(task_id, processor_id)
        execution_time = task.computation_cost.get(processor_id, float('inf'))
        
        if execution_time == float('inf'):
            # Jika processor tidak memiliki cost untuk task ini, gunakan average
            execution_time = self.avg_computation_cost[task_id]
        
        return est + execution_time
    
    def _select_best_processor(self, task_id: int) -> Tuple[int, float, float]:
        """
        Memilih processor terbaik untuk task berdasarkan earliest finish time
        
        Args:
            task_id: ID task
            
        Returns:
            Tuple (best_processor_id, earliest_start_time, earliest_finish_time)
        """
        best_processor = None
        best_eft = float('inf')
        best_est = 0.0
        
        for processor_id in self.processors:
            eft = self._calculate_earliest_finish_time(task_id, processor_id)
            if eft < best_eft:
                best_eft = eft
                best_processor = processor_id
                best_est = self._calculate_earliest_start_time(task_id, processor_id)
        
        return best_processor, best_est, best_eft
    
    def schedule_tasks(self) -> Dict[int, ScheduleEvent]:
        """
        Menjalankan algoritma HEFT untuk scheduling semua tasks
        
        Returns:
            Dictionary mapping task_id -> ScheduleEvent
        """
        # Phase 1: Hitung average computation cost
        self._calculate_average_computation_cost()
        
        # Phase 2: Hitung upward rank untuk semua tasks
        for task_id in self.tasks.keys():
            self._calculate_upward_rank(task_id)
        
        # Phase 3: Sort tasks berdasarkan upward rank (descending)
        sorted_tasks = sorted(
            self.tasks.keys(),
            key=lambda tid: self.upward_ranks[tid],
            reverse=True
        )
        
        # Phase 4: Schedule setiap task ke processor terbaik
        for task_id in sorted_tasks:
            best_processor, est, eft = self._select_best_processor(task_id)
            
            # Buat schedule event
            event = ScheduleEvent(
                task_id=task_id,
                processor_id=best_processor,
                start_time=est,
                finish_time=eft
            )
            
            self.schedule[task_id] = event
            self.processor_availability[best_processor] = eft
        
        return self.schedule
    
    def get_makespan(self) -> float:
        """Menghitung makespan (total waktu penyelesaian)"""
        if not self.schedule:
            return 0.0
        return max(event.finish_time for event in self.schedule.values())
    
    def get_schedule_summary(self) -> Dict:
        """Mendapatkan summary dari schedule"""
        if not self.schedule:
            return {}
        
        processor_loads = defaultdict(list)
        for event in self.schedule.values():
            processor_loads[event.processor_id].append({
                'task_id': event.task_id,
                'start_time': event.start_time,
                'finish_time': event.finish_time,
                'duration': event.finish_time - event.start_time
            })
        
        return {
            'makespan': self.get_makespan(),
            'total_tasks': len(self.schedule),
            'processor_loads': dict(processor_loads),
            'schedule': {
                task_id: {
                    'processor_id': event.processor_id,
                    'start_time': event.start_time,
                    'finish_time': event.finish_time
                }
                for task_id, event in self.schedule.items()
            }
        }

