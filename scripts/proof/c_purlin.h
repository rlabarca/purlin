/*
 * Purlin proof harness for C tests.
 *
 * Single-header library. Include this file in your test runner, call
 * purlin_proof() for each test, then purlin_proof_finish() at the end.
 * Results are written to stdout as JSON which the companion script
 * (c_purlin_emit.py) merges into proof files.
 *
 * Usage:
 *   #include "purlin_proof.h"
 *
 *   int main(void) {
 *       int result = login("alice", "secret");
 *       purlin_proof("auth_login", "PROOF-1", "RULE-1", result == 200,
 *                    "test_valid_login", __FILE__, "unit");
 *
 *       purlin_proof_finish();
 *       return 0;
 *   }
 *
 * Compile and run, then pipe to the emitter:
 *   gcc -o test_runner test_runner.c && ./test_runner | python3 c_purlin_emit.py
 */

#ifndef PURLIN_PROOF_H
#define PURLIN_PROOF_H

#include <stdio.h>
#include <string.h>

#define PURLIN_MAX_PROOFS 256
#define PURLIN_MAX_STR 256

typedef struct {
    char feature[PURLIN_MAX_STR];
    char id[PURLIN_MAX_STR];
    char rule[PURLIN_MAX_STR];
    char test_name[PURLIN_MAX_STR];
    char test_file[PURLIN_MAX_STR];
    char tier[PURLIN_MAX_STR];
    int passed;
} PurlinProofEntry;

static PurlinProofEntry _purlin_proofs[PURLIN_MAX_PROOFS];
static int _purlin_proof_count = 0;

static void purlin_proof(const char *feature, const char *id, const char *rule,
                         int passed, const char *test_name, const char *test_file,
                         const char *tier) {
    if (_purlin_proof_count >= PURLIN_MAX_PROOFS) return;
    PurlinProofEntry *e = &_purlin_proofs[_purlin_proof_count++];
    strncpy(e->feature, feature, PURLIN_MAX_STR - 1);
    strncpy(e->id, id, PURLIN_MAX_STR - 1);
    strncpy(e->rule, rule, PURLIN_MAX_STR - 1);
    strncpy(e->test_name, test_name, PURLIN_MAX_STR - 1);
    strncpy(e->test_file, test_file, PURLIN_MAX_STR - 1);
    strncpy(e->tier, tier, PURLIN_MAX_STR - 1);
    e->passed = passed;
}

/* Escape a string for JSON output (handles quotes and backslashes). */
static void _purlin_json_escape(const char *s, char *out, int max_len) {
    int j = 0;
    for (int i = 0; s[i] && j < max_len - 2; i++) {
        if (s[i] == '"' || s[i] == '\\') {
            out[j++] = '\\';
        }
        out[j++] = s[i];
    }
    out[j] = '\0';
}

static void purlin_proof_finish(void) {
    char buf[PURLIN_MAX_STR * 2];
    printf("{\n  \"proofs\": [\n");
    for (int i = 0; i < _purlin_proof_count; i++) {
        PurlinProofEntry *e = &_purlin_proofs[i];
        if (i > 0) printf(",\n");
        _purlin_json_escape(e->feature, buf, sizeof(buf));
        printf("    {\"feature\": \"%s\"", buf);
        _purlin_json_escape(e->id, buf, sizeof(buf));
        printf(", \"id\": \"%s\"", buf);
        _purlin_json_escape(e->rule, buf, sizeof(buf));
        printf(", \"rule\": \"%s\"", buf);
        _purlin_json_escape(e->test_file, buf, sizeof(buf));
        printf(", \"test_file\": \"%s\"", buf);
        _purlin_json_escape(e->test_name, buf, sizeof(buf));
        printf(", \"test_name\": \"%s\"", buf);
        printf(", \"status\": \"%s\"", e->passed ? "pass" : "fail");
        _purlin_json_escape(e->tier, buf, sizeof(buf));
        printf(", \"tier\": \"%s\"}", buf);
    }
    printf("\n  ]\n}\n");
}

#endif /* PURLIN_PROOF_H */
