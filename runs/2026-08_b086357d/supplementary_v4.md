# Supplementary Information

For "Perovskite Photovoltaics in August 2026: Non-radiative recombination control and buried-interface treatment"

Havid Aqoma, September 8, 2026

This Supplementary Information contains the corpus construction and selection method (Note S1), the extraction and evidence-chain method (Note S2), the full reporting audit (Note S3), the corpus statistics (Note S4), the complete certified-record table (Note S5), the limitations (Note S6), and the automated gate report for this build (Note S7).

## Note S1. Corpus construction and selection

The corpus came from an OpenAlex title-and-abstract search for perovskite AND ("solar cell" OR photovoltaic), restricted to August 2026 publication dates and to the work types article, preprint and review. That set was unioned with records from Semantic Scholar, Crossref and arXiv and de-duplicated by DOI. Exclusion terms are applied in Python after retrieval, never inside the query. Of 531 works meeting the scope gate, 362 had a usable abstract and 144 met the depth-review threshold.

The depth tier is built on abstracts by decision, not by omission: a full-text retrieval probe succeeded for about 5% of a month's papers, and the failure is publisher refusal of automated retrieval rather than indexing delay. Selection is a constrained draw over venue citation percentile and mechanism axis with per-axis minima and venue and institution share caps, seeded for reproducibility. Across 200 sensitivity draws the median Jaccard overlap of the selected set was 1.0, with 135 papers appearing in every draw.

**Table S1.** Records retrieved by source.

| Source | Records retrieved |
| --- | --- |
| OpenAlex (keyed, cursor-paginated) | 538 |
| Semantic Scholar (bulk) | 432 |
| Crossref | 200 |
| arXiv | 9 |
| **Corpus after de-duplication and topical post-filter** | **531** |
| With a usable abstract | 362 |
| Non-English (machine translated) | 2 |
| Preprints | 29 |

**Table S2.** Selection funnel.

| Stage | Works |
| --- | --- |
| Passed the scope gate | 531 |
| Usable abstract (eligibility) | 360 |
| Depth tier (selected for close reading) | 144 |
| Extraction records surviving all guards | 144 |
| Dropped: no verifiable claim survived | 0 |
| Cited in the main text | 75 |
| Audited but not cited individually | 69 |

![**Figure S1.** Corpus construction funnel.](runs/2026-08_b086357d/fig/S2_corpus_funnel.pdf){width=85%}

## Note S2. Extraction and the evidence chain

Every closely read paper was passed through a structured extraction step that returned numeric fields, each bound to a verbatim quotation from that paper's own abstract. Three deterministic guards were then applied by script, never by the extracting model. First, the quotation must appear word for word in the source abstract. Second, the numeric value must appear inside its own quotation. Third, the quotation is truncated to 25 words before that check rather than after it, so a value can never be separated from the words that prove it. Any field failing a guard is nulled and counted, and a paper whose extraction left no verifiable claim was dropped from the cited set rather than shipped with an unprovable record (0 of 144 this month).

Independent re-verification of the shipped records, run as a separate script against the source abstracts, found every quotation present verbatim, none exceeding 25 words, and no numeric value missing from its own quotation. The abstract of the main text carries an additional gate: every numeral in it must exist either in the statistics file or in an extraction record, and each named scientific highlight is bound to one explicit record by its DOI, so a highlight cannot silently attach a real number to the wrong paper.

## Note S3. The full reporting audit

This note reports how completely the August 2026 papers describe their own measurements. The audit reads abstracts, so it measures what authors chose to summarise, not what appears in an experimental section or in supporting information. Two tiers are covered: a corpus tier of 362 abstracts and a depth tier of 144 abstracts.

Because the hand-labelled validation set for the detector is not yet complete, every percentage here is a lower bound and is written as "detected in at least", with no precision or recall figure attached. In the corpus tier an efficiency value was detected in at least 55.5% of abstracts, a stabilised or maximum-power-point-tracked efficiency in at least 12.7%, independent certification in at least 9.7%, an active or aperture area in at least 12.4%, and a complete open-circuit voltage, short-circuit current density and fill factor triplet in at least 4.1%. An ISOS stability-protocol label was detected in at least 1.9% and an explicit hysteresis statement in at least 3.6%. Table S3 gives both tiers side by side.

**Table S3.** Reporting-completeness detection rates. All values are lower bounds obtained by pattern detection on abstracts, not by human reading.

| Reporting item | Corpus (n=362) | Depth (n=144) |
| --- | --- | --- |
| Efficiency value stated | 55.5% | 58.3% |
| Stabilised or MPPT value | 12.7% | 20.1% |
| Independent certification | 9.7% | 13.2% |
| Device area stated | 12.4% | 18.8% |
| Hysteresis or scan direction | 3.6% | 3.5% |
| ISOS protocol label | 1.9% | 1.4% |
| Complete Voc / Jsc / FF triplet | 4.1% | 0.7% |

![**Figure S2.** Reporting-completeness detection rates, corpus and depth tiers.](runs/2026-08_b086357d/fig/S1_reporting_audit.pdf){width=90%}

Two properties of these rates govern how they should be read. They are measured on abstracts, so they describe what authors chose to summarise rather than what was measured in the laboratory: an abstract omitting a device area is not evidence that the area went unrecorded. They are also lower bounds, because the hand-labelled validation set that would attach a precision and recall figure to each pattern is not yet complete. No percentage becomes exact until its precision reaches 0.85 against human labels, and until then every figure in this note carries that caveat without restating it.

## Note S4. Corpus statistics

**Table S4.** Mechanism-axis distribution.

| Mechanism axis | Corpus | Depth | Share of corpus |
| --- | --- | --- | --- |
| composition | 195 | 25 | 36.7% |
| defects | 104 | 42 | 19.6% |
| interfaces | 106 | 32 | 20.0% |
| architecture | 56 | 17 | 10.5% |
| stability | 43 | 16 | 8.1% |
| scale up | 27 | 12 | 5.1% |

Axis assignment uses weighted keyword scoring over title and abstract across six fixed axes, with the title weighted twice. Mechanism centrality is the winning axis score normalised by that axis maximum. Selection into the depth tier scores venue citation percentile (0.40), mechanism centrality (0.35) and novelty (0.25), subject to a floor of 12 papers per axis, a preprint reservation, and per-venue and per-institution caps.

One caveat on the selection statistics is worth stating plainly. In this first issue the novelty term is constant, because it is defined against a cumulative history of extracted records that does not yet exist, so ranking reduces to venue percentile plus mechanism centrality. Repeating the selection under 200 perturbed weightings therefore returns a selection overlap of 1.0 with 135 papers selected in almost every draw. That number should be read as a consequence of the flat novelty term, not as evidence that the selector is robust; it becomes informative from the third issue onward.

## Note S5. Every certified efficiency reported in the month

Of 144 closely read papers, 18 reported an independently certified efficiency. The complete list follows, highest first. Each DOI is a live link.

| Certified PCE (%) | Venue | Architecture | DOI |
| --- | --- | --- | --- |
| 33.66 | Nature Communications | tandem_2T | [10.1038/s41467-026-76266-0](https://doi.org/10.1038/s41467-026-76266-0) |
| 32.56 | Angewandte Chemie International Edition | tandem_2T | [10.1002/anie.5241611](https://doi.org/10.1002/anie.5241611) |
| 30.77 | Nature Communications | tandem_2T | [10.1038/s41467-026-76713-y](https://doi.org/10.1038/s41467-026-76713-y) |
| 29.7 | Joule | tandem_2T | [10.1016/j.joule.2026.102645](https://doi.org/10.1016/j.joule.2026.102645) |
| 27.84 | Nature Communications | tandem_2T | [10.1038/s41467-026-76786-9](https://doi.org/10.1038/s41467-026-76786-9) |
| 27.4 | Science | p-i-n | [10.1126/science.aeg8415](https://doi.org/10.1126/science.aeg8415) |
| 27.2 | Nature Communications | p-i-n | [10.1038/s41467-026-76497-1](https://doi.org/10.1038/s41467-026-76497-1) |
| 26.77 | Angewandte Chemie International Edition | p-i-n | [10.1002/anie.3095986](https://doi.org/10.1002/anie.3095986) |
| 26.56 | Advanced Materials | tandem_2T | [10.1002/adma.74461](https://doi.org/10.1002/adma.74461) |
| 26.51 | Angewandte Chemie International Edition | unknown | [10.1002/anie.7848549](https://doi.org/10.1002/anie.7848549) |
| 26.45 | Science Advances | p-i-n | [10.1126/sciadv.aec3096](https://doi.org/10.1126/sciadv.aec3096) |
| 26.44 | Angewandte Chemie International Edition | n-i-p | [10.1002/anie.2425823](https://doi.org/10.1002/anie.2425823) |
| 26.03 | National Science Review | unknown | [10.1093/nsr/nwag484](https://doi.org/10.1093/nsr/nwag484) |
| 25.67 | Nature Communications | unknown | [10.1038/s41467-026-76848-y](https://doi.org/10.1038/s41467-026-76848-y) |
| 25.23 | Advanced Functional Materials | p-i-n | [10.1002/adfm.77942](https://doi.org/10.1002/adfm.77942) |
| 20.11 | Advanced Materials | p-i-n | [10.1002/adma.74438](https://doi.org/10.1002/adma.74438) |
| 17.35 | Small | module | [10.1002/smll.75068](https://doi.org/10.1002/smll.75068) |
| 16.98 | Nano Letters | unknown | [10.1021/acs.nanolett.6c03508](https://doi.org/10.1021/acs.nanolett.6c03508) |

## Note S6. Limitations

Venue-impact-prioritised selection under-samples preprints, regional journals and non-English venues, so the depth subset is biased toward well-indexed English-language publishing. Work circulating chiefly on preprint servers or in regional venues can carry mechanism results and reporting habits this review never sees. Of the corpus, 29 records are preprints and 2 were machine translated from another language; translation can blur technical wording.

Because indexing lags publication, this review describes the indexed record of August 2026 as retrieved at build time, not the month itself. The lag is uneven, and work published late in the month is systematically under-represented relative to work published early. A later rebuild of the same month would retrieve a larger corpus, which is why no publication count appears in the title.

Four limitations are specific to this build. First, the reporting audit is unvalidated pending the human label set (Note S3). Second, the depth tier is built on abstracts by decision: a full-text retrieval probe succeeded for only 5% of the month's papers, and a diagnostic across three months of differing age showed the failure is publisher refusal of automated retrieval rather than indexing delay, since a fourteen-month-old month retrieved worse than a two-month-old one. The audit therefore measures reported summaries, and the extraction records quote abstracts rather than full texts. Third, operational stability evidence is thin in an absolute sense: 5 papers reported a T80 lifetime and 2 named an ISOS protocol, which limits what any review can conclude about degradation this month. Fourth, this issue covers a single month, so nothing in it is a trend; the first month-over-month comparison becomes possible with the next issue.

## Note S7. Automated gate report for this build

| Gate | Status | Summary |
| --- | --- | --- |
| G4 | pass | em-dash 0, banned 0, self-report leaks 0 |
| G1 | pass | 75 citations resolved, 0 unresolved |
| G2c-cite-count | pass | 75 cited, target [60, 85], 39.3 words per citation |
| G2 | pass | 2949 words, 8 sections within 135% of ceiling |
| G2b-cite-order | pass | {"first_appearance_sequence": [], "monotonic": true} |
| G6 | pass | {"hits": []} |
| G3-abstract | pass | {"unverified": [], "words": 289, "placeholders_resolved": ["A_MAX", "H |
| G3b-abstract-form | pass | {"words": 289, "band": [260, 340], "citation_markers": 0} |
| G7-abbrev | pass | {"expanded_automatically": ["SAM", "SAM"], "still_bare": []} |
| G8-novelty | pass | worst section 0.049 vs 0.25, abstract 0.016 vs 0.3, 0 shared shingles |
| G9a-notation | pass | {"residual_defects": {}, "ambiguous_for_human_review": {"bare anion":  |
| G9b-cite-links | pass | {"hyperlinked_markers": 122, "unlinked_markers": [], "works_without_do |
| G9c-figure-unique | pass | {"attached": ["F1_certified_frontier.pdf", "F2_area_penalty.pdf", "F4_ |
| G9d-model-names | pass | {"bare_slugs_found": [], "declared": ["qwen3.8-flash", "gemini-3.8-fla |
| G10-title-block | pass | {"gaps_pt": {"author_to_affil": 14.42, "affil_to_date": 22.52, "date_t |
| G5 | pass | 14 pages, 9.6 content |

Gate definitions. G1 requires every citation marker in the main text to resolve to an extraction record carrying its own source quotation. G2 enforces length and structure ceilings and records a SHA-256 fingerprint of each drafted section, so a gate result is permanently bound to the text it judged. G4 enforces prose hygiene: em-dash count, a banned vocabulary list, and detection of leaked model self-commentary. G6 forbids first-person experimental claims, since this is a review of other groups' work. The main-text abstract carries the additional numeric gate described in Note S2.
