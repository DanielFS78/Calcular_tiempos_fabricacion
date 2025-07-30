# simulation_engine.py

import logging
from collections import deque
from datetime import datetime
from calendar_helper import add_work_minutes

class Task:
    """Representa una única tarea a realizar."""

    def __init__(self, task_id, name, duration_minutes, department, worker_type, dependencies=None):
        self.id = task_id
        self.name = name
        self.duration = duration_minutes
        self.department = department
        self.worker_type = worker_type
        self.dependencies = dependencies or []
        self.start_time = None
        self.end_time = None
        self.assigned_worker_id = None
        self.start_reason = ""

    def __repr__(self):
        return f"Task({self.id}, {self.name})"


class Worker:
    """Representa un trabajador individual."""

    def __init__(self, worker_id, worker_type, department):
        self.id = worker_id
        self.type = worker_type
        self.department = department

    def __repr__(self):
        return f"Worker({self.id})"


class WorkerPool:
    """Gestiona un conjunto de trabajadores de un tipo y departamento específicos."""

    def __init__(self, department, worker_type, workers):
        self.department = department
        self.type = worker_type
        self.available_workers = deque(workers)
        self.busy_workers = {}  # key: worker_id, value: (Worker, available_from_time)

    def get_earliest_available_worker(self):
        """Encuentra el trabajador (libre o el que se desocupa antes) y cuándo estará disponible."""
        if self.available_workers:
            worker = self.available_workers[0]
            return datetime.min, worker

        if not self.busy_workers:
            return None, None

        earliest_time = min(t for _, t in self.busy_workers.values())
        for worker_id, (worker, available_time) in self.busy_workers.items():
            if available_time == earliest_time:
                return earliest_time, worker
        return None, None

    def assign_worker(self, start_time, duration, workday_minutes):
        """Asigna un trabajador a una tarea y calcula cuándo terminará."""
        worker_to_assign = None

        if self.available_workers:
            worker_to_assign = self.available_workers.popleft()
        elif self.busy_workers:
            earliest_time = min(t for _, t in self.busy_workers.values())
            for worker_id, (worker, available_time) in list(self.busy_workers.items()):
                if available_time == earliest_time:
                    worker_to_assign = worker
                    del self.busy_workers[worker_id]
                    break

        if not worker_to_assign:
            return None, None, None

        task_start_time = max(start_time, self.get_worker_availability_time(worker_to_assign.id))
        task_end_time = add_work_minutes(task_start_time, duration, workday_minutes)
        self.busy_workers[worker_to_assign.id] = (worker_to_assign, task_end_time)
        return worker_to_assign, task_start_time, task_end_time

    def get_worker_availability_time(self, worker_id):
        if worker_id in self.busy_workers:
            return self.busy_workers[worker_id][1]
        return datetime.min


class ResourceManager:
    """Gestiona todos los pools de trabajadores por departamento."""

    def __init__(self, department_plans):
        self.pools = {}
        for dept, plan in department_plans.items():
            for worker_type, count in plan['workers'].items():
                if count > 0:
                    workers = [Worker(f"{dept[:3].upper()}-T{worker_type}-{i + 1}", worker_type, dept) for i in
                               range(count)]
                    self.pools[(dept, worker_type)] = WorkerPool(dept, worker_type, workers)

    def get_pool(self, department, worker_type):
        return self.pools.get((department, worker_type))

    def transfer_workers(self, from_dept, to_dept, worker_type, count):
        """Transfiere una cantidad de trabajadores de un departamento a otro."""
        from_pool = self.get_pool(from_dept, worker_type)
        to_pool = self.get_pool(to_dept, worker_type)
        if not from_pool or not to_pool:
            return 0

        available_to_transfer = len(from_pool.available_workers)
        count_to_transfer = min(count, available_to_transfer)

        transferred_count = 0
        for _ in range(count_to_transfer):
            if from_pool.available_workers:
                worker = from_pool.available_workers.popleft()
                worker.department = to_dept
                to_pool.available_workers.append(worker)
                transferred_count += 1

        logging.info(f"Se transfirieron {transferred_count} trabajadores T{worker_type} de {from_dept} a {to_dept}")
        return transferred_count


class Scheduler:
    """Orquesta la simulación de la planificación."""

    def __init__(self, tasks, resource_manager, global_start_date, workday_minutes):
        self.tasks = {t.id: t for t in tasks}
        self.resource_manager = resource_manager
        self.workday_minutes = workday_minutes
        # Guardamos la fecha de inicio global como el tiempo actual de la simulación
        self.current_time = datetime.combine(global_start_date, datetime.min.time())
        self.results_log = []
        logging.info("Scheduler inicializado.")

    def run_simulation(self):
        """Ejecuta la simulación encontrando y planificando la próxima tarea disponible."""
        while any(t.start_time is None for t in self.tasks.values()):
            next_task_to_schedule = None
            earliest_start_time = None

            for task in self.tasks.values():
                if task.start_time is not None:
                    continue

                dependencies_met = True
                completed_deps_time = datetime.min
                for dep_id in task.dependencies:
                    dep_task = self.tasks.get(dep_id)
                    if not (dep_task and dep_task.end_time):
                        dependencies_met = False
                        break
                    completed_deps_time = max(completed_deps_time, dep_task.end_time)

                if not dependencies_met:
                    continue

                pool = self.resource_manager.get_pool(task.department, task.worker_type)
                if not pool:
                    continue

                earliest_worker_info = pool.get_earliest_available_worker()
                if earliest_worker_info[0] is None:
                    continue

                worker_available_time, _ = earliest_worker_info
                # La tarea debe empezar después de las dependencias, cuando el trabajador esté libre,
                # Y no antes de la fecha de inicio global que hemos establecido.
                potential_start_time = max(completed_deps_time, worker_available_time, self.current_time)

                if next_task_to_schedule is None or potential_start_time < earliest_start_time:
                    earliest_start_time = potential_start_time
                    next_task_to_schedule = task

            if next_task_to_schedule:
                task = next_task_to_schedule
                pool = self.resource_manager.get_pool(task.department, task.worker_type)
                worker, actual_task_start_time, end_time = pool.assign_worker(earliest_start_time, task.duration,
                                                                              # Usar earliest_start_time calculado
                                                                              self.workday_minutes)

                if worker:
                    task.start_time, task.end_time, task.assigned_worker_id = actual_task_start_time, end_time, worker.id

                    # --- LÓGICA MEJORADA PARA start_reason ---
                    reason_parts = []
                    # 1. Razón de disponibilidad del trabajador
                    if actual_task_start_time > earliest_start_time:  # Esto significa que el trabajador no estaba disponible antes de earliest_start_time
                        reason_parts.append(f"Esperó a que el {worker.id} estuviera libre (fin de su tarea anterior).")
                    else:
                        reason_parts.append(f"Trabajador {worker.id} disponible.")

                    # 2. Razón de finalización de dependencias
                    dependencies_end_times = [self.tasks[dep_id].end_time for dep_id in task.dependencies if
                                              self.tasks.get(dep_id) and self.tasks[dep_id].end_time]
                    if dependencies_end_times:
                        max_dep_end_time = max(dependencies_end_times)
                        if actual_task_start_time < max_dep_end_time:  # Esto no debería pasar con la lógica de max(completed_deps_time, worker_available_time, self.current_time)
                            # Si esto ocurre, es un error de lógica, pero lo capturamos
                            reason_parts.append(f"ATENCIÓN: Inicio antes de dependencias.")
                        elif actual_task_start_time == max_dep_end_time:
                            reason_parts.append(
                                f"Comenzó al finalizar todas las dependencias ({', '.join(task.dependencies)}).")
                        else:  # actual_task_start_time > max_dep_end_time
                            reason_parts.append(
                                f"Dependencias ({', '.join(task.dependencies)}) finalizadas previamente.")
                    else:
                        reason_parts.append("No tiene dependencias directas.")

                    # 3. Razón de la fecha de inicio global o tiempo actual del simulador
                    if actual_task_start_time == self.current_time and actual_task_start_time > max(
                            dependencies_end_times or [datetime.min]) and actual_task_start_time == (
                    pool.get_worker_availability_time(worker.id) if pool else datetime.min):
                        reason_parts.append("Pudo iniciar en la fecha de inicio más temprana posible del simulador.")
                    elif actual_task_start_time > self.current_time and actual_task_start_time == (
                    pool.get_worker_availability_time(worker.id) if pool else datetime.min):
                        reason_parts.append(f"Esperó hasta que el trabajador {worker.id} estuviera libre.")

                    task.start_reason = " ".join(reason_parts)  # Unimos todas las partes de la razón
                    # --- FIN LÓGICA MEJORADA PARA start_reason ---

                    self.log_task(task)
                else:
                    logging.error(f"Error irrecuperable: No se pudo asignar trabajador para {task.name}.")
                    break
            else:
                # Si no hay más tareas que se puedan planificar, actualizamos el tiempo para liberar trabajadores
                tasks_in_progress = [t for t in self.tasks.values() if t.start_time is not None and t.end_time is None]
                if not tasks_in_progress:
                    logging.error(
                        "No se pudo encontrar la siguiente tarea a planificar. Posible deadlock de dependencias.")
                    break

        logging.info("Simulación completada.")
        return sorted(self.results_log, key=lambda x: x['Inicio'])

    def log_task(self, task):
        from calendar_helper import count_workdays
        self.results_log.append({
            "Tarea": task.name, "Departamento": task.department, "Inicio": task.start_time,
            "Fin": task.end_time, "Tipo Trabajador": task.worker_type, "Trabajador Asignado": task.assigned_worker_id,
            "Duracion (min)": task.duration, "Dias Laborables": count_workdays(task.start_time, task.end_time),
            "Motivo Inicio": task.start_reason
        })