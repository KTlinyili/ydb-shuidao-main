from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from threading import Lock, Semaphore
from typing import Callable, Generic, TypeVar

from app.core.llm_clients import LLMRoute


T = TypeVar("T")


@dataclass(frozen=True)
class RoutedTask(Generic[T]):
    name: str
    route: LLMRoute
    fn: Callable[[], T]


class RouteConcurrencyController:
    def __init__(
        self,
        *,
        max_parallel_tasks: int = 3,
        max_concurrency_per_route: int = 2,
    ) -> None:
        self.max_parallel_tasks = max(1, int(max_parallel_tasks))
        self.max_concurrency_per_route = max(1, int(max_concurrency_per_route))
        self._lock = Lock()
        self._route_semaphores: dict[str, Semaphore] = {}

    def iter_run(self, tasks: list[RoutedTask[T]]):
        if not tasks:
            return

        worker_count = min(self.max_parallel_tasks, len(tasks))
        with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="agent-layer") as executor:
            futures = {
                executor.submit(self._run_guarded, task): task
                for task in tasks
            }
            for future in as_completed(futures):
                task = futures[future]
                yield task, future.result()

    def _run_guarded(self, task: RoutedTask[T]) -> T:
        semaphore = self._semaphore_for(task.route)
        with semaphore:
            return task.fn()

    def _semaphore_for(self, route: LLMRoute) -> Semaphore:
        key = f"{route.provider.strip().lower()}::{route.model.strip()}"
        with self._lock:
            semaphore = self._route_semaphores.get(key)
            if semaphore is None:
                semaphore = Semaphore(self.max_concurrency_per_route)
                self._route_semaphores[key] = semaphore
            return semaphore
