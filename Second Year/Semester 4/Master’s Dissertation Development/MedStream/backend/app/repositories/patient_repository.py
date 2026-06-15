from __future__ import annotations

from typing import Any

from app.repositories.address_repository import AddressRepository
from app.repositories.patient_assignment_repository import PatientAssignmentRepository
from app.repositories.patient_clinical_record_repository import PatientClinicalRecordRepository
from app.repositories.patient_core_repository import PatientCoreRepository
from app.service.patient.alert_state_service import PatientAlertStateService
from app.service.patient.discharge_service import PatientDischargeService
from app.service.patient.post_discharge_summary_service import PatientPostDischargeSummaryService
from app.service.patient.treatment_evaluator import PatientTreatmentEvaluator


class PatientRepository:
    MEDICATION_NAME_MAX_LENGTH = PatientAlertStateService.MEDICATION_NAME_MAX_LENGTH
    MEDICATION_DOSAGE_MAX_LENGTH = PatientAlertStateService.MEDICATION_DOSAGE_MAX_LENGTH
    MEDICATION_FREQUENCY_MAX_LENGTH = PatientAlertStateService.MEDICATION_FREQUENCY_MAX_LENGTH
    MIN_TREATMENT_ACTIONS_BEFORE_RECOVERY_DISCHARGE = (
        PatientAlertStateService.MIN_TREATMENT_ACTIONS_BEFORE_RECOVERY_DISCHARGE
    )
    HEART_RATE_STABLE_MAX = PatientAlertStateService.HEART_RATE_STABLE_MAX
    OXYGEN_STABLE_MIN = PatientAlertStateService.OXYGEN_STABLE_MIN
    TEMPERATURE_STABLE_MAX = PatientAlertStateService.TEMPERATURE_STABLE_MAX
    ABNORMAL_ALERT_TYPES = PatientAlertStateService.ABNORMAL_ALERT_TYPES
    RECOVERY_ALERT_TYPES = PatientAlertStateService.RECOVERY_ALERT_TYPES
    VITAL_PRIORITY = PatientAlertStateService.VITAL_PRIORITY
    VITAL_LABELS = PatientAlertStateService.VITAL_LABELS

    def __init__(self, address_repository: AddressRepository | None = None):
        self.treatment_evaluator = PatientTreatmentEvaluator()
        self.discharge_service = PatientDischargeService()
        self.summary_service = PatientPostDischargeSummaryService()
        self.assignment_repository = PatientAssignmentRepository(
            treatment_evaluator=self.treatment_evaluator,
            discharge_service=self.discharge_service,
        )
        self.core_repository = PatientCoreRepository(
            address_repository=address_repository,
            assignment_repository=self.assignment_repository,
        )
        self.clinical_record_repository = PatientClinicalRecordRepository(
            treatment_evaluator=self.treatment_evaluator,
            discharge_service=self.discharge_service,
        )
        self._delegates = (
            self.core_repository,
            self.assignment_repository,
            self.clinical_record_repository,
            self.treatment_evaluator,
            self.discharge_service,
            self.summary_service,
        )

    def __getattr__(self, name: str) -> Any:
        for delegate in self._delegates:
            if hasattr(delegate, name):
                return getattr(delegate, name)
        raise AttributeError(f"{type(self).__name__!s} has no attribute {name!r}")


def _delegate_classmethod(target: type, name: str):
    @classmethod
    def wrapper(cls, *args, **kwargs):
        return getattr(target, name)(*args, **kwargs)

    wrapper.__name__ = name
    return wrapper


for _target, _method_names in (
    (
        PatientAlertStateService,
        (
            "_classify_alert_state",
            "_classify_vital_alert_state",
            "_extract_status_vitals",
            "_extract_alert_structured_fields",
            "_normalize_datetime_for_comparison",
            "_normalize_datetime_candidates",
            "_get_latest_vital_specific_alert_state",
            "_build_latest_alert_debug_payload",
            "_current_alert_level",
            "_format_vital_label",
            "_pick_most_problematic_vital",
            "_safe_summary_text",
            "_build_final_vital_state_text",
            "_get_unresolved_abnormal_vitals",
            "_get_recovered_vitals_after_treatment",
            "_find_complete_recovery_snapshot",
            "_has_unresolved_abnormal_alerts_after_in_sequence",
            "get_latest_vital_state",
            "get_latest_vital_alert_state",
            "has_unresolved_abnormal_alerts_after",
        ),
    ),
    (
        PatientTreatmentEvaluator,
        (
            "_stable_vital_count",
            "_build_treatment_actions",
            "_build_treatment_evaluation_window",
            "_get_latest_vital_state_for_window",
            "_get_latest_vital_before_timestamp",
            "_get_vital_trend_improvements",
            "_is_treatment_escalation_due_to_worsening",
            "_derive_treatment_outcome_from_window",
            "_derive_treatment_outcome_from_alert_recovery",
            "_evaluate_treatment_action",
            "_latest_treatment_action_outcome",
            "_build_treatment_reasoning_payload",
            "build_treatment_actions",
            "evaluate_treatment_action",
            "get_latest_treatment_action_outcome",
        ),
    ),
    (
        PatientDischargeService,
        ("can_discharge_patient_as_recovered",),
    ),
    (
        PatientPostDischargeSummaryService,
        (
            "_build_episode_window",
            "_is_within_episode",
            "_build_post_discharge_clinical_summary",
            "_build_post_discharge_readmission_notes",
            "_serialize_post_discharge_summary_row",
            "_build_post_discharge_summary_payload",
            "generate_post_discharge_summaries",
        ),
    ),
):
    for _method_name in _method_names:
        setattr(PatientRepository, _method_name, _delegate_classmethod(_target, _method_name))

del _target, _method_names, _method_name
