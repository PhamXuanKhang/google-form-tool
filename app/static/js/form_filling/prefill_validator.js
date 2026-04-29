/**
 * Prefill-link compatibility validator (TIP-005 / TIP-005.1).
 *
 * Pure module — no DOM, no globals. Imported by main.js for the live UI and
 * by tests/js/test_prefill_validator.mjs for unit verification.
 */

const UNSUPPORTED_BETA_TYPES = new Set(["rank", "file_upload", "rating"]);

export function hasEntryParam(question) {
    if (question?.entry_id) return true;
    if (question?.question_id && /^\d+$/.test(question.question_id)) return true;
    return false;
}

function _identityT(_key, fallback) {
    return fallback;
}

/**
 * Decide whether q_email will actually be submitted.
 * Returns true if any of the three answer sources carries a non-empty value
 * for q_email (manual edits, file-driven responses_list, or single AI response).
 */
export function emailWillBeSubmitted(settings, manualEdits) {
    // 1. Manual mode: collected edits keyed by question_id.
    const edit = manualEdits?.q_email;
    if (edit) {
        const fill = edit.fill_percentage;
        const answers = Array.isArray(edit.answers) ? edit.answers : [];
        if ((fill ?? 0) > 0 && answers.length > 0) return true;
    }

    // 2. File-driven responses_list: any row carrying a q_email value.
    if (Array.isArray(settings?.responses_list)) {
        for (const row of settings.responses_list) {
            if (!row) continue;
            if (Object.prototype.hasOwnProperty.call(row, "q_email")) {
                const v = row.q_email;
                if (v !== "" && v != null && !(Array.isArray(v) && v.length === 0)) {
                    return true;
                }
            }
        }
    }

    // 3. AI / single response mode.
    const r = settings?.responses;
    if (r && Object.prototype.hasOwnProperty.call(r, "q_email")) {
        const v = r.q_email;
        if (v !== "" && v != null && !(Array.isArray(v) && v.length === 0)) {
            return true;
        }
    }

    return false;
}

/**
 * Validate that a form is compatible with prefill-link mode.
 *
 * @param {object} formData     - extracted form preview (response_config.pages[].questions[])
 * @param {object} settings     - the request body about to be POSTed to /start_submission
 * @param {object} [opts]
 * @param {object} [opts.manualEdits] - result of window.collectManualEdits()
 * @param {function} [opts.t]         - i18n translator (key, fallback) -> string
 *
 * Returns:
 *   { ok: true }                                -> proceed
 *   { ok: false, blocking: true, message }      -> show popup, abort submit
 */
export function validatePrefillCompatibility(formData, settings, opts = {}) {
    const t = opts.t || _identityT;
    const manualEdits = opts.manualEdits;

    if (settings?.submission_mode !== "prefill_link") {
        return { ok: true };
    }
    if (!formData || !formData.response_config?.pages) {
        return { ok: true };
    }

    for (const page of formData.response_config.pages) {
        for (const question of (page.questions || [])) {
            if (UNSUPPORTED_BETA_TYPES.has(question.type)) {
                return {
                    ok: false,
                    blocking: true,
                    message: `${t("unsupportedFeaturePopup", "This feature is being developed and will be available in the next update.")} (${question.type})`,
                };
            }

            if (hasEntryParam(question)) continue;

            // q_email pseudo-question: only block when the user has actually
            // configured/queued an email value to be submitted. Otherwise the
            // field is simply ignored, exactly like Google Forms would when
            // no value is supplied.
            if (question.question_id === "q_email") {
                if (emailWillBeSubmitted(settings, manualEdits)) {
                    return {
                        ok: false,
                        blocking: true,
                        message: t(
                            "prefillEmailNotSupportedBlock",
                            "The default email field is not supported in prefill-link mode yet. Remove the email column/answer or use a form question with real entry metadata."
                        ),
                    };
                }
                continue;
            }

            return {
                ok: false,
                blocking: true,
                message: t(
                    "prefillMissingEntry",
                    "Question '{q}' is missing entry metadata; please re-extract the form. A future fallback may ask you for a prefill link."
                ).replace("{q}", question.text || question.question_id),
            };
        }
    }

    return { ok: true };
}
