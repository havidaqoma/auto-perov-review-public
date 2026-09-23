# Supplementary Information

For "Perovskite Photovoltaics in July 2026: Trap density and ion migration, self-assembled monolayer contacts"

Havid Aqoma, September 8, 2026

This Supplementary Information contains the corpus construction and selection method (Note S1), the extraction and evidence-chain method (Note S2), the full reporting audit (Note S3), the corpus statistics (Note S4), the complete certified-record table (Note S5), the limitations (Note S6), and the automated gate report for this build (Note S7).

## Note S1. Corpus construction and selection

The corpus came from an OpenAlex title-and-abstract search for perovskite AND ("solar cell" OR photovoltaic), restricted to July 2026 publication dates and to the work types article, preprint, and review. That set was then unioned with records from Semantic Scholar, Crossref and arXiv, and de-duplicated by DOI. Of 648 works published in July 2026 that met the scope gate, 453 had a usable abstract and 181 of those met the depth-review threshold.

All 181 depth-tier papers were audited, 180 are cited individually, and the remainder are indexed in the supplementary table. The depth tier is based on abstracts, because a full-text retrieval probe succeeded for only 5% of the month's papers. Screening therefore rests on what authors chose to state in the abstract, and each abstract was assessed against a common checklist so that the counts reported in the following sections can be reproduced from the supplementary table.

The audit also measures how completely the corpus reports the quantities behind its own claims. Because the hand-labelled validation set is not yet complete, every corpus-level percentage in this section is reported as a lower bound using the phrase "detected in at least", with no precision or recall figure attached. Point estimates will replace these bounds once the validation labels are final, and any rate that rises will be reported against the updated denominator rather than silently revised.

**Table S1.** Records retrieved by source.

| Source | Records retrieved |
| --- | --- |
| OpenAlex (keyed, cursor-paginated) | 657 |
| Semantic Scholar (bulk) | 549 |
| Crossref | 200 |
| arXiv | 6 |
| **Corpus after de-duplication and topical post-filter** | **648** |
| With a usable abstract | 456 |
| Non-English (machine translated) | 6 |
| Preprints | 27 |

**Table S2.** Selection funnel.

| Stage | Works |
| --- | --- |
| Passed the scope gate | 648 |
| Usable abstract (eligibility) | 453 |
| Depth tier (selected for close reading) | 181 |
| Extraction records surviving all guards | 169 |
| Dropped: no verifiable claim survived | 12 |
| Cited in the main text | 79 |
| Audited but not cited individually | 90 |

![**Figure S1.** Corpus construction funnel.](runs/2026-07_197abe83/fig/S2_corpus_funnel.pdf){width=85%}

## Note S2. Extraction and the evidence chain

Every closely read paper was passed through a structured extraction step that returned numeric fields, each bound to a verbatim quotation from that paper's own abstract. Three deterministic guards were then applied by script, never by the extracting model. First, the quotation must appear word for word in the source abstract. Second, the numeric value must appear inside its own quotation. Third, the quotation is truncated to 25 words before that check rather than after it, so a value can never be separated from the words that prove it. Any field failing a guard is nulled and counted, and a paper whose extraction left no verifiable claim was dropped from the cited set rather than shipped with an unprovable record (12 of 181 this month).

Independent re-verification of the shipped records, run as a separate script against the source abstracts, found every quotation present verbatim, none exceeding 25 words, and no numeric value missing from its own quotation. The abstract of the main text carries an additional gate: every numeral in it must exist either in the statistics file or in an extraction record, and each named scientific highlight is bound to one explicit record by its DOI, so a highlight cannot silently attach a real number to the wrong paper.

## Note S3. The full reporting audit

This section reports how completely the July 2026 papers describe their own measurements. The audit reads abstracts, so it measures what authors chose to summarise, not what appears in an experimental section or in supporting information. Two tiers are covered: a corpus tier of 456 abstracts and a depth tier of 181 abstracts. Because the hand-labelled validation set for the detector is not yet complete, every percentage in this section is a lower bound and is written as "detected in at least", with no precision or recall figure attached.

In the corpus tier, an efficiency value was detected in at least 50.4% of abstracts. A stabilised or MPPT efficiency was detected in at least 15.4%. Certification was detected in at least 8.3%. A device area was detected in at least 9.2%. Hysteresis or scan direction was detected in at least 2.6%, and a labelled ISOS stability protocol was detected in at least 1.3%. The complete Voc, Jsc and FF triplet was detected in at least 2.9%. Roughly half of the month's abstracts therefore claim an efficiency, while very few report certification or the full parameter triplet that would let a reader check that claim against another paper's. The headline number is the quantity authors summarise most often, and it is also the quantity whose meaning depends most on the details left out of the summary.

The depth tier scores higher on six of the seven measures: efficiency detected in at least 61.3%, stabilised or MPPT efficiency detected in at least 26.5%, certification detected in at least 13.3%, device area detected in at least 13.8%, hysteresis or scan direction detected in at least 3.9%, and an ISOS label detected in at least 2.8%. The exception is the complete triplet, detected in at least 2.2% in the depth tier, while in the corpus tier it was detected in at least 2.9%. The general direction is expected rather than reassuring. The depth tier was selected partly on venue citation percentile, so better-reported work from high-visibility venues is over-represented by construction. The gap between the tiers therefore describes the sampling as much as it describes reporting practice, and its practical effect is that the corpus-level lower bounds understate how completely the strongest papers of the month disclose their measurements.

The main limitation of measuring reporting this way is structural. An abstract is a summary, and its silence is not proof that a measurement was not made. Certification, active area, scan direction and ISOS labels routinely appear in the experimental section without ever reaching the abstract, and naming a stability protocol in an abstract is not a field-wide convention. The percentages above therefore bound what was summarised, not what was measured. They remain worth tracking for two reasons. The abstract is what most readers screen and what automated databases ingest, so a quantity absent from it is invisible to the pipelines that aggregate the record. And the pattern of what does reach the abstract is itself informative: a single efficiency number travels easily into a summary, while the contextual facts that make efficiency comparable, certification, area, scan direction and protocol, mostly do not. A monthly audit of that gap costs little, and it is the part of this digest that measures the field's willingness to make its own claims checkable.

**Table S3.** Reporting-completeness detection rates. All values are lower bounds obtained by pattern detection on abstracts, not by human reading.

| Reporting item | Corpus (n=456) | Depth (n=181) |
| --- | --- | --- |
| Efficiency value stated | 50.4% | 61.3% |
| Stabilised or MPPT value | 15.4% | 26.5% |
| Independent certification | 8.3% | 13.3% |
| Device area stated | 9.2% | 13.8% |
| Hysteresis or scan direction | 2.6% | 3.9% |
| ISOS protocol label | 1.3% | 2.8% |
| Complete Voc / Jsc / FF triplet | 2.9% | 2.2% |

![**Figure S2.** Reporting-completeness detection rates, corpus and depth tiers.](runs/2026-07_197abe83/fig/S1_reporting_audit.pdf){width=90%}

Two properties of these rates govern how they should be read. They are measured on abstracts, so they describe what authors chose to summarise rather than what was measured in the laboratory: an abstract omitting a device area is not evidence that the area went unrecorded. They are also lower bounds, because the hand-labelled validation set that would attach a precision and recall figure to each pattern is not yet complete. No percentage becomes exact until its precision reaches 0.85 against human labels, and until then every figure in this note carries that caveat without restating it.

## Note S4. Corpus statistics

**Table S4.** Mechanism-axis distribution.

| Mechanism axis | Corpus | Depth | Share of corpus |
| --- | --- | --- | --- |
| composition | 271 | 38 | 41.8% |
| defects | 101 | 45 | 15.6% |
| interfaces | 119 | 39 | 18.4% |
| architecture | 64 | 22 | 9.9% |
| stability | 66 | 25 | 10.2% |
| scale up | 27 | 12 | 4.2% |

Axis assignment uses weighted keyword scoring over title and abstract across six fixed axes, with the title weighted twice. Mechanism centrality is the winning axis score normalised by that axis maximum. Selection into the depth tier scores venue citation percentile (0.40), mechanism centrality (0.35) and novelty (0.25), subject to a floor of 12 papers per axis, a preprint reservation, and per-venue and per-institution caps.

One caveat on the selection statistics is worth stating plainly. In this first issue the novelty term is constant, because it is defined against a cumulative history of extracted records that does not yet exist, so ranking reduces to venue percentile plus mechanism centrality. Repeating the selection under 200 perturbed weightings therefore returns a selection overlap of 1.0 with 172 papers selected in almost every draw. That number should be read as a consequence of the flat novelty term, not as evidence that the selector is robust; it becomes informative from the third issue onward.

## Note S5. Every certified efficiency reported in the month

Of 169 closely read papers, 22 reported an independently certified efficiency. The complete list follows, highest first. Each DOI is a live link.

| Certified PCE (%) | Venue | Architecture | DOI |
| --- | --- | --- | --- |
| 33.1 | Science Advances | tandem_2T | [10.1126/sciadv.aei2945](https://doi.org/10.1126/sciadv.aei2945) |
| 32.13 | Angewandte Chemie International Edition | tandem_2T | [10.1002/anie.1676645](https://doi.org/10.1002/anie.1676645) |
| 29.57 | Advanced Materials | tandem_2T | [10.1002/adma.74078](https://doi.org/10.1002/adma.74078) |
| 28.84 | Science Advances | tandem_2T | [10.1126/sciadv.aeb8790](https://doi.org/10.1126/sciadv.aeb8790) |
| 27.49 | Science Advances | tandem_2T | [10.1126/sciadv.aef6600](https://doi.org/10.1126/sciadv.aef6600) |
| 27.31 | Advanced Materials | p-i-n | [10.1002/adma.73807](https://doi.org/10.1002/adma.73807) |
| 27.31 | Science Advances | p-i-n | [10.1126/sciadv.aeg1456](https://doi.org/10.1126/sciadv.aeg1456) |
| 27.3 | Science | p-i-n | [10.1126/science.aed8175](https://doi.org/10.1126/science.aed8175) |
| 27.12 | Nature Communications | p-i-n | [10.1038/s41467-026-74018-8](https://doi.org/10.1038/s41467-026-74018-8) |
| 26.94 | Advanced Materials | p-i-n | [10.1002/adma.74316](https://doi.org/10.1002/adma.74316) |
| 26.84 | Advanced Energy Materials | p-i-n | [10.1002/aenm.71305](https://doi.org/10.1002/aenm.71305) |
| 26.82 | Angewandte Chemie International Edition | p-i-n | [10.1002/anie.8080769](https://doi.org/10.1002/anie.8080769) |
| 26.52 | Science Advances | unknown | [10.1126/sciadv.aed6327](https://doi.org/10.1126/sciadv.aed6327) |
| 26.18 | Nature Communications | tandem_2T | [10.1038/s41467-026-75305-0](https://doi.org/10.1038/s41467-026-75305-0) |
| 26.14 | Advanced Materials | p-i-n | [10.1002/adma.74033](https://doi.org/10.1002/adma.74033) |
| 26.1 | Science | unknown | [10.1126/science.aef1969](https://doi.org/10.1126/science.aef1969) |
| 25.9 | Advanced Energy Materials | tandem_2T | [10.1002/aenm.71267](https://doi.org/10.1002/aenm.71267) |
| 25.75 | Nature Communications | unknown | [10.1038/s41467-026-75053-1](https://doi.org/10.1038/s41467-026-75053-1) |
| 23.5 | Science | module | [10.1126/science.aeg1730](https://doi.org/10.1126/science.aeg1730) |
| 23.26 | Nano Energy | p-i-n | [10.1016/j.nanoen.2026.112222](https://doi.org/10.1016/j.nanoen.2026.112222) |
| 23.1 | Science Advances | module | [10.1126/sciadv.aee4175](https://doi.org/10.1126/sciadv.aee4175) |
| 14.67 | Angewandte Chemie International Edition | p-i-n | [10.1002/anie.7827890](https://doi.org/10.1002/anie.7827890) |

## Note S6. Limitations

Venue-impact-prioritised selection under-samples preprints, regional journals and non-English venues, so the depth subset is biased toward well-indexed English-language publishing. Work that circulates chiefly on preprint servers or in regional venues can carry mechanism results and reporting habits that this digest never sees. Abstracts in languages other than English were machine translated, and translation can blur technical wording, which is a second reason to read the small non-English share of the corpus with care.

Because indexing lags publication, this digest describes the indexed record of July 2026 as of 2026-07, not the month itself. The lag is uneven. Articles that appeared late in July, or that reach the indexes only afterwards, are absent from every count here and will surface in later months.

The audit is measured on abstracts, not full texts, because full-text retrieval succeeded for only 5% of the month's papers. An abstract omitting a measurement is not evidence the measurement was absent. The rates therefore characterise disclosure in summaries rather than practice in the laboratory, and they should be read as a floor. Because the hand-labelled validation set is not yet complete, every corpus-level percentage in this section is reported as a lower bound using the phrase "detected in at least", with no precision or recall figure attached.

This is the first month in the series, so no trend or month-over-month comparison is available. Statements that a reporting rate is rising or stalling cannot be supported yet; several months processed by the same pipeline are needed before these numbers mean anything beyond a single snapshot.

Four limitations are specific to this build. First, the reporting audit is unvalidated pending the human label set (Note S3). Second, the depth tier is built on abstracts by decision: a full-text retrieval probe succeeded for only 5% of the month's papers, and a diagnostic across three months of differing age showed the failure is publisher refusal of automated retrieval rather than indexing delay, since a fourteen-month-old month retrieved worse than a two-month-old one. The audit therefore measures reported summaries, and the extraction records quote abstracts rather than full texts. Third, operational stability evidence is thin in an absolute sense: 4 papers reported a T80 lifetime and 6 named an ISOS protocol, which limits what any review can conclude about degradation this month. Fourth, this issue covers a single month, so nothing in it is a trend; the first month-over-month comparison becomes possible with the next issue.

## Note S7. Automated gate report for this build

| Gate | Status | Summary |
| --- | --- | --- |
| G4 | pass | em-dash 0, banned 0, self-report leaks 0 |
| G1 | pass | 79 citations resolved, 0 unresolved |
| G2c-cite-count | pass | 79 cited, target [60, 85], 39.1 words per citation |
| G2 | pass | 3092 words, 8 sections within 135% of ceiling |
| G2b-cite-order | pass | {"first_appearance_sequence": [], "monotonic": true} |
| G6 | pass | {"hits": []} |
| G3-abstract | pass | {"unverified": [], "words": 299, "placeholders_resolved": ["A_MAX", "H |
| G3c-abstract-physics | pass | {"implausible": [], "sj_limit_pct": 29.4} |
| G3b-abstract-form | pass | {"words": 299, "band": [260, 340], "citation_markers": 0} |
| G7-abbrev | pass | {"expanded_automatically": ["SAMs", "MPPT", "ISOS", "SAMs", "SAM"], "s |
| G8-novelty | pass | worst section 0.075 vs 0.25, abstract 0.033 vs 0.3, 0 shared shingles |
| G9a-notation | pass | {"residual_defects": {}, "ambiguous_for_human_review": {}, "substituti |
| G9b-cite-links | pass | {"hyperlinked_markers": 136, "unlinked_markers": [], "works_without_do |
| G9c-figure-unique | pass | {"attached": ["F1_certified_frontier.pdf", "F4_stability_evidence.pdf" |
| G9d-model-names | pass | {"bare_slugs_found": [], "declared": ["qwen3.8-flash", "gemini-3.8-fla |
| G10-title-block | pass | {"gaps_pt": {"author_to_affil": 14.42, "affil_to_date": 22.52, "date_t |
| G5 | pass | 15 pages, 9.6 content |

Gate definitions. G1 requires every citation marker in the main text to resolve to an extraction record carrying its own source quotation. G2 enforces length and structure ceilings and records a SHA-256 fingerprint of each drafted section, so a gate result is permanently bound to the text it judged. G4 enforces prose hygiene: em-dash count, a banned vocabulary list, and detection of leaked model self-commentary. G6 forbids first-person experimental claims, since this is a review of other groups' work. The main-text abstract carries the additional numeric gate described in Note S2.
