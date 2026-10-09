# AI conversation and code review log

This file is a concise chronological record of the project requests and work
completed in the assistant sessions. It summarizes the conversations rather
than reproducing them verbatim. Line references below refer to the reviewed
workspace snapshot and can change as files are edited. Blank lines and
comment/docstring-only lines do not execute; within each listed code range,
the description explains the purpose of the nonblank lines.

## Conversation history

1. **Cleaning the LGA census CSVs (2011, 2016, 2021).** The user reported
   NaN values and irrelevant rows in the loaded LGA output. The loader was
   adjusted to select the actual ABS columns, recognize valid LGA records,
   exclude title/total rows, retain valid unincorporated areas, normalize
   counts and percentages, and return a consistent schema. Regression tests
   were added.
2. **Explaining the LGA changes.** The user asked for a line-by-line account of
   the edits and how they affected the output.
3. **Adding regional-area loading.** A loader for CSVs marked `_ireg` was
   added, following the LGA loader's conventions and covering the three
   Census years.
4. **Adding IARE and GCCSA loading.** Loaders for `_iare` and `_gccsa` tables
   were added with year-specific column mappings, count/proportion handling,
   and tests.
5. **Explaining the additional loaders.** The user requested a line-by-line
   explanation of the IARE and GCCSA processing.
6. **Centralizing data processing.** `data_loader.py` was created to normalize
   and combine the five area datasets, cache the result, and provide JSON
   endpoints for the frontend.
7. **Building the interactive population map.** The requested application
   shows a national state/territory map, population summaries and Census
   comparison, hover details, and state-to-LGA exploration. Official 2021 ABS
   boundaries were prepared for the map. The available table represents the
   combined "Aboriginal and/or Torres Strait Islander" category, so separate
   Aboriginal-only, Torres Strait Islander-only, and both counts are not
   claimed.
8. **Visual and interaction improvements.** The headline, change indicator,
   chart, labels, and hover/focus chart details were improved. The map
   launcher was changed to close its listening server on Ctrl+C.
9. **Comparing LGA counts within a state.** The LGA map gained a within-state
   count gradient and a count-based legend that updates with the selected
   year. Census data records without a matching boundary are listed separately.
10. **Investigating state selection and server persistence.** The failed state
    request was traced to the service being unavailable rather than an
    oversized response. The tested state response was small; Ctrl+C must be
    sent in the terminal running the launcher.
11. **Suggesting pytest edge cases.** The user requested unusual-input cases,
    including malformed filters, zero/invalid years, pagination boundaries,
    missing values, and cache/data edge cases.
12. **Fixing the year-zero handling.** The API was changed to distinguish an
    omitted `year` from a supplied `year=0`; zero is rejected as unsupported
    rather than treated as if the filter were absent. Tests cover both cases.
13. **PythonAnywhere deployment.** `Interface (Frontend)/web_app.py` was
    added as a WSGI entry point, with deployment steps added to the README.
14. **Whole-project review and this log.** The user requested a code review
    for mistakes and security risks, an explanation of code locations, and
    an `AI-LOG.md` conversation log. The review found the issues listed below.
    No application behavior was changed as part of this review.
