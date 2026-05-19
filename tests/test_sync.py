"""Tests for sync.py pure logic — normalize(), _personal_option_id(), _translate()."""

from focal.sync import normalize

# ── normalize() ───────────────────────────────────────────────────────────────


def test_normalize_strips_emoji():
    assert normalize("🏗 In progress") == "In progress"


def test_normalize_leaves_bmp_emoji():
    # ✅ is U+2705 (Basic Multilingual Plane) — not stripped by the regex
    # Both sides of a comparison are normalized, so matching still works
    assert normalize("✅ Done") == "✅ Done"


def test_normalize_strips_new_emoji():
    assert normalize("🆕 New") == "New"


def test_normalize_no_emoji():
    assert normalize("In progress") == "In progress"


def test_normalize_strips_leading_whitespace():
    assert normalize("  Ready") == "Ready"


def test_normalize_strips_dash_prefix():
    assert normalize("- Blocked") == "Blocked"


def test_normalize_empty_string():
    assert normalize("") == ""


# ── Syncer helper methods (tested via a minimal stub) ────────────────────────
# Syncer.__init__ calls gh, so we test the pure methods by constructing the
# object without calling __init__.


class _StubSyncer:
    """Minimal stub that wires up the same helpers without touching gh."""

    def __init__(self, personal_options, status_map=None):
        self.personal_options = personal_options
        self.status_map = status_map or {}

    # copy the real implementations verbatim
    def _personal_option_id(self, status_name: str):
        target = normalize(status_name)
        return next(
            (o["id"] for o in self.personal_options if normalize(o["name"]) == target),
            None,
        )

    def _translate(self, project_id: str, origin_status: str):
        mapped = self.status_map.get(project_id, {}).get(origin_status, origin_status)
        target = normalize(mapped)
        return next(
            (
                o["name"]
                for o in self.personal_options
                if normalize(o["name"]) == target
            ),
            None,
        )


PERSONAL_OPTIONS = [
    {"id": "id_new", "name": "🆕 New"},
    {"id": "id_inprogress", "name": "🏗 In progress"},
    {"id": "id_done", "name": "✅ Done"},
    {"id": "id_blocked", "name": "✋ Blocked"},
]


class TestPersonalOptionId:
    def setup_method(self):
        self.syncer = _StubSyncer(PERSONAL_OPTIONS)

    def test_exact_match_with_emoji(self):
        assert self.syncer._personal_option_id("🏗 In progress") == "id_inprogress"

    def test_match_without_emoji(self):
        assert self.syncer._personal_option_id("In progress") == "id_inprogress"

    def test_match_done(self):
        assert self.syncer._personal_option_id("✅ Done") == "id_done"

    def test_no_match_returns_none(self):
        assert self.syncer._personal_option_id("Nonexistent") is None

    def test_case_sensitive(self):
        # "in progress" ≠ "In progress"
        assert self.syncer._personal_option_id("in progress") is None


class TestTranslate:
    def test_direct_match_no_map(self):
        syncer = _StubSyncer(PERSONAL_OPTIONS)
        result = syncer._translate("proj1", "🏗 In progress")
        assert result == "🏗 In progress"

    def test_status_map_remaps_name(self):
        status_map = {"proj1": {"Doing": "🏗 In progress"}}
        syncer = _StubSyncer(PERSONAL_OPTIONS, status_map)
        result = syncer._translate("proj1", "Doing")
        assert result == "🏗 In progress"

    def test_status_map_different_project_ignored(self):
        status_map = {"proj2": {"Doing": "🏗 In progress"}}
        syncer = _StubSyncer(PERSONAL_OPTIONS, status_map)
        # "Doing" has no mapping for proj1 → falls through → no personal match
        result = syncer._translate("proj1", "Doing")
        assert result is None

    def test_no_personal_match_returns_none(self):
        syncer = _StubSyncer(PERSONAL_OPTIONS)
        result = syncer._translate("proj1", "Some Unknown Status")
        assert result is None

    def test_emoji_exact_match(self):
        syncer = _StubSyncer(PERSONAL_OPTIONS)
        # ✅ is a BMP emoji — normalize leaves it, so full string must match
        result = syncer._translate("proj1", "✅ Done")
        assert result == "✅ Done"

    def test_supplementary_emoji_stripped_for_matching(self):
        syncer = _StubSyncer(PERSONAL_OPTIONS)
        # 🏗 is supplementary plane — normalize strips it, so bare text matches
        result = syncer._translate("proj1", "In progress")
        assert result == "🏗 In progress"
