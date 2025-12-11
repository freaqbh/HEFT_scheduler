"""
Script untuk membandingkan performa berbagai algoritma scheduling
(HEFT, SHC, RR, FCFS) secara otomatis.
"""

import subprocess
import sys
import pandas as pd
import os
import time

# Try to import matplotlib
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not found. Plotting will be skipped.")

ALGORITHMS = ['heft', 'shc', 'rr', 'fcfs']
RESULTS_PREFIX = 'results_'
SUMMARY_FILE = 'comparison_summary.csv'

def run_algorithm(algo):
    """Menjalankan scheduler.py dengan algoritma tertentu."""
    print(f"\n{'='*50}")
    print(f"Running Algorithm: {algo.upper()}")
    print(f"{'='*50}")
    
    cmd = [sys.executable, 'scheduler.py', '--algo', algo]
    
    try:
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        end_time = time.time()
        
        print(result.stdout)
        print(f"Execution finished in {end_time - start_time:.2f} seconds.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running {algo}:")
        print(e.stderr)
        return False

def collect_metrics():
    """Mengumpulkan metrik dari file CSV hasil."""
    summary_data = []
    
    for algo in ALGORITHMS:
        filename = f"{RESULTS_PREFIX}{algo}.csv"
        if not os.path.exists(filename):
            print(f"Warning: Result file {filename} not found.")
            continue
            
        try:
            df = pd.read_csv(filename)
            
            # Hitung metrik ulang atau ambil dari log (di sini kita hitung ulang dari CSV)
            if df.empty:
                continue
                
            # Convert timestamps
            # Asumsi start_time dan finish_time di CSV sudah dalam seconds relative
            
            makespan = df['finish_time'].max()
            total_wait_time = df['wait_time'].sum()
            avg_exec_time = df['exec_time'].mean()
            
            # Hitung imbalance
            vm_loads = df.groupby('vm_assigned')['exec_time'].sum()
            imbalance = (vm_loads.max() - vm_loads.min()) / vm_loads.mean() if not vm_loads.empty else 0
            
            summary_data.append({
                'Algorithm': algo.upper(),
                'Makespan (s)': makespan,
                'Total Wait Time (s)': total_wait_time,
                'Avg Exec Time (s)': avg_exec_time,
                'Imbalance Degree': imbalance
            })
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            
    return pd.DataFrame(summary_data)

def plot_comparison(df):
    """Membuat plot perbandingan."""
    if df.empty or not MATPLOTLIB_AVAILABLE:
        return
        
    # Plot Makespan
    plt.figure(figsize=(10, 6))
    plt.bar(df['Algorithm'], df['Makespan (s)'], color=['blue', 'green', 'orange', 'red'])
    plt.title('Makespan Comparison (Lower is Better)')
    plt.ylabel('Time (seconds)')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.savefig('comparison_makespan.png')
    print("Saved plot to comparison_makespan.png")
    
    # Plot Imbalance
    plt.figure(figsize=(10, 6))
    plt.bar(df['Algorithm'], df['Imbalance Degree'], color=['blue', 'green', 'orange', 'red'])
    plt.title('Imbalance Degree Comparison (Lower is Better)')
    plt.ylabel('Imbalance Degree')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.savefig('comparison_imbalance.png')
    print("Saved plot to comparison_imbalance.png")

def main():
    # 1. Run semua algoritma
    for algo in ALGORITHMS:
        run_algorithm(algo)
        # Beri jeda sedikit agar tidak konflik resource (opsional)
        time.sleep(1)
        
    # 2. Collect metrics
    df = collect_metrics()
    
    if not df.empty:
        print("\n=== Comparison Summary ===")
        print(df.to_string(index=False))
        
        # Simpan summary
        df.to_csv(SUMMARY_FILE, index=False)
        print(f"\nSummary saved to {SUMMARY_FILE}")
        
        # 3. Plotting (jika matplotlib tersedia)
        try:
            plot_comparison(df)
        except Exception as e:
            print(f"Could not generate plots: {e}")
    else:
        print("No results collected.")

if __name__ == "__main__":
    main()
