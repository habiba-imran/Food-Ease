"""Trusted dispatch metadata, separate from client-authored shopping events."""

from typing import Literal

from pydantic import StrictBool, field_validator

from foodease_contract.models import Id, Model, SessionBinding


class StartupBinding(Model):
    schema_version: Literal["2.0"]
    transport: Literal["website"]
    consent: StrictBool
    generation: Id
    request_id: Id
    binding: SessionBinding
    worker_proof: Id

    @field_validator("consent")
    @classmethod
    def consent_required(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("consent required")
        return value
