import json
import os
import subprocess
import yaml
import tempfile
from typing import Dict, Optional
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class ChaosMeshStressInjector:
    def __init__(self, namespace: str):
        self.namespace = namespace
        self.active_experiments: Dict[str, str] = {}  # experiment_name -> experiment_kind
        self._ensure_chaos_mesh_installed()
        self._recover_all_experiments() # cleanup namespace

    def _run_command(self, command: str) -> tuple[bool, str]:
        """Run a shell command and return success status and output"""
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                check=False
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)

    def _ensure_chaos_mesh_installed(self):
        """Ensure Chaos Mesh is installed in the cluster"""
        
        # Check if chaos-mesh is installed
        success, _ = self._run_command("kubectl get pods -n chaos-mesh")
        if not success:
            logging.error("❌ Chaos Mesh not installed in the cluster...")
            exit(1)

    def _recover_all_experiments(self):
        """Recover all active experiments"""
        
        command = f"kubectl delete stresschaos --all -n {self.namespace}"
        success, output = self._run_command(command)
        if success:
            logging.info("Namespace cleanup: All stress chaos experiments deleted successfully")
            self.active_experiments.clear()
        else:
            logging.error(f"Failed to recover all stress chaos experiments: {output}")
        return success

    def _create_chaos_experiment(self, experiment_yaml: dict, experiment_name: str):
        """Apply chaos experiment to the cluster"""
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(experiment_yaml, f, default_flow_style=False)
            temp_file_path = f.name

        try:
            # Apply the experiment
            command = f"kubectl apply -f {temp_file_path}"
            success, output = self._run_command(command)
            if success:
                logging.info(f"Applied {experiment_name} chaos experiment successfully, yaml at {temp_file_path}")
                # Add to active experiments tracking
                self.active_experiments[experiment_name] = "StressChaos"
            else:
                logging.error(f"Failed to apply {experiment_name} chaos experiment: {output}")
            return success
        finally:
            pass

    def _delete_chaos_experiment(self, experiment_name: str, kind: str):
        """Delete chaos experiment from the cluster"""
        command = f"kubectl delete {kind} {experiment_name} -n {self.namespace}"
        success, output = self._run_command(command)
        if success:
            logging.info(f"Deleted {experiment_name} chaos experiment successfully")
            # Remove from active experiments tracking
            self.active_experiments.pop(experiment_name, None)
        else:
            logging.error(f"Failed to delete {experiment_name} chaos experiment: {output}")
        return success

    def inject_cpu_stress(self, microservice: str, duration: str = "5m", 
                         workers: int = 1, load: int = 100, mode: str = "one",
                         experiment_name: Optional[str] = None):
        """
        Inject CPU stress on a specified microservice.
        
        Args:
            microservice (str): Microservice name to target (app label value)
            duration (str): Duration of the stress test (e.g., "30s", "5m")
            workers (int): Number of CPU workers
            load (int): CPU load percentage (0-100)
            mode (str): Selection mode ("one", "all", "fixed", etc.)
            experiment_name (str): Optional custom name for the experiment
        """
        if experiment_name is None:
            experiment_name = f"burn-cpu-{microservice}"


        # Check if experiment with this name already exists
        if experiment_name in self.active_experiments:
            success = self._check_if_terminated_and_succeeded(experiment_name)

            if success:
                # Experiment is terminated, delete it and continue
                self._delete_chaos_experiment(experiment_name, self.active_experiments[experiment_name])
                time.sleep(1)
            else:
                logging.error(f"Experiment {experiment_name} already exists and is in progress")
                return False
            
        chaos_experiment = {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "StressChaos",
            "metadata": {
                "name": experiment_name,
                "namespace": self.namespace
            },
            "spec": {
                "mode": mode,
                "selector": {
                    "labelSelectors": {
                        "app": microservice
                    }
                },
                "stressors": {
                    "cpu": {
                        "workers": workers,
                        "load": load
                    }
                },
                "duration": duration
            }
        }

        return self._create_chaos_experiment(chaos_experiment, experiment_name)

    def _check_if_terminated_and_succeeded(self, experiment_name: str) -> bool:
        """
        Check if experiment with this name already exists and if is terminated.

        Args:
            experiment_name (str): Specific experiment name to remove
        """

        if experiment_name in self.active_experiments:
            
            logging.info(f"Checking status of existing experiment {experiment_name}...")
            
            # Check if the experiment is terminated
            command = f"kubectl get {self.active_experiments[experiment_name]} {experiment_name} -n {self.namespace}" 
            
            # first check if injectedCount is 0, meaning it has not started yet
            command_tmp = command + " -o jsonpath='{.status.experiment.containerRecords[0].injectedCount}'"
            
            success, output = self._run_command(command_tmp)
            if success:
                injected_count = int(output.strip().replace("'", ""))
                if injected_count == 0:
                    logging.info(f"Experiment {experiment_name} exists but has not started yet.")
                    return False
            
            # if started, check if it is terminated and succeeded
            command_tmp = command + " -o jsonpath='{.status.experiment.containerRecords[0].events}'"
            success, output = self._run_command(command_tmp)

            output = json.loads(output.replace("'", "\"")) if success else ""
            
            for event in output:
                if event["operation"]=="Recover" and event["type"]=="Succeeded":
                    return True
            
        return False
        
    
    def recover_cpu_stress(self, experiment_name: Optional[str] = None, microservice: Optional[str] = None):
        """
        Remove CPU stress chaos experiment
        
        Args:
            experiment_name (str): Specific experiment name to remove
            microservice (str): Microservice name (will use default naming pattern)
        """
        if experiment_name is None and microservice is not None:
            experiment_name = f"burn-cpu-{microservice}"
        elif experiment_name is None:
            logging.error("Must provide either experiment_name or microservice")
            return False
            
        if experiment_name not in self.active_experiments:
            logging.error(f"No active experiment found with name {experiment_name}")
            return False
            
        return self._delete_chaos_experiment(experiment_name, "StressChaos")

    def inject_memory_stress(self, microservice: str, duration: str = "30s",
                           workers: int = 1, size: str = "70%", mode: str = "one",
                           experiment_name: Optional[str] = None):
        """
        Inject memory stress on a specified microservice.
        
        Args:
            microservice (str): Microservice name to target (app label value)
            duration (str): Duration of the stress test (e.g., "30s", "5m")
            workers (int): Number of memory workers
            size (str): Memory size to allocate (e.g., "70%", "1GB", "500MB")
            mode (str): Selection mode ("one", "all", "fixed", etc.)
            experiment_name (str): Optional custom name for the experiment
        """
        if experiment_name is None:
            experiment_name = f"pod-oom-{microservice}"

        # Check if experiment with this name already exists
        if experiment_name in self.active_experiments:

            success = self._check_if_terminated_and_succeeded(experiment_name)

            if success:
                # Experiment is terminated, delete it and continue
                self._delete_chaos_experiment(experiment_name, self.active_experiments[experiment_name])
                time.sleep(1)
            else:
                logging.error(f"Experiment {experiment_name} already exists and is in progress")
                return False
            
        chaos_experiment = {
            "apiVersion": "chaos-mesh.org/v1alpha1",
            "kind": "StressChaos",
            "metadata": {
                "name": experiment_name,
                "namespace": self.namespace
            },
            "spec": {
                "mode": mode,
                "selector": {
                    "labelSelectors": {
                        "app": microservice
                    }
                },
                "stressors": {
                    "memory": {
                        "workers": workers,
                        "size": size
                    }
                },
                "duration": duration
            }
        }

        return self._create_chaos_experiment(chaos_experiment, experiment_name)

    def recover_memory_stress(self, experiment_name: Optional[str] = None, microservice: Optional[str] = None):
        """
        Remove memory stress chaos experiment
        
        Args:
            experiment_name (str): Specific experiment name to remove
            microservice (str): Microservice name (will use default naming pattern)
        """
        if experiment_name is None and microservice is not None:
            experiment_name = f"pod-oom-{microservice}"
        elif experiment_name is None:
            logging.error("Must provide either experiment_name or microservice")
            return False
            
        if experiment_name not in self.active_experiments:
            logging.error(f"No active experiment found with name {experiment_name}")
            return False
            
        return self._delete_chaos_experiment(experiment_name, "StressChaos")

    def list_active_experiments(self):
        """List all active experiments tracked by this instance"""
        if not self.active_experiments:
            logging.info("No active experiments")
            return
            
        logging.info("Active experiments:")
        for name, kind in self.active_experiments.items():
            logging.info(f"  - {name} ({kind})")

    def cleanup_all_experiments(self):
        """Clean up all tracked experiments"""
        if not self.active_experiments:
            logging.info("No experiments to clean up")
            return True
            
        results = []
        # Create a copy of the keys since we'll be modifying the dict
        experiment_names = list(self.active_experiments.keys())
        
        for experiment_name in experiment_names:
            kind = self.active_experiments[experiment_name]
            result = self._delete_chaos_experiment(experiment_name, kind)
            results.append(result)
            
        success = all(results)
        if success:
            logging.info("All tracked experiments cleaned up successfully")
        else:
            logging.error("Some experiments failed to cleanup")
        return success

    def get_active_experiment_count(self) -> int:
        """Get the number of currently active experiments"""
        return len(self.active_experiments)




# Example usage
if __name__ == "__main__":

    namespace = "online-boutique"
    
    # Initialize the injector
    injector = ChaosMeshStressInjector(namespace)
    
    try:
        # Inject CPU stress on productcatalogservice
        logging.info("Injecting CPU stress...")
        injector.inject_cpu_stress("productcatalogservice", duration="1m", workers=1, load=100)
        
        # Inject memory stress on recommendationservice
        logging.info("Injecting memory stress...")
        injector.inject_memory_stress("recommendationservice", duration="3m", workers=1, size="70%")
        
        time.sleep(80)

        # Inject CPU stress on productcatalogservice
        logging.info("Injecting CPU stress equal to above...")
        injector.inject_cpu_stress("productcatalogservice", duration="3m", workers=1, load=100)
        
    
        # List active experiments
        time.sleep(5)
        injector.list_active_experiments()
        logging.info(f"Total active experiments: {injector.get_active_experiment_count()}")
        
        # Wait
        time.sleep(5*60)
        
        # Recover specific experiments
        logging.info("Recovering CPU stress...")
        injector.recover_cpu_stress(microservice="productcatalogservice")
        
        logging.info("Recovering memory stress...")
        injector.recover_memory_stress(microservice="recommendationservice")
        
        # Show final state
        injector.list_active_experiments()
        logging.info(f"Total active experiments: {injector.get_active_experiment_count()}")
    except KeyboardInterrupt:
        print("Interrupted, cleaning up...")
        injector.cleanup_all_experiments()