---
name: google-form-automation
description: Test a Google Form with Google Form Automation Tool through its MCP server. Use when the user wants to fill a Google Form they own with many test responses, preview how answers would be spread, start or stop a batch, or read a run report. Needs the desktop app open and the google-form-automation MCP server connected.
---

# Google Form Automation Tool

Google Form Automation Tool is a desktop app that sends many test responses to a Google Form
with answer percentages the user controls. Its MCP server lets you drive the app. Every tool
goes through the running app, so the app's own limits and checks apply.

## Before you start

- The desktop app must be open. If a tool answers "Google Form Automation Tool is not running",
  ask the user to open the app, then call `app_status` again. You cannot start it yourself.
- Use it only on forms the user owns or is allowed to test. Sending responses changes the form's
  real results. If ownership is unclear, ask.
- Limits: at most 500 responses per run and 10 parallel threads. One run per form at a time.
  The tool cannot create or edit a Google Form, and it cannot use an AI key; text answers
  generated with AI are set up by the user in the app.

## Standard workflow

1. `app_status`: confirm the app runs and Chrome is found. If Chrome is missing, tell the user
   to install Chrome before going on.
2. Find the form: `list_forms` for saved forms, or `extract_form` with the form URL. Then
   `get_form` to see questions, options and current settings.
3. Propose a configuration in plain words (for example "Q1: 60% Yes, 40% No; Q3: names from
   this list") and ask the user to confirm or adjust it. Then apply it with `set_answer_config`.
   Option percentages of one question should add up to 100. For common shapes use
   `apply_preset` (uniform, first_heavy; for scales also positive_skew, negative_skew, bell).
   To reuse a configuration, `list_templates` and `import_config` (preview first, then
   `apply: true`), or `export_config` to keep a copy.
4. `simulate` with the number of responses the user wants. Present the spread per question
   against the target, any skipped questions, and a few sample rows. Keep the `seed`.
5. Only after the user explicitly agrees, call `start_run` with the same count and the `seed`
   from the simulation, so the run sends exactly what was previewed. Default to 1 thread and
   a few seconds of delay unless the user asks otherwise. `prefill_link` is the default mode;
   `dom_fill` fills the form in the browser and is slower.
6. Follow progress with `run_status` (do not poll more than every few seconds). Use `stop_run`
   with the form id if the user wants to stop.
7. When it finishes, `get_report` with the `run_id` (use `list_runs` to find earlier runs of a
   form): share success and failure counts, failure
   reasons, and actual against target. If responses failed, offer `retry_failed`. Only pass
   `include_unknown: true` when the user accepts that those responses may be sent twice.

## Good practice

- Ask before every action that sends responses: `start_run` and `retry_failed`.
- Do not invent form ids or run ids; take them from tool results.
- When a tool returns an error, show the message to the user and suggest the next step rather
  than retrying the same call.
