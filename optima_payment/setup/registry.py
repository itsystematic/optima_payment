"""Optima Payment setup features and which of them apply to the current site."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import frappe

from .features import (
    bank_guarantee,
    banking,
    hrms_integration,
    letter_of_credit,
    payment_workflow,
)

CustomFieldFactory = Callable[[], dict[str, list[dict]]]
PropertySetterFactory = Callable[[], list[dict]]
EnabledPredicate = Callable[[], bool]


def _always_enabled() -> bool:
    return True


def _is_installed(app_name: str) -> bool:
    """Check app installation only when a Frappe site context is available."""
    try:
        return app_name in frappe.get_installed_apps()
    except Exception:
        return False


@dataclass(frozen=True)
class FeatureSpec:
    """One setup feature: the customizations it declares and whether it applies to the site."""

    key: str
    get_custom_fields: CustomFieldFactory | None = None
    get_property_setters: PropertySetterFactory | None = None
    enabled: EnabledPredicate = _always_enabled


def get_feature_specs() -> list[FeatureSpec]:
    return [
        FeatureSpec(
            key="payment_workflow",
            get_custom_fields=payment_workflow.get_custom_fields,
            get_property_setters=payment_workflow.get_property_setters,
        ),
        FeatureSpec(
            key="banking",
            get_custom_fields=banking.get_custom_fields,
        ),
        FeatureSpec(
            key="bank_guarantee",
            get_custom_fields=bank_guarantee.get_custom_fields,
            get_property_setters=bank_guarantee.get_property_setters,
        ),
        FeatureSpec(
            key="letter_of_credit",
            get_custom_fields=letter_of_credit.get_custom_fields,
            get_property_setters=letter_of_credit.get_property_setters,
        ),
        FeatureSpec(
            key="hrms_integration",
            get_custom_fields=hrms_integration.get_custom_fields,
            enabled=lambda: _is_installed("hrms"),
        ),
    ]


def get_enabled_features() -> list[FeatureSpec]:
    """Return features enabled for the current site."""
    return [feature for feature in get_feature_specs() if feature.enabled()]
