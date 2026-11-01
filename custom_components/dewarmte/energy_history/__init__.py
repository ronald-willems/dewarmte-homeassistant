"""Copy DeWarmte's own energy history into Home Assistant's long-term statistics.

The portal meters energy itself and keeps hourly history per heat pump. The
live `*_energy` sensors only estimate the same quantity by integrating polled
power, so the portal's numbers are written as separate *external* statistics
under the `dewarmte:` namespace. They have no entity behind them: they appear
in the Energy dashboard and in statistics cards, never in the state machine.

- `importer.py` is the algorithm: which days to walk and what to do per hour.
- `portal.py` is DeWarmte's side: a day's hours, and where the history begins.
- `store.py` is Home Assistant's side: what is stored, and how to add to it.
"""
from .importer import EnergyHistoryImporter
from .store import async_delete_history

__all__ = ["EnergyHistoryImporter", "async_delete_history"]
