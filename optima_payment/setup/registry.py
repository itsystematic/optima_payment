"""Ordered setup registry for Optima Payment feature-owned customizations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import click
import frappe

from . import metadata
from .features import (
    bank_guarantee,
    banking,
    hrms_integration,
    letter_of_credit,
    payment_workflow,
)
from .runner import describe_exception, run_setup_steps

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
    """Describe one setup feature and its lifecycle behavior."""

    key: str
    label: str
    get_custom_fields: CustomFieldFactory | None = None
    get_property_setters: PropertySetterFactory | None = None
    obsolete_property_setters: list[dict] = field(default_factory=list)
    enabled: EnabledPredicate = _always_enabled
    is_optional: bool = False


def get_feature_specs() -> list[FeatureSpec]:
    """Return setup features in the order they must be applied."""
    return [
        FeatureSpec(
            key="payment_workflow",
            label="Payment workflow customizations",
            get_custom_fields=payment_workflow.get_custom_fields,
            get_property_setters=payment_workflow.get_property_setters,
            obsolete_property_setters=payment_workflow.OBSOLETE_PROPERTY_SETTERS,
        ),
        FeatureSpec(
            key="banking",
            label="Banking customizations",
            get_custom_fields=banking.get_custom_fields,
        ),
        FeatureSpec(
            key="bank_guarantee",
            label="Bank guarantee customizations",
            get_custom_fields=bank_guarantee.get_custom_fields,
            get_property_setters=bank_guarantee.get_property_setters,
        ),
        FeatureSpec(
            key="letter_of_credit",
            label="Letter of Credit customizations",
            get_custom_fields=letter_of_credit.get_custom_fields,
        ),
        FeatureSpec(
            key="hrms_integration",
            label="HRMS integration customizations",
            get_custom_fields=hrms_integration.get_custom_fields,
            enabled=lambda: _is_installed("hrms"),
            is_optional=True,
        ),
    ]


def get_enabled_features() -> list[FeatureSpec]:
    """Return features enabled for the current site."""
    return [feature for feature in get_feature_specs() if feature.enabled()]


def get_all_custom_fields() -> dict[str, list[dict]]:
    """Collect custom fields from all enabled features."""
    return metadata.merge_custom_fields(
        *[
            feature.get_custom_fields()
            for feature in get_enabled_features()
            if feature.get_custom_fields
        ]
    )


def get_all_property_setters() -> list[dict]:
    """Collect property setters from all enabled features."""
    property_setters: list[dict] = []
    for feature in get_enabled_features():
        if feature.get_property_setters:
            property_setters.extend(feature.get_property_setters())
    return property_setters


def ensure_customizations() -> None:
    """Apply setup customizations feature by feature."""
    click.secho("Applying Optima Payment customizations...", fg="yellow")
    for feature in get_feature_specs():
        if not feature.enabled():
            continue
        _apply_feature(feature)


def before_uninstall() -> None:
    """Remove feature-owned metadata before uninstalling the app."""
    click.secho("Removing Optima Payment customizations...", fg="blue")
    for feature in reversed(get_enabled_features()):
        _remove_feature(feature)


def _apply_feature(feature: FeatureSpec) -> None:
    custom_fields = feature.get_custom_fields() if feature.get_custom_fields else {}
    property_setters = feature.get_property_setters() if feature.get_property_setters else []

    steps = []
    if custom_fields:
        steps.append(
            (
                "Create custom fields",
                lambda custom_fields=custom_fields: _create_custom_fields(custom_fields),
            )
        )
    if property_setters:
        steps.append(
            (
                "Apply property setters",
                lambda property_setters=property_setters: metadata.add_property_setters(property_setters),
            )
        )
    if feature.obsolete_property_setters:
        steps.append(
            (
                "Remove obsolete property setters",
                lambda property_setters=feature.obsolete_property_setters: metadata.cleanup_obsolete_property_setters(
                    property_setters
                ),
            )
        )

    if not steps:
        return

    try:
        run_setup_steps(steps, section_label=feature.label)
    except Exception as error:
        if not feature.is_optional:
            raise

        message = (
            f"Skipping optional setup feature '{feature.label}': "
            f"{describe_exception(error if isinstance(error, Exception) else Exception(str(error)))}"
        )
        click.secho(message, fg="yellow")
        frappe.log_error(message=frappe.get_traceback(), title=f"Optima Payment optional feature failed: {feature.key}")


def _create_custom_fields(custom_fields: dict[str, list[dict]]) -> None:
    metadata.create_custom_fields_safely(custom_fields)
    metadata.sync_custom_field_schema(custom_fields)


def _remove_feature(feature: FeatureSpec) -> None:
    custom_fields = feature.get_custom_fields() if feature.get_custom_fields else {}
    property_setters = feature.get_property_setters() if feature.get_property_setters else []

    try:
        if property_setters:
            removed = metadata.cleanup_property_setters(property_setters)
            click.secho(
                f"{feature.label}: removed {removed} property setters",
                fg="green",
            )
        if custom_fields:
            removed = metadata.cleanup_custom_fields(custom_fields)
            click.secho(
                f"{feature.label}: removed {removed} custom fields",
                fg="green",
            )
    except Exception as error:
        raise RuntimeError(
            f"Failed removing customizations for {feature.label}: {describe_exception(error)}"
        ) from error
