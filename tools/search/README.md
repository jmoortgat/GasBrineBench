# Literature search for v1.2

The search that added papers to version 1.2 was run once, on 1 October 2026, with
the script and the criteria in this directory. The earlier versions (1.0.0 to
1.1.1) were assembled by reading and citation chasing, without a recorded query.

| file | content |
|---|---|
| `run_search.py` | the 30 OpenAlex queries (title and abstract), the cut to the highest-ranked records of each query by OpenAlex relevance, and the removal of works whose DOI is already in `bib/references.bib`. Set `OPENALEX_MAILTO` to an e-mail address before running it. Network access is needed, and OpenAlex results change over time, so a rerun will not reproduce the pool exactly. |
| `query_log.csv` | every query string, its number of hits, the number retrieved and the run date |
| `CRITERIA.md` | the written criteria used to classify each work on title and abstract into seven classes |
| `screening_decisions.csv` | the class given to each of the 2,323 distinct works screened, with the reason (15 words at most), the gases and properties noted, and the queries that retrieved it |

The screening was done by a language model (Claude, Anthropic, run through
Claude Code) following `CRITERIA.md`, and nobody checked it work by work. It is a
triage of titles and abstracts and not a judgement on any paper. A paper entered
the data set only after its tables had been read in full; see `CHANGELOG.md` and
the data descriptor.
