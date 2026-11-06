"""An explicit, idempotent DRAFT creation command using the frozen P1 store."""
from decimal import InvalidOperation
import re
from uuid import UUID

from vde.errors import StorageError, utc_now
from vde.models import OrderRecord
from vde.persistence.repositories import verify_values
from vde.persistence.uow import UnitOfWork
from vde.recovery import recover

from .delivery import P6Error


_USER_FIELDS = ("title", "listing_text", "listing_url", "budget", "deadline", "notes")
_DEADLINE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
_BUDGET = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?")


def _invalid(reason):
    raise P6Error("P6_INVALID_FORM", reason)


def _validated(request_token, *, title, listing_text, listing_url, budget, deadline, notes):
    if not isinstance(request_token, str):
        _invalid("The request token must be a canonical UUID4.")
    try:
        parsed = UUID(request_token)
    except (ValueError, AttributeError) as exc:
        raise P6Error("P6_INVALID_FORM", "The request token must be a canonical UUID4.") from exc
    if parsed.version != 4 or str(parsed) != request_token:
        _invalid("The request token must be a canonical UUID4.")
    if not isinstance(title, str) or not title.strip():
        _invalid("Enter a nonempty Order title.")
    if not isinstance(listing_text, str) or not listing_text.strip():
        _invalid("Enter nonempty listing text.")
    for name, value in (("listing_url", listing_url), ("budget", budget),
                        ("deadline", deadline), ("notes", notes)):
        if value is not None and not isinstance(value, str):
            _invalid(f"{name} must be text or absent.")
    if deadline is not None and _DEADLINE.fullmatch(deadline) is None:
        _invalid("Deadline must be exact UTC YYYY-MM-DDTHH:MM:SSZ.")
    if budget is not None and _BUDGET.fullmatch(budget) is None:
        _invalid("Budget must already be finite canonical decimal text.")
    now = utc_now()
    record = OrderRecord(request_token, title.strip(), listing_text, now, now,
                         listing_url=listing_url, budget=budget, deadline=deadline,
                         notes=notes)
    try:
        # Use the authoritative frozen decimal/timestamp rules without changing
        # the supplied lexical value, rounding, or converting a local time.
        verify_values(record)
    except (StorageError, InvalidOperation, ValueError, TypeError, OverflowError) as exc:
        raise P6Error("P6_INVALID_FORM", "Budget or deadline is not in its required canonical form.") from exc
    return record


class CreateOrderService:
    def __init__(self, env):
        self.env = env

    def _healthy(self):
        if self.env.workspace is None:
            raise StorageError("Workspace unavailable")
        if recover(self.env.database, self.env.workspace).health != "ready":
            raise StorageError("Order creation requires healthy local storage")

    def list(self) -> list[OrderRecord]:
        """Read current Orders without treating an old bootstrap banner as health."""
        self._healthy()
        with UnitOfWork(self.env.database, self.env.workspace) as uow:
            return uow.orders.list()

    def create(self, request_token, *, title, listing_text, listing_url=None,
               budget=None, deadline=None, notes=None) -> OrderRecord:
        record = _validated(request_token, title=title, listing_text=listing_text,
                            listing_url=listing_url, budget=budget, deadline=deadline,
                            notes=notes)
        self._healthy()
        with UnitOfWork(self.env.database, self.env.workspace) as uow:
            # A missing get() poisons the frozen UoW. List and insert occur in
            # this same BEGIN IMMEDIATE transaction, including concurrent replay.
            prior = next((item for item in uow.orders.list() if item.id == request_token), None)
            if prior is not None:
                if any(getattr(prior, name) != getattr(record, name) for name in _USER_FIELDS):
                    raise P6Error("P6_ORDER_TOKEN_CONFLICT", "This request token already identifies different Order fields.")
                return prior
            return uow.orders.add(record)
