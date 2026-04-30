// Node.js test for app/static/js/form_filling/prefill_validator.js
// Run via: node tests/js/test_prefill_validator.mjs
// Wrapped by tests/test_js_prefill_validator.py so it runs under pytest.

import assert from "node:assert/strict";
import {
    validatePrefillCompatibility,
    emailWillBeSubmitted,
    hasEntryParam,
} from "../../app/static/js/form_filling/prefill_validator.js";

let passed = 0;
function test(name, fn) {
    try {
        fn();
        passed += 1;
        process.stdout.write(`ok  ${name}\n`);
    } catch (e) {
        process.stdout.write(`FAIL ${name}\n${e.stack}\n`);
        process.exitCode = 1;
    }
}

// Helpers
const supportedForm = {
    response_config: {
        pages: [
            {
                questions: [
                    { question_id: "111", entry_id: "entry.111", type: "input_text", text: "Name?" },
                    { question_id: "222", entry_id: "entry.222", type: "multiple_choice", text: "Color?" },
                ],
            },
        ],
    },
};

const formWithRank = {
    response_config: {
        pages: [
            { questions: [{ question_id: "111", entry_id: "entry.111", type: "input_text", text: "n" }] },
            { questions: [{ question_id: "999", entry_id: "entry.999", type: "rank", text: "Order these" }] },
        ],
    },
};

const formMissingEntry = {
    response_config: {
        pages: [
            { questions: [{ question_id: "weird_id", entry_id: null, type: "input_text", text: "Mystery" }] },
        ],
    },
};

const formWithEmail = {
    response_config: {
        pages: [
            {
                questions: [
                    { question_id: "111", entry_id: "entry.111", type: "input_text", text: "Name?" },
                    { question_id: "q_email", entry_id: null, type: "input_email", text: "Default Email" },
                ],
            },
        ],
    },
};

// ---- hasEntryParam --------------------------------------------------------

test("hasEntryParam: true when entry_id present", () => {
    assert.equal(hasEntryParam({ entry_id: "entry.123" }), true);
});
test("hasEntryParam: numeric question_id falls back to true", () => {
    assert.equal(hasEntryParam({ question_id: "456" }), true);
});
test("hasEntryParam: false for q_email pseudo-question", () => {
    assert.equal(hasEntryParam({ question_id: "q_email" }), false);
});

// ---- emailWillBeSubmitted ------------------------------------------------

test("emailWillBeSubmitted: false when nothing configured", () => {
    assert.equal(emailWillBeSubmitted({}, undefined), false);
});

test("emailWillBeSubmitted: true via manual edits", () => {
    const edits = { q_email: { fill_percentage: 100, answers: ["a@b.com"] } };
    assert.equal(emailWillBeSubmitted({}, edits), true);
});

test("emailWillBeSubmitted: false when manual fill_percentage = 0", () => {
    const edits = { q_email: { fill_percentage: 0, answers: ["a@b.com"] } };
    assert.equal(emailWillBeSubmitted({}, edits), false);
});

test("emailWillBeSubmitted: false when manual answers empty", () => {
    const edits = { q_email: { fill_percentage: 100, answers: [] } };
    assert.equal(emailWillBeSubmitted({}, edits), false);
});

test("emailWillBeSubmitted: true via responses_list (file mode)", () => {
    const settings = { responses_list: [{ "111": "Alice", q_email: "a@b.com" }] };
    assert.equal(emailWillBeSubmitted(settings, undefined), true);
});

test("emailWillBeSubmitted: false when responses_list rows lack q_email", () => {
    const settings = { responses_list: [{ "111": "Alice" }, { "111": "Bob" }] };
    assert.equal(emailWillBeSubmitted(settings, undefined), false);
});

test("emailWillBeSubmitted: ignores empty-string q_email rows", () => {
    const settings = { responses_list: [{ q_email: "" }, { q_email: null }] };
    assert.equal(emailWillBeSubmitted(settings, undefined), false);
});

test("emailWillBeSubmitted: true via single responses dict (AI mode)", () => {
    const settings = { responses: { "111": "Alice", q_email: "a@b.com" } };
    assert.equal(emailWillBeSubmitted(settings, undefined), true);
});

// ---- validatePrefillCompatibility ----------------------------------------

test("validate: skip when submission_mode is dom_fill", () => {
    const r = validatePrefillCompatibility(formMissingEntry, { submission_mode: "dom_fill" });
    assert.deepEqual(r, { ok: true });
});

test("validate: ok for fully supported form", () => {
    const r = validatePrefillCompatibility(supportedForm, { submission_mode: "prefill_link" });
    assert.deepEqual(r, { ok: true });
});

test("validate: rank is supported in prefill mode", () => {
    const r = validatePrefillCompatibility(formWithRank, { submission_mode: "prefill_link" });
    assert.deepEqual(r, { ok: true });
});

test("validate: blocks question with missing entry, names the question text", () => {
    const r = validatePrefillCompatibility(formMissingEntry, { submission_mode: "prefill_link" });
    assert.equal(r.ok, false);
    assert.equal(r.blocking, true);
    assert.match(r.message, /Mystery/);
});

test("validate: q_email alone (no configured value) does NOT block", () => {
    const r = validatePrefillCompatibility(formWithEmail, { submission_mode: "prefill_link" });
    assert.deepEqual(r, { ok: true });
});

test("validate: q_email + manual edits blocks with clear message", () => {
    const r = validatePrefillCompatibility(
        formWithEmail,
        { submission_mode: "prefill_link" },
        { manualEdits: { q_email: { fill_percentage: 100, answers: ["a@b.com"] } } }
    );
    assert.equal(r.blocking, true);
    assert.match(r.message, /default email field is not supported/i);
    assert.match(r.message, /Remove the email column\/answer/);
});

test("validate: q_email + responses_list blocks", () => {
    const r = validatePrefillCompatibility(
        formWithEmail,
        {
            submission_mode: "prefill_link",
            responses_list: [{ "111": "Alice", q_email: "a@b.com" }],
        }
    );
    assert.equal(r.blocking, true);
    assert.match(r.message, /default email field is not supported/i);
});

test("validate: q_email + AI single response blocks", () => {
    const r = validatePrefillCompatibility(
        formWithEmail,
        {
            submission_mode: "prefill_link",
            responses: { "111": "Alice", q_email: "a@b.com" },
        }
    );
    assert.equal(r.blocking, true);
});

test("validate: handles missing formData gracefully", () => {
    const r = validatePrefillCompatibility(null, { submission_mode: "prefill_link" });
    assert.deepEqual(r, { ok: true });
});

// ---- exit ------------------------------------------------------------------
process.stdout.write(`\n${passed} JS tests passed\n`);
