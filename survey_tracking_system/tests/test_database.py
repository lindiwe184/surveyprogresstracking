def test_schema_contains_core_tables():
    """
    Basic smoke test to ensure key table names exist in schema.sql.
    This does not execute SQL, but guards against accidental deletions.
    """
    from pathlib import Path

    schema = Path("survey_tracking_system/database/schema.sql").read_text()
    for name in ["regions", "institutions", "survey_campaigns", "surveys", "daily_progress"]:
        assert f"TABLE {name}" in schema or f"TABLE {name} " in schema


