from pathlib import Path

from mutator.functions import sites_in_file
from mutator.sites import discover_raw


def _sites(tmp_path: Path, relative: str, source: str):
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return sites_in_file(source, path, tmp_path, relative)


def _pairs(source: str) -> list[tuple[str, str]]:
    return [(site.original, site.mutant) for site in discover_raw(source, "kotlin", "A.kt")]


def test_kotlin_rules_follow_the_java_decisions(tmp_path):
    source = """package demo

class Board {
    fun place(x: Int, ok: Boolean): Int {
        if (x > 0 && ok) {
            return x + 1
        }
        return if (!ok) -x else 0
    }

    private fun hide(): Boolean {
        return true
    }
}
"""
    sites = _sites(tmp_path, "src/main/kotlin/demo/Board.kt", source)
    described = {(site.form_id, site.original, site.mutant) for site in sites}
    for pair in [("+", "-"), (">", ">="), ("&&", "||"), ("!", ""), ("-", ""), ("0", "1"), ("1", "0")]:
        assert ("defn/place", *pair) in described
    assert ("defn-/hide", "true", "false") in described
    assert {site.namespace for site in sites} == {"demo.Board"}


def test_kotlin_operator_table():
    source = """fun f(a: Int, b: Int, c: Int, p: Boolean, q: Boolean): Boolean {
    val d = a * b / c
    val e = a < b
    val g = a <= b
    val h = a == b
    val i = a != b
    val j = a === b
    return p || q
}
"""
    pairs = _pairs(source)
    for pair in [
        ("*", "/"),
        ("/", "*"),
        ("<", "<="),
        ("<=", "<"),
        ("==", "!="),
        ("!=", "=="),
        ("===", "!=="),
        ("||", "&&"),
    ]:
        assert pair in pairs


def test_kotlin_null_safety_and_ranges_are_not_sites():
    source = """fun f(s: String?, a: Int): Int {
    val n = s?.length ?: 2
    val r = a in 2..3
    val m = a % 2
    return s!!.length
}
"""
    originals = {original for original, _mutant in _pairs(source)}
    assert originals.isdisjoint({"?.", "?:", "..", "in", "%", "!!"})


def test_kotlin_strings_types_and_annotations_are_not_sites():
    source = """@Suppress("x")
fun g(a: Int = 0): Map<String, Int> {
    val s = "a + 1 > 0"
    val t = "v=${a + 1}"
    return mapOf()
}
"""
    assert _pairs(source) == [("0", "1"), ("+", "-"), ("1", "0")]


def test_kotlin_annotation_arguments_are_not_sites():
    source = """@Retry(times = 1, enabled = true)
fun g(): Int {
    return 2
}
"""
    assert _pairs(source) == []


def test_kotlin_anchor_is_the_statement_line():
    source = """fun f(a: Int): List<Int> {
    val x = 2
    return listOf(
        a + 2
    )
}
"""
    plus = [site for site in discover_raw(source, "kotlin", "A.kt") if site.original == "+"]
    assert [(site.line, site.anchor_line) for site in plus] == [(4, 3)]


def test_kotlin_coverage_reads_jacoco_source_lines(tmp_path):
    from mutator.coverage import covered_lines

    report = tmp_path / "target" / "site" / "jacoco" / "jacoco.xml"
    report.parent.mkdir(parents=True)
    report.write_text(
        """<?xml version="1.0"?>
<report name="demo">
  <package name="demo">
    <sourcefile name="Board.kt">
      <line nr="3" mi="0" ci="2" mb="0" cb="0"/>
      <line nr="4" mi="4" ci="0" mb="1" cb="0"/>
      <line nr="5" mi="0" ci="0" mb="0" cb="1"/>
    </sourcefile>
  </package>
</report>
""",
        encoding="utf-8",
    )
    source = tmp_path / "src" / "main" / "kotlin" / "demo" / "Board.kt"
    source.parent.mkdir(parents=True)
    source.write_text("package demo\nclass Board\n", encoding="utf-8")
    assert covered_lines(tmp_path, source, "kotlin") == {3, 5}


def test_kotlin_private_functions():
    from mutator.functions import is_private

    assert is_private("kotlin", "hide", "private fun hide() = 1\n", 1, 1) is True
    assert is_private("kotlin", "hide", "internal fun hide() = 1\n", 1, 1) is False


def test_kotlin_runs_maven_in_the_nearest_module(tmp_path):
    from mutator.runner import test_plan

    (tmp_path / "mod").mkdir()
    (tmp_path / "mod" / "pom.xml").write_text("<project/>", encoding="utf-8")
    source = tmp_path / "mod" / "src" / "main" / "kotlin" / "A.kt"
    source.parent.mkdir(parents=True)
    source.write_text("fun a() = 1\n", encoding="utf-8")
    assert test_plan(tmp_path, source, "kotlin", None) == (
        ["mvn", "-q", "test", "-DexcludeTags=no-mutate"],
        tmp_path / "mod",
    )


def test_help_mentions_kotlin():
    from mutator.cli import HELP

    assert "Kotlin" in HELP
