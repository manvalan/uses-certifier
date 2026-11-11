# Bugs found while adopting the certifier on BoardLab (2026-11-11)

BoardLab (Python, TypeScript/TSX, C++, Rust; 1238 sources) was the first
large existing program put under certification in migration mode. Four
defects showed up; each one is fixed with a test that failed before the
fix.

| # | PR | Symptom | Cause | Fix | Test |
|---|---|---|---|---|---|
| 1 | #2 | `certify` crashed: `TypeError: can only concatenate str (not "Name") to str` on `services/review_runner.py` | Python 3.12 `type X = ...` statements are `ast.TypeAlias` nodes whose `name` is an `ast.Name`, not a string. `_children` built the qualified name of every child before checking its type. | The qualified name is built only for functions and classes. | `test_statement_whose_name_is_a_node_is_skipped` |
| 2 | #3 | `check` failed right after `stamp`: 293 "stray inline stamp" on TypeScript | Anonymous callbacks (`test('...', () => {...})`) and Python property setters share one qualified name; the element map kept only the last one, so the other stamps had no owner. | Repeated names get an ordinal: `(anonymous)`, `(anonymous)#2`, ... (`_number_duplicate_names`). | `test_duplicate_names_get_an_ordinal`, `test_anonymous_functions_keep_their_own_stamps` |
| 3 | #3 | After fix 2, `check` still failed: 8 "missing" inline stamps | Two elements starting on the same line (`const hex = (c) => c.map((v) => ...)`) share one stamped line; the second code overwrote the first in the line-to-code map. | Each stamped line holds a list of codes; `take_stamp` consumes the expected one. | `test_elements_on_the_same_line_keep_their_stamps` |
| 4 | #4 | CI red on Python 3.10 after #2 | The regression test for 1 parsed `type X = ...`, which is a syntax error before 3.12. | The test builds a statement shaped like `ast.TypeAlias` by hand, so it runs on every supported version (no skip). | same as 1 |
| 5 | #5 | BoardLab frontend lint failed (`react/jsx-no-comment-textnodes`) in `eda-tabs.tsx` and `toast.tsx` | A stamp above a callback among JSX children (`{items.map((item) => ...)}`) is JSX text: React would render `// uses-cert: stamp ...` on the page. | `.tsx`/`.jsx` sources keep no stamps; `stamp` removes old ones and `verify` skips them. The JSON certificate still fingerprints every element, so `check` still covers them. | `test_jsx_sources_are_not_stamped`, `test_old_stamps_are_removed_from_jsx_sources` |

## Lessons

- Run the project's whole build (tests, lint, frontend) after `stamp`, not
  only `check`: comments are not neutral in every language context.
- Wait for this repository's CI on every supported Python before merging;
  #2 was merged on a local 3.13 run and broke 3.10.
