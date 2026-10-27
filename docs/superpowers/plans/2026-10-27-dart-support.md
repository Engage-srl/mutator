# mutator — Dart/Flutter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `mutator` trova i siti di mutazione nei sorgenti `.dart`, salta le righe non coperte (LCOV), esegue `flutter test` / `dart test` per ogni mutante e scrive `.metrics/mutate`.

**Architecture:** Funzioni e namespace da `crapper` Dart (`../crapper`, branch `develop`). Qui: genitori Dart degli operatori ed esclusioni in `sites.py`, privato in `functions.py`, piano di test in `runner.py` (comando come in crapper), coverage LCOV già generica.

**Tech Stack:** Python ≥ 3.11, `tree-sitter-language-pack` (grammatica `dart`), pytest, Flutter/Dart SDK.

**Spec:** `Engage-srl/crapper` → `docs/superpowers/specs/2026-10-27-dart-support-design.md`.

## Global Constraints

- Richiede `crapper` con Dart già su `develop`.
- Solo righe di aggancio; nessun test esistente modificato; esclusioni nuove valide solo con `language == "dart"`.
- Mutazioni e non-mutazioni esattamente come nello spec.
- Test: `flutter test` se il `pubspec.yaml` più vicino dipende da Flutter, altrimenti `dart test`; directory = package.
- Privato Dart: nome che inizia con `_`.
- Ogni funzione nuova/modificata `CRAP < 10`. Baseline: `.venv/bin/pytest -q` → 88 passed.

## Nodi Dart (verificati)

Token operatore e loro genitore: `+`/`-` binari sono foglie `additive_operator` (genitore `additive_expression`); `*` `/` `%` `~/` dentro `multiplicative_operator`; `<` `<=` `>` `>=` dentro `relational_operator`; `==` `!=` foglie `equality_operator`; `&&` dentro `logical_and_operator`; `||` dentro `logical_or_operator`; `!` negazione dentro `negation_operator` (in `prefix_operator`); `-` unario foglia `minus_operator` (in `prefix_operator`); `!` di null assertion figlio diretto di `selector`. Letterali: `decimal_integer_literal`, `true`/`false`.

## Review Focus

1. `x!` (null assertion) e `!x`: solo il secondo è un sito. (Task 1)
2. `a ~/ b`, `a % b`, `a ?? b`, `a?.b`, `x is T`, `x as T` → nessun sito. (Task 1)
3. Riga senza `DA` in LCOV (es. `return 1;`) dentro un `if` coperto → coperta tramite ancora. (Task 2)
4. `case 1:` / pattern costanti → `1`→`0` mutato (codice eseguito). (Task 1)
5. Package Flutter senza `flutter` nel PATH → errore di baseline chiaro, nessun mutante eseguito. (Task 2)

---

### Task 1: Siti di mutazione Dart

**Files:** Modify `src/mutator/sites.py`; Test `tests/test_dart.py`.

- [ ] **Step 1: Write failing tests:**
  - `test_dart_rules_follow_the_java_decisions` (classe con `if (x > 0 && ok) return x + 1; return !ok ? -x : 0;` più metodo privato `_hide` → `defn-/_hide`; namespace `demo.src.board.Board`).
  - `test_dart_operator_table` (`*`, `/`, `<`, `<=`, `==`, `!=`, `||` → coppie Java).
  - `test_dart_null_safety_and_integer_division_are_not_sites` (Review Focus 1–2).
  - `test_dart_strings_types_and_annotations_are_not_sites` (`@Deprecated('x')`, `Map<String, int>`, `'a + 1'` no; `'${a + 1}'` sì; default `{int a = 0}` sì).
  - `test_dart_switch_case_constants_are_sites` (Review Focus 4).
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement**: parent dei token Dart (`additive_expression`, `multiplicative_operator`, `relational_operator`, `equality_operator`, `logical_and_operator`, `logical_or_operator`) in `_BINARY_PARENTS`; `negation_operator` e `prefix_operator` in `_UNARY_PARENTS`; esclusione per `dart`: antenati `type_arguments`, `type_identifier`, `annotation`, `type_test`, `type_cast`, e `string_literal` tranne dentro `template_substitution`.
- [ ] **Step 4: Run** `.venv/bin/pytest -q` — Expected: PASS.
- [ ] **Step 5: Commit** `Find Dart mutation sites`.

### Task 2: Privato, runner, coverage, documentazione

**Files:** Modify `src/mutator/functions.py`, `src/mutator/runner.py`, `src/mutator/cli.py`, `README.md`, `pyproject.toml`; Test `tests/test_dart.py`.

- [ ] **Step 1: Write failing tests:** `test_dart_private_functions`; `test_dart_runs_flutter_or_dart_test_in_the_package` (due `pubspec.yaml`); `test_dart_coverage_reads_lcov_lines` (LCOV con `SF:` relativo in `<package>/coverage/lcov.info` e assoluto in `target/coverage/dart/...`); `test_dart_line_without_da_uses_the_anchor` (Review Focus 3); `test_help_mentions_dart`.
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement** le righe di aggancio; README: sezione Dart (mutazioni fatte/non fatte, comandi, nota su Flutter e tempi).
- [ ] **Step 4: Run** `.venv/bin/pytest -q` — Expected: PASS.
- [ ] **Step 5: Commit** `Cover, run and document Dart mutants`.

### Task 3: Verifica

- [ ] **Step 1:** `crapper --threshold 10` sui file toccati — Expected: exit 0.
- [ ] **Step 2:** `--scan` su un file di `gap_fleet/packages/gap_core/lib` — Expected: siti con funzioni e namespace di crapper.
- [ ] **Step 3:** run reale su un file piccolo di un package eseguibile qui (`dart test`), oppure, se tutti richiedono Flutter, riportare il blocco (puro x86) e il comando da usare.
- [ ] **Step 4:** `CLOSE=1` sull'ultimo commit; riportare esiti e durata.
