"""
backend/app/services/cost_service.py
Calcoli costi workshop con Decimal. Mai floating point.
Interfaccia RouteCostProvider per futura integrazione API route.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Optional

from sqlalchemy.orm import Session

from backend.app.models.cost import WorkshopCost

CENT = Decimal("0.01")
ZERO = Decimal("0")


def _d(value: str | int | float | None) -> Decimal:
    """Converte qualsiasi valore numerico in Decimal sicuro."""
    if value is None:
        return ZERO
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return ZERO


class RouteCostProvider:
    """
    Interfaccia astratta per provider di costi itinerario.
    Attualmente: solo inserimento manuale (ViaMichelin link + valori a mano).
    In futuro: implementare con un provider API autorizzato.
    """
    def get_route_costs(
        self,
        departure: str,
        destination: str,
        vehicle_type: str,
    ) -> dict:
        raise NotImplementedError(
            "L'inserimento automatico dei costi itinerario richiede un provider API autorizzato. "
            "Usa l'inserimento manuale tramite ViaMichelin."
        )


class ManualRouteCostProvider(RouteCostProvider):
    """Provider manuale: non fa chiamate esterne, restituisce sempre None."""
    def get_route_costs(self, departure: str, destination: str, vehicle_type: str) -> dict:
        return {"fuel": None, "tolls": None, "source": "manual"}


def calculate_costs(cost: WorkshopCost, participant_count: int, revenue_cents: int) -> dict:
    """
    Ricalcola tutti i totali con Decimal.
    Formule:
      totale_pernotto = notti × costo_notte × quantità_camere
      totale_viaggio  = carburante + pedaggi + parcheggi + traghetti + altre_viaggio
      totale_costi    = totale_pernotto + totale_viaggio + altre_org
      costo_pp        = totale_costi / n_partecipanti  (N > 0)
      margine         = ricavi - totale_costi
    """
    total_acc = (
        _d(cost.nights) * _d(cost.cost_per_night_decimal) * _d(cost.room_count)
    ).quantize(CENT, rounding=ROUND_HALF_UP)

    total_travel = sum([
        _d(cost.fuel_decimal),
        _d(cost.tolls_decimal),
        _d(cost.parking_decimal),
        _d(cost.ferries_decimal),
        _d(cost.other_travel_decimal),
    ], ZERO).quantize(CENT, rounding=ROUND_HALF_UP)

    total_costs = (total_acc + total_travel + _d(cost.other_org_decimal)).quantize(
        CENT, rounding=ROUND_HALF_UP
    )

    n = participant_count if participant_count > 0 else 1  # evita divisione per zero
    cpp = (total_costs / Decimal(str(n))).quantize(CENT, rounding=ROUND_HALF_UP)

    revenue = (_d(revenue_cents) / Decimal("100")).quantize(CENT, rounding=ROUND_HALF_UP)
    margin = (revenue - total_costs).quantize(CENT, rounding=ROUND_HALF_UP)

    return {
        "totalAccommodation": str(total_acc),
        "totalTravel": str(total_travel),
        "totalCosts": str(total_costs),
        "costPerParticipant": str(cpp),
        "estimatedMargin": str(margin),
        "revenue": str(revenue),
    }


def update_cost_totals(db: Session, cost: WorkshopCost, participant_count: int, revenue_cents: int) -> WorkshopCost:
    """Ricalcola e persiste i totali nel record WorkshopCost."""
    result = calculate_costs(cost, participant_count, revenue_cents)
    cost.total_accommodation_decimal = result["totalAccommodation"]
    cost.total_travel_decimal = result["totalTravel"]
    cost.total_costs_decimal = result["totalCosts"]
    cost.cost_per_participant_decimal = result["costPerParticipant"]
    cost.estimated_margin_decimal = result["estimatedMargin"]
    db.commit()
    return cost
