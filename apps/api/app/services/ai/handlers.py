"""Side-effect-only import: importing this module registers every job
handler with `jobs.py`'s registry (see `register_handler` calls at the
bottom of each capability module). `jobs.py::process_due_jobs` imports this
module locally (inside the function, not at module top level) so the import
graph stays one-way: capability modules import from `jobs.py`, `jobs.py`
never imports capability modules except through this one late-bound hook —
no circular import.
"""

from . import design_generation, duplicates, embeddings, moderation, tagging  # noqa: F401
