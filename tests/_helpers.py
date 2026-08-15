"""Shared test helpers for the fawaterak test suite."""

from __future__ import annotations


class FakeTokenManager:
	"""Token manager stub that avoids real OAuth calls in unit tests."""

	def __init__(self, token: str = "test-token") -> None:
		self._token = token
		self.refresh_count = 0

	@property
	def access_token(self) -> str:
		return self._token

	def refresh(self) -> None:
		self.refresh_count += 1
		self._token = f"refreshed-{self._token}"
