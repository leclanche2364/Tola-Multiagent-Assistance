# Batch T24 -- Event-Driven Executive Proactivity
# correlation.py: CorrelationChain for traceable event-decision chains.

from typing import List, Tuple, Optional


class CorrelationChain:
    def __init__(self, chain_id: str):
        self.chain_id = chain_id
        self._events: list = []
        self._decisions: list = []
        self._attached: set = set()

    def attach(self, event_id: str, decision) -> None:
        if event_id in self._attached:
            return
        self._events.append(event_id)
        self._decisions.append(decision)
        self._attached.add(event_id)

    def trace(self) -> List[Tuple[str, object]]:
        return list(zip(self._events, self._decisions))

    @property
    def events(self) -> list:
        return list(self._events)

    @property
    def decisions(self) -> list:
        return list(self._decisions)
