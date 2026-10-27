# mutator — Kotlin (Maven) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `mutator` trova i siti di mutazione nei sorgenti `.kt`, salta le righe non coperte da JaCoCo, esegue i test Maven per ogni mutante e scrive `.metrics/mutate`, come fa per Java.

**Architecture:** Funzioni e namespace arrivano già da `crapper` (importato da `../crapper`, cioè `~/sviluppo/crapper` su `develop`, con Kotlin). Qui si aggiungono: i nodi Kotlin come genitori di operatori in `sites.py`, `kotlin` accanto a `java` in `coverage.py` (righe JaCoCo), `functions.py` (privato) e `runner.py` (Maven). Nessun modulo nuovo.

**Tech Stack:** Python ≥ 3.11, `tree-sitter-language-pack` (grammatica `kotlin`), pytest, Maven.

**Spec:** `Engage-srl/crapper` → `docs/superpowers/specs/2026-10-26-kotlin-support-design.md` (funzioni e namespace). Decisioni proprie di questo piano: sotto.

## Global Constraints

- Fork `Engage-srl/mutator`, allineabile con upstream: solo righe di aggancio nei file esistenti; nessun test esistente modificato.
- `mutator` deve stare accanto al fork di `crapper` con Kotlin (`~/sviluppo/crapper`, branch `develop`). `crapper_link.py` non cambia.
- Mutazioni Kotlin = decisioni Java (mutate4java), scritte in Kotlin: `+`↔`-`, `*`↔`/`, `>`↔`>=`, `<`↔`<=`, `==`↔`!=`, `===`↔`!==`, `&&`↔`||`, rimozione di `!` e del `-` unario, `true`↔`false`, `0`↔`1`.
- **Non** mutati in Kotlin: `?.` (togliere il safe call su un tipo nullable non compila: il mutante risulterebbe "ucciso" in modo fasullo), elvis `?:`, `%`, `..`, `in`/`!in`, `is`/`!is`, `!!`; nulla dentro stringhe (incluse interpolazioni) e commenti; nulla nei tipi (`Map<String, Int>`), nelle annotazioni, nei default dei parametri di classe.
- Comando di test Kotlin = quello Java: `mvn -q test -DexcludeTags=no-mutate` nel modulo del `pom.xml` più vicino. Per eARTS (moduli dipendenti tra loro) il README indicherà `--test-command` e `--use-existing-coverage`.
- Privato Kotlin: `private` nell'intestazione (stessa regex di Java). `internal`/`protected` = pubblici.
- Ogni funzione nuova/modificata `CRAP < 10`.
- Baseline: `.venv/bin/pytest -q` → 76 passed (con `~/sviluppo/crapper` su `develop`).

## Nodi Kotlin (verificati sulla grammatica)

Genitori di operatori binari: `additive_expression` (`+ -`), `multiplicative_expression` (`* / %`), `comparison_expression` (`< > <= >=`), `equality_expression` (`== != === !==`), `conjunction_expression` (`&&`), `disjunction_expression` (`||`). Unari: `prefix_expression` (`!x`, `-x`). Letterali: `boolean_literal`, `integer_literal`. Stringhe: `string_literal` (figli `string_content`, `interpolated_identifier`, `interpolated_expression`).

## Review Focus

1. `"a + 1 = ${a + 1}"` → nessun sito dentro la stringa? Decisione: i siti dentro `interpolated_expression` **sono** codice eseguito e vanno mutati; `string_content` no. (Task 1)
2. `val m: Map<String, Int> = mapOf()` / `@Ann(1)` / `fun f(x: Int = 0)` → nessun sito in tipi e annotazioni; il default `0` **è** codice eseguito e va mutato. (Task 1)
3. `x?.let { it + 1 } ?: 0` → mutati solo `+` e `0`/`1`. (Task 1)
4. Mutante che non compila (raro: es. `-` unario su `UInt`) → risultato "killed" come per Java; documentato, non gestito. (Task 2, README)
5. File `.kt` in un modulo senza `pom.xml` → comportamento come Java (comando nel root). (Task 2)

---

### Task 1: Siti di mutazione Kotlin

**Files:**
- Modify: `src/mutator/sites.py` (`_BINARY_PARENTS`, `_UNARY_PARENTS`, `_NUMBERS`, esclusione tipi/annotazioni per `kotlin`, docstring)
- Test: `tests/test_kotlin.py` (nuovo)

**Interfaces:**
- Consumes: `crapper.languages.kotlin` (via `sites_in_file` → funzioni e namespace).
- Produces: `discover_raw(source, "kotlin", path)` e `sites_in_file(...)` restituiscono i siti Kotlin.

- [ ] **Step 1: Write failing tests** in `tests/test_kotlin.py`, con l'helper `_sites` di `tests/test_sites.py` (copiarlo, non importarlo da un test):
  - `test_kotlin_rules_follow_the_java_decisions`: `package demo\n\nclass Board {\n    fun place(x: Int, ok: Boolean): Int {\n        if (x > 0 && ok) {\n            return x + 1\n        }\n        return if (!ok) -x else 0\n    }\n\n    private fun hide(): Boolean {\n        return true\n    }\n}\n` → in `defn/place`: `("+", "-")`, `(">", ">=")`, `("&&", "||")`, `("!", "")`, `("-", "")`, `("0", "1")`, `("1", "0")`; in `defn-/hide`: `("true", "false")`; namespace `{"demo.Board"}`.
  - `test_kotlin_operator_table`: una funzione con `a * b / c`, `a < b`, `a <= b`, `a == b`, `a != b`, `a === b`, `a || b` → coppie `("*", "/")`, `("/", "*")`, `("<", "<=")`, `("<=", "<")`, `("==", "!=")`, `("!=", "==")`, `("===", "!==")`, `("||", "&&")`.
  - `test_kotlin_null_safety_and_ranges_are_not_sites`: `fun f(s: String?, a: Int): Int {\n    val n = s?.length ?: 2\n    val r = a in 2..3\n    val m = a % 2\n    return s!!.length\n}` → nessun sito con `original` in `{"?.", "?:", "..", "in", "%", "!!"}`.
  - `test_kotlin_strings_types_and_annotations_are_not_sites`: `@Suppress("x")\nfun g(a: Int = 0): Map<String, Int> {\n    val s = "a + 1 > 0"\n    val t = "v=${a + 1}"\n    return mapOf()\n}` → siti esattamente `[("0", "1"), ("+", "-"), ("1", "0")]` in ordine di sorgente (default `0`; `+` e `1` dentro `${}`); nessuno dentro `"a + 1 > 0"`.
- [ ] **Step 2: Run** `.venv/bin/pytest -q tests/test_kotlin.py` — Expected: FAIL (nessun sito trovato per Kotlin).
- [ ] **Step 3: Implement**: aggiungi i genitori Kotlin a `_BINARY_PARENTS` e `prefix_expression` a `_UNARY_PARENTS`; `_visit_not` deve accettare `prefix_expression`; `_visit_boolean_token` già vede i token `true`/`false`; `integer_literal` è già in `_NUMBERS`. Verifica che `%` resti escluso (non è in `_BINARY`). Per `kotlin` estendi l'esclusione dei tipi (`_in_type`) ai nodi `user_type`, `nullable_type`, `type_arguments`, `annotation`, `file_annotation`, e salta `string_content` (il resto della stringa: le interpolazioni sono codice). Non toccare il comportamento delle altre lingue: le nuove esclusioni valgono solo se `language == "kotlin"`.
- [ ] **Step 4: Run** `.venv/bin/pytest -q` — Expected: tutti PASS (76 + nuovi).
- [ ] **Step 5: Commit** `Find Kotlin mutation sites`.

### Task 2: Coverage, privato, runner, documentazione

**Files:**
- Modify: `src/mutator/coverage.py` (`covered_lines`: `language in {"java", "kotlin"}`)
- Modify: `src/mutator/functions.py` (`is_private`: Kotlin come Java)
- Modify: `src/mutator/runner.py` (`_PLANS["kotlin"] = _java_plan`)
- Modify: `src/mutator/cli.py` (HELP), `README.md`, `pyproject.toml` (description)
- Test: `tests/test_kotlin.py`

- [ ] **Step 1: Write failing tests**:
  - `test_kotlin_coverage_reads_jacoco_source_lines`: come `tests/test_coverage.py::test_jacoco_marks_lines_with_covered_instructions` ma `sourcefile name="Board.kt"` e sorgente `src/main/kotlin/demo/Board.kt` → `covered_lines(tmp_path, source, "kotlin") == {3, 5}`.
  - `test_kotlin_private_functions`: `is_private("kotlin", "hide", "private fun hide() = 1\n", 0, 22) is True`; con `internal fun` → `False`.
  - `test_kotlin_runs_maven_in_the_nearest_module`: `pom.xml` in `tmp_path/mod`, sorgente `mod/src/main/kotlin/A.kt` → `test_plan(tmp_path, source, "kotlin", None) == (["mvn", "-q", "test", "-DexcludeTags=no-mutate"], tmp_path / "mod")`.
  - `test_help_mentions_kotlin`: `"Kotlin" in HELP`.
- [ ] **Step 2: Run** `.venv/bin/pytest -q tests/test_kotlin.py` — Expected: i 4 nuovi FAIL.
- [ ] **Step 3: Implement** le righe di aggancio; HELP: Kotlin nell'elenco lingue; README: sezione Kotlin con mutazioni fatte/non fatte (vedi Global Constraints), coverage JaCoCo, e flusso per Maven multi-modulo (`mutator --use-existing-coverage --test-command "mvn -q -pl <modulo> -am test" path/File.kt`); description con Kotlin.
- [ ] **Step 4: Run** `.venv/bin/pytest -q` — Expected: tutti PASS.
- [ ] **Step 5: Commit** `Cover, run and document Kotlin mutants`.

### Task 3: Verifica

- [ ] **Step 1:** `cd ~/sviluppo/mutator && ~/sviluppo/crapper/crapper --threshold 10 src/mutator/sites.py src/mutator/coverage.py src/mutator/functions.py src/mutator/runner.py` — Expected: exit 0 (le funzioni toccate sotto 10). Se no, spezzare e ritestare.
- [ ] **Step 2:** in eARTS, `--scan` su un file Kotlin di `apt2artemis` (modulo con ~97% funzioni coperte): `cd ~/sviluppo/Artemis/eARTS && ~/sviluppo/mutator/mutator --scan --use-existing-coverage <file>.kt` — Expected: elenco siti Kotlin con namespace/funzioni di crapper, nessun crash.
- [ ] **Step 3:** run reale su un file piccolo (≤ 10 siti coperti) di `apt2artemis`, con `--use-existing-coverage --max-workers 2`. Expected: baseline verde, ogni mutante killed/survived/timeout, `.metrics/mutate/<ns>.edn` scritto. Se la baseline Maven fallisce per dipendenze fra moduli, riprovare con `--test-command "mvn -q -pl apt2artemis -am test"` e riportarlo. Riportare durata per mutante.
- [ ] **Step 4:** riportare in chat: siti trovati, esiti, durata, eventuali mutanti che non compilano.
