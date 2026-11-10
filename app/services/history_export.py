"""Serialize a form's submission history for download."""

import csv
import io
import json

CSV_HEADER = ['submission_id', 'num_submission', 'concurrent_thread',
              'time_used', 'success_rate', 'network_status']


def submissions_to_json(submissions) -> str:
    data = [s.model_dump() for s in submissions]
    return json.dumps(data, indent=2, default=str)


def submissions_to_csv(submissions) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_HEADER)
    for sub in submissions:
        writer.writerow([
            sub.submission_id,
            sub.num_submission,
            sub.concurrent_thread,
            sub.time_used,
            sub.success_rate,
            sub.network_status,
        ])
    return output.getvalue()
