"""Serialize a form's submission history and run rows for download."""

import csv
import io
import json

CSV_HEADER = ['submission_id', 'num_submission', 'concurrent_thread',
              'time_used', 'success_rate', 'network_status']

# Spreadsheet apps treat cells starting with these as formulas.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(value):
    """Neutralize text that a spreadsheet would run as a formula."""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def submissions_to_json(submissions) -> str:
    data = [s.model_dump() for s in submissions]
    return json.dumps(data, indent=2, default=str)


def submissions_to_csv(submissions) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_HEADER)
    for sub in submissions:
        writer.writerow([csv_safe(value) for value in (
            sub.submission_id,
            sub.num_submission,
            sub.concurrent_thread,
            sub.time_used,
            sub.success_rate,
            sub.network_status,
        )])
    return output.getvalue()


def _cell_text(value):
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return value


def run_rows_to_csv(snapshot, rows) -> str:
    """One line per response: outcome columns, then one column per question."""
    question_ids = list(snapshot.keys())
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["index", "status", "error", "started_at", "finished_at"]
        + [csv_safe(snapshot[qid].get("text") or qid) for qid in question_ids]
    )
    for row in rows:
        answers = row.get("answers") or {}
        values = [row.get("index"), row.get("status"), row.get("error"),
                  row.get("started_at"), row.get("finished_at")]
        for qid in question_ids:
            entry_param = snapshot[qid].get("entry_param")
            value = answers.get(qid)
            if value is None and entry_param:
                value = answers.get(entry_param)
            values.append(_cell_text(value))
        writer.writerow([csv_safe(_cell_text(value)) for value in values])
    return output.getvalue()


def run_to_json(header, rows) -> str:
    return json.dumps({"run": header, "rows": rows}, indent=2, ensure_ascii=False, default=str)
