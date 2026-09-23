# Supplementary Information

For "Perovskite Photovoltaics in January-June 2026: The Certified Frontier From Cell to Module"

Havid Aqoma, September 14, 2026

This Supplementary Information contains the corpus construction and selection method (Note S1), the extraction and evidence-chain method (Note S2), the full reporting audit (Note S3), the corpus statistics (Note S4), the complete certified-record table (Note S5), the limitations (Note S6), the automated gate report for this build (Note S7), the half-year assembly method (Note S8), a date-precision limitation in the first month (Note S9), device-family assignment (Note S10), illumination conditions and excluded efficiencies (Note S11), the corpus denominators (Note S14), what was and was not verified automatically (Note S12), and how to check any number in this review (Note S13).

## Note S1. Corpus construction and selection

The corpus came from an OpenAlex title-and-abstract search for perovskite AND ("solar cell" OR photovoltaic), restricted to January-June 2026 publication dates and to the work types article, preprint and review. That set was unioned with records from Semantic Scholar, Crossref and arXiv and de-duplicated by DOI; exclusion terms are applied in Python after retrieval, never inside the query. Of 3328 works meeting the scope gate, 2238 had a usable abstract and 884 met the depth-review threshold.

The depth tier is built on abstracts by decision, not by omission: a full-text retrieval probe succeeded for about 5% of a month's papers, and the failure is publisher refusal of automated retrieval rather than indexing delay. Selection is a constrained draw over venue citation percentile and mechanism axis with per-axis minima and venue and institution share caps, seeded for reproducibility. Across 200 sensitivity draws the median Jaccard overlap of the selected set was 1.0, with 819 papers appearing in every draw.

**Table S1.** Records retrieved by source.

| Source | Records retrieved |
| --- | --- |
| OpenAlex (keyed, cursor-paginated) | 3418 |
| Semantic Scholar (bulk) | 1417 |
| Crossref | 1200 |
| arXiv | 59 |
| **Corpus after de-duplication and topical post-filter** | **3328** |
| With a usable abstract | 2238 |
| Non-English (machine translated) | 40 |
| Preprints | 183 |

**Table S2.** Selection funnel.

| Stage | Works |
| --- | --- |
| Passed the scope gate | 3328 |
| Usable abstract (eligibility) | 2213 |
| Depth tier (selected for close reading) | 884 |
| Extraction records surviving all guards | 872 |
| Dropped: no verifiable claim survived | 12 |
| Cited in the main text | 184 |
| Audited but not cited individually | 688 |

![**Figure S1.** Corpus construction funnel.](runs/2026-H1/fig/S2_corpus_funnel.pdf){width=85%}

## Note S2. Extraction and the evidence chain

Every closely read paper was passed through a structured extraction step that returned numeric fields, each bound to a verbatim quotation from that paper's own abstract. Three deterministic guards were then applied by script, never by the extracting model: first, the quotation must appear word for word in the source abstract. Second, the numeric value must appear inside its own quotation, and third, the quotation is truncated to 25 words before that check rather than after it, so a value can never be separated from the words that prove it. Any field failing a guard is nulled and counted, and a paper whose extraction left no verifiable claim was dropped from the cited set rather than shipped with an unprovable record (12 of 884 this month).

Independent re-verification of the shipped records, run as a separate script against the source abstracts, found every quotation present verbatim, none exceeding 25 words, and no numeric value missing from its own quotation. The abstract of the main text carries an additional gate: every numeral in it must exist either in the statistics file or in an extraction record, and each named scientific highlight is bound to one explicit record by its DOI, so a highlight cannot silently attach a real number to the wrong paper.

## Note S3. The full reporting audit

This note reports how completely the January-June 2026 papers describe their own measurements. The audit reads abstracts, so it measures what authors chose to summarise, not what appears in an experimental section or in supporting information. Two tiers are covered: a corpus tier of 2238 abstracts and a depth tier of 884 abstracts.

Because the hand-labelled validation set for the detector is not yet complete, every percentage here is a lower bound and is written as "detected in at least", with no precision or recall figure attached. In the corpus tier an efficiency value was detected in at least 52.1% of abstracts, a stabilised or maximum-power-point-tracked efficiency in at least 11.0%, independent certification in at least 8.5%, an active or aperture area in at least 8.4%, and a complete open-circuit voltage, short-circuit current density and fill factor triplet in at least 2.9%. An ISOS stability-protocol label was detected in at least 1.7% and an explicit hysteresis statement in at least 2.7%. Table S3 gives both tiers side by side.

**Table S3.** Reporting-completeness detection rates. All values are lower bounds obtained by pattern detection on abstracts, not by human reading.

| Reporting item | Corpus (n=2238) | Depth (n=884) |
| --- | --- | --- |
| Efficiency value stated | 52.1% | 61.3% |
| Stabilised or MPPT value | 11.0% | 17.3% |
| Independent certification | 8.5% | 14.1% |
| Device area stated | 8.4% | 13.2% |
| Hysteresis or scan direction | 2.7% | 3.2% |
| ISOS protocol label | 1.7% | 3.3% |
| Complete Voc / Jsc / FF triplet | 2.9% | 0.2% |

![**Figure S2.** Reporting-completeness detection rates, corpus and depth tiers.](runs/2026-H1/fig/S1_reporting_audit.pdf){width=90%}

Two properties of these rates govern how they should be read. They are measured on abstracts, so they describe what authors chose to summarise rather than what was measured in the laboratory: an abstract omitting a device area is not evidence that the area went unrecorded. They are also lower bounds, because the hand-labelled validation set that would attach a precision and recall figure to each pattern is not yet complete. No percentage becomes exact until its precision reaches 0.85 against human labels, and until then every figure in this note carries that caveat without restating it.

## Note S4. Corpus statistics

**Table S4.** Mechanism-axis distribution.

| Mechanism axis | Corpus | Depth | Share of corpus |
| --- | --- | --- | --- |
| composition | 1360 | 152 | 40.9% |
| defects | 560 | 224 | 16.8% |
| interfaces | 651 | 207 | 19.6% |
| architecture | 324 | 112 | 9.7% |
| stability | 292 | 116 | 8.8% |
| scale up | 141 | 73 | 4.2% |

Axis assignment uses weighted keyword scoring over title and abstract across six fixed axes, with the title weighted twice, and mechanism centrality is the winning axis score normalised by that axis maximum. Selection into the depth tier scores venue citation percentile (0.40), mechanism centrality (0.35) and novelty (0.25), subject to a floor of 12 papers per axis, a preprint reservation, and per-venue and per-institution caps.

One caveat on the selection statistics is worth stating plainly: in this first issue the novelty term is constant, because it is defined against a cumulative history of extracted records that does not yet exist, so ranking reduces to venue percentile plus mechanism centrality. Repeating the selection under 200 perturbed weightings therefore returns a selection overlap of 1.0 with 819 papers selected in almost every draw. That number should be read as a consequence of the flat novelty term, not as evidence that the selector is robust; it becomes informative from the third issue onward.

## Note S5. Every certified efficiency reported in the month

Of 872 closely read papers, 114 reported an independently certified efficiency; the complete list follows, highest first, and each DOI is a live link.

| Certified PCE (%) | Venue | Architecture | DOI |
| --- | --- | --- | --- |
| 34.85 | Advanced Optical Materials | tandem_2T | [10.1002/adom.202503341](https://doi.org/10.1002/adom.202503341) |
| 33.6 | Science | tandem_2T | [10.1126/science.aef5355](https://doi.org/10.1126/science.aef5355) |
| 33.5 | Nature Communications | tandem_2T | [10.1038/s41467-026-72794-x](https://doi.org/10.1038/s41467-026-72794-x) |
| 33.48 | Science Advances | tandem_2T | [10.1126/sciadv.aec4431](https://doi.org/10.1126/sciadv.aec4431) |
| 33.37 | Advanced Energy Materials | tandem_2T | [10.1002/aenm.71107](https://doi.org/10.1002/aenm.71107) |
| 33.04 | Nature Communications | tandem_2T | [10.1038/s41467-026-73656-2](https://doi.org/10.1038/s41467-026-73656-2) |
| 32.95 | Nature Communications | tandem_2T | [10.1038/s41467-026-73276-w](https://doi.org/10.1038/s41467-026-73276-w) |
| 32.81 | Advanced Materials | tandem_2T | [10.1002/adma.73106](https://doi.org/10.1002/adma.73106) |
| 32.46 | ACS Energy Letters | tandem_2T | [10.1021/acsenergylett.5c04127](https://doi.org/10.1021/acsenergylett.5c04127) |
| 32.45 | Nature Communications | tandem_2T | [10.1038/s41467-026-72160-x](https://doi.org/10.1038/s41467-026-72160-x) |
| 32.1 | Angewandte Chemie International Edition | tandem_2T | [10.1002/anie.5162616](https://doi.org/10.1002/anie.5162616) |
| 31.93 | eScience | tandem_2T | [10.1016/j.esci.2026.100563](https://doi.org/10.1016/j.esci.2026.100563) |
| 31.52 | Advanced Energy Materials | unknown | [10.1002/aenm.71077](https://doi.org/10.1002/aenm.71077) |
| 30.3 | Nature Nanotechnology | tandem_2T | [10.1038/s41565-026-02165-6](https://doi.org/10.1038/s41565-026-02165-6) |
| 29.44 | Nature Communications | tandem_2T | [10.1038/s41467-026-73210-0](https://doi.org/10.1038/s41467-026-73210-0) |
| 29.2 | Nature Communications | tandem_2T | [10.1038/s41467-025-68213-2](https://doi.org/10.1038/s41467-025-68213-2) |
| 28.98 | Advanced Materials | tandem_2T | [10.1002/adma.202523338](https://doi.org/10.1002/adma.202523338) |
| 28.79 | Angewandte Chemie International Edition | tandem_2T | [10.1002/anie.4918900](https://doi.org/10.1002/anie.4918900) |
| 28.57 | Advanced Materials | tandem_2T | [10.1002/adma.73038](https://doi.org/10.1002/adma.73038) |
| 28.53 | ACS Energy Letters | tandem_2T | [10.1021/acsenergylett.6c00617](https://doi.org/10.1021/acsenergylett.6c00617) |
| 28.34 | ACS Energy Letters | tandem_2T | [10.1021/acsenergylett.6c00227](https://doi.org/10.1021/acsenergylett.6c00227) |
| 28.25 | Nano-Micro Letters | tandem_2T | [10.1007/s40820-025-01962-3](https://doi.org/10.1007/s40820-025-01962-3) |
| 27.99 | Advanced Materials | tandem_2T | [10.1002/adma.73011](https://doi.org/10.1002/adma.73011) |
| 27.7 | Nature Communications | tandem_2T | [10.1038/s41467-026-70848-8](https://doi.org/10.1038/s41467-026-70848-8) |
| 27.6 | Science | unknown | [10.1126/science.aeb9953](https://doi.org/10.1126/science.aeb9953) |
| 27.41 | Nature | unknown | [10.1038/s41586-026-10626-0](https://doi.org/10.1038/s41586-026-10626-0) |
| 27.28 | Science Advances | unknown | [10.1126/sciadv.aef6596](https://doi.org/10.1126/sciadv.aef6596) |
| 27.1 | Advanced Materials | p-i-n | [10.1002/adma.202517596](https://doi.org/10.1002/adma.202517596) |
| 27.03 | Nature Communications | p-i-n | [10.1038/s41467-026-72097-1](https://doi.org/10.1038/s41467-026-72097-1) |
| 27.02 | Nature Communications | unknown | [10.1038/s41467-026-71845-7](https://doi.org/10.1038/s41467-026-71845-7) |
| 26.9 | Nature Energy | unknown | [10.1038/s41560-026-01993-z](https://doi.org/10.1038/s41560-026-01993-z) |
| 26.9 | Nature Communications | unknown | [10.1038/s41467-026-73426-0](https://doi.org/10.1038/s41467-026-73426-0) |
| 26.85 | Advanced Materials | p-i-n | [10.1002/adma.73529](https://doi.org/10.1002/adma.73529) |
| 26.84 | Nature Communications | unknown | [10.1038/s41467-026-74107-8](https://doi.org/10.1038/s41467-026-74107-8) |
| 26.8 | Advanced Materials | p-i-n | [10.1002/adma.73855](https://doi.org/10.1002/adma.73855) |
| 26.79 | Nature Communications | p-i-n | [10.1038/s41467-026-72115-2](https://doi.org/10.1038/s41467-026-72115-2) |
| 26.78 | Advanced Materials | unknown | [10.1002/adma.202520432](https://doi.org/10.1002/adma.202520432) |
| 26.75 | Angewandte Chemie International Edition | unknown | [10.1002/anie.202525815](https://doi.org/10.1002/anie.202525815) |
| 26.71 | Advanced Materials | p-i-n | [10.1002/adma.73306](https://doi.org/10.1002/adma.73306) |
| 26.69 | Advanced Materials | unknown | [10.1002/adma.72823](https://doi.org/10.1002/adma.72823) |
| 26.64 | Advanced Materials | p-i-n | [10.1002/adma.73358](https://doi.org/10.1002/adma.73358) |
| 26.64 | Advanced Materials | n-i-p | [10.1002/adma.73286](https://doi.org/10.1002/adma.73286) |
| 26.61 | Advanced Energy Materials | module | [10.1002/aenm.71159](https://doi.org/10.1002/aenm.71159) |
| 26.6 | Science | p-i-n | [10.1126/science.aea3339](https://doi.org/10.1126/science.aea3339) |
| 26.57 | Nature Communications | p-i-n | [10.1038/s41467-026-71301-6](https://doi.org/10.1038/s41467-026-71301-6) |
| 26.5 | Science | n-i-p | [10.1126/science.aea8228](https://doi.org/10.1126/science.aea8228) |
| 26.5 | Advanced Materials | p-i-n | [10.1002/adma.72622](https://doi.org/10.1002/adma.72622) |
| 26.48 | Nature Communications | p-i-n | [10.1038/s41467-026-72159-4](https://doi.org/10.1038/s41467-026-72159-4) |
| 26.44 | Advanced Energy Materials | p-i-n | [10.1002/aenm.70966](https://doi.org/10.1002/aenm.70966) |
| 26.44 | ACS Energy Letters | p-i-n | [10.1021/acsenergylett.6c01257](https://doi.org/10.1021/acsenergylett.6c01257) |
| 26.4 | Journal of the American Chemical Society | p-i-n | [10.1021/jacs.5c18303](https://doi.org/10.1021/jacs.5c18303) |
| 26.4 | Advanced Functional Materials | p-i-n | [10.1002/adfm.75697](https://doi.org/10.1002/adfm.75697) |
| 26.37 | Journal of the American Chemical Society | unknown | [10.1021/jacs.6c02548](https://doi.org/10.1021/jacs.6c02548) |
| 26.37 | Angewandte Chemie International Edition | n-i-p | [10.1002/anie.9551164](https://doi.org/10.1002/anie.9551164) |
| 26.35 | Journal of the American Chemical Society | unknown | [10.1021/jacs.5c16976](https://doi.org/10.1021/jacs.5c16976) |
| 26.35 | Advanced Energy Materials | p-i-n | [10.1002/aenm.70806](https://doi.org/10.1002/aenm.70806) |
| 26.33 | Advanced Energy Materials | p-i-n | [10.1002/aenm.70925](https://doi.org/10.1002/aenm.70925) |
| 26.31 | Advanced Energy Materials | p-i-n | [10.1002/aenm.71068](https://doi.org/10.1002/aenm.71068) |
| 26.3 | Nature Communications | tandem_2T | [10.1038/s41467-026-68904-4](https://doi.org/10.1038/s41467-026-68904-4) |
| 26.29 | Advanced Materials | n-i-p | [10.1002/adma.73161](https://doi.org/10.1002/adma.73161) |
| 26.27 | Nature Communications | n-i-p | [10.1038/s41467-026-72793-y](https://doi.org/10.1038/s41467-026-72793-y) |
| 26.24 | Angewandte Chemie International Edition | p-i-n | [10.1002/anie.202523665](https://doi.org/10.1002/anie.202523665) |
| 26.24 | Advanced Materials | p-i-n | [10.1002/adma.202522825](https://doi.org/10.1002/adma.202522825) |
| 26.23 | Nature Communications | n-i-p | [10.1038/s41467-026-69198-2](https://doi.org/10.1038/s41467-026-69198-2) |
| 26.22 | Advanced Materials | unknown | [10.1002/adma.202522508](https://doi.org/10.1002/adma.202522508) |
| 26.2 | Angewandte Chemie International Edition | p-i-n | [10.1002/anie.8890696](https://doi.org/10.1002/anie.8890696) |
| 26.2 | Advanced Materials | p-i-n | [10.1002/adma.73656](https://doi.org/10.1002/adma.73656) |
| 26.15 | Nature Communications | p-i-n | [10.1038/s41467-026-72790-1](https://doi.org/10.1038/s41467-026-72790-1) |
| 26.13 | Advanced Materials | p-i-n | [10.1002/adma.202523249](https://doi.org/10.1002/adma.202523249) |
| 26.12 | Advanced Functional Materials | p-i-n | [10.1002/adfm.76756](https://doi.org/10.1002/adfm.76756) |
| 26.1 | Nature Communications | unknown | [10.1038/s41467-026-72581-8](https://doi.org/10.1038/s41467-026-72581-8) |
| 26.09 | Angewandte Chemie International Edition | tandem_2T | [10.1002/anie.5905435](https://doi.org/10.1002/anie.5905435) |
| 26.07 | Nature Communications | unknown | [10.1038/s41467-026-69391-3](https://doi.org/10.1038/s41467-026-69391-3) |
| 26.07 | Advanced Materials | p-i-n | [10.1002/adma.73382](https://doi.org/10.1002/adma.73382) |
| 26.03 | ACS Energy Letters | unknown | [10.1021/acsenergylett.6c00476](https://doi.org/10.1021/acsenergylett.6c00476) |
| 25.98 | Angewandte Chemie International Edition | unknown | [10.1002/anie.3920745](https://doi.org/10.1002/anie.3920745) |
| 25.94 | Advanced Materials | p-i-n | [10.1002/adma.202519339](https://doi.org/10.1002/adma.202519339) |
| 25.9 | InfoMat | p-i-n | [10.1002/inf2.70140](https://doi.org/10.1002/inf2.70140) |
| 25.85 | Advanced Materials | p-i-n | [10.1002/adma.73373](https://doi.org/10.1002/adma.73373) |
| 25.8 | Science Advances | unknown | [10.1126/sciadv.aea7629](https://doi.org/10.1126/sciadv.aea7629) |
| 25.8 | Nature Communications | tandem_2T | [10.1038/s41467-026-73743-4](https://doi.org/10.1038/s41467-026-73743-4) |
| 25.66 | Nano Letters | p-i-n | [10.1021/acs.nanolett.5c05593](https://doi.org/10.1021/acs.nanolett.5c05593) |
| 25.62 | Nature Communications | n-i-p | [10.1038/s41467-025-68231-0](https://doi.org/10.1038/s41467-025-68231-0) |
| 25.61 | Nature Energy | unknown | [10.1038/s41560-026-02027-4](https://doi.org/10.1038/s41560-026-02027-4) |
| 25.6 | Science Advances | tandem_2T | [10.1126/sciadv.aed2200](https://doi.org/10.1126/sciadv.aed2200) |
| 25.56 | Nano-Micro Letters | tandem_2T | [10.1007/s40820-025-02037-z](https://doi.org/10.1007/s40820-025-02037-z) |
| 25.56 | Advanced Materials | unknown | [10.1002/adma.73679](https://doi.org/10.1002/adma.73679) |
| 25.55 | Science Advances | unknown | [10.1126/sciadv.aec3238](https://doi.org/10.1126/sciadv.aec3238) |
| 25.4 | Science | p-i-n | [10.1126/science.aea0656](https://doi.org/10.1126/science.aea0656) |
| 25.36 | Angewandte Chemie International Edition | p-i-n | [10.1002/anie.202525625](https://doi.org/10.1002/anie.202525625) |
| 25.11 | ACS Nano | p-i-n | [10.1021/acsnano.5c21709](https://doi.org/10.1021/acsnano.5c21709) |
| 24.5 | ACS Energy Letters | tandem_2T | [10.1021/acsenergylett.5c04203](https://doi.org/10.1021/acsenergylett.5c04203) |
| 23.55 | Nature Communications | module | [10.1038/s41467-026-69685-6](https://doi.org/10.1038/s41467-026-69685-6) |
| 23.48 | Advanced Materials | tandem_2T | [10.1002/adma.202521129](https://doi.org/10.1002/adma.202521129) |
| 23.47 | Nature Communications | tandem_2T | [10.1038/s41467-026-71017-7](https://doi.org/10.1038/s41467-026-71017-7) |
| 23.42 | Nano-Micro Letters | tandem_4T | [10.1007/s40820-025-01959-y](https://doi.org/10.1007/s40820-025-01959-y) |
| 23.0 | FlexMat. | module | [10.1002/flm2.70045](https://doi.org/10.1002/flm2.70045) |
| 22.02 | Nature Communications | unknown | [10.1038/s41467-026-69687-4](https://doi.org/10.1038/s41467-026-69687-4) |
| 21.95 | Advanced Energy Materials | unknown | [10.1002/aenm.202505854](https://doi.org/10.1002/aenm.202505854) |
| 21.74 | Angewandte Chemie International Edition | unknown | [10.1002/anie.4293157](https://doi.org/10.1002/anie.4293157) |
| 21.69 | Advanced Materials | unknown | [10.1002/adma.72756](https://doi.org/10.1002/adma.72756) |
| 21.54 | Nature Communications | tandem_4T | [10.1038/s41467-026-72099-z](https://doi.org/10.1038/s41467-026-72099-z) |
| 21.42 | Science Advances | unknown | [10.1126/sciadv.aea7043](https://doi.org/10.1126/sciadv.aea7043) |
| 21.34 | Advanced Energy Materials | p-i-n | [10.1002/aenm.71216](https://doi.org/10.1002/aenm.71216) |
| 20.62 | ACS Energy Letters | p-i-n | [10.1021/acsenergylett.6c00820](https://doi.org/10.1021/acsenergylett.6c00820) |
| 20.35 | Nature Communications | unknown | [10.1038/s41467-026-73709-6](https://doi.org/10.1038/s41467-026-73709-6) |
| 20.04 | Advanced Functional Materials | unknown | [10.1002/adfm.202521919](https://doi.org/10.1002/adfm.202521919) |
| 20.02 | Advanced Energy Materials | tandem_2T | [10.1002/aenm.70755](https://doi.org/10.1002/aenm.70755) |
| 19.95 | Advanced Materials | tandem_2T | [10.1002/adma.202521898](https://doi.org/10.1002/adma.202521898) |
| 18.48 | eScience | module | [10.1016/j.esci.2026.100601](https://doi.org/10.1016/j.esci.2026.100601) |
| 18.35 | Nature Materials | unknown | [10.1038/s41563-026-02494-w](https://doi.org/10.1038/s41563-026-02494-w) |
| 15.88 | Advanced Materials | unknown | [10.1002/adma.202519934](https://doi.org/10.1002/adma.202519934) |
| 15.06 | Rare Metals | unknown | [10.1002/rar2.70162](https://doi.org/10.1002/rar2.70162) |
| 11.22 | Nature Communications | unknown | [10.1038/s41467-026-72272-4](https://doi.org/10.1038/s41467-026-72272-4) |

## Note S6. Limitations

Venue-impact-prioritised selection under-samples preprints, regional journals and non-English venues, so the depth subset is biased toward well-indexed English-language publishing. Work circulating chiefly on preprint servers or in regional venues can carry mechanism results and reporting habits this review never sees. Of the corpus, 183 records are preprints and 40 were machine translated from another language; translation can blur technical wording.

Because indexing lags publication, this review describes the indexed record of January-June 2026 as retrieved at build time, not the month itself. The lag is uneven, and work published late in the month is systematically under-represented relative to work published early. A later rebuild of the same month would retrieve a larger corpus, which is why no publication count appears in the title.

Four limitations are specific to this build: first, the reporting audit is unvalidated pending the human label set (Note S3). Second, the depth tier is built on abstracts by decision: a full-text retrieval probe succeeded for only 5% of the month's papers, and a diagnostic across three months of differing age showed the failure is publisher refusal of automated retrieval rather than indexing delay, since a fourteen-month-old month retrieved worse than a two-month-old one. The audit therefore measures reported summaries, and the extraction records quote abstracts rather than full texts. Third, operational stability evidence is thin in an absolute sense: 39 papers reported a T80 lifetime and 39 named an ISOS protocol, which limits what any review can conclude about degradation this month. Fourth, this issue covers a single month, so nothing in it is a trend; the first month-over-month comparison becomes possible with the next issue.

## Note S7. Automated gate report for this build

| Gate | Status | Summary |
| --- | --- | --- |
| G4 | pass | em-dash 0, banned 0, self-report leaks 0 |
| G1 | pass | 184 citations resolved, 0 unresolved |
| G2c-cite-count | pass | 184 cited, target [150, 250], 49.8 words per citation |
| G2 | pass | 9158 words, 9 sections within 135% of ceiling |
| G2b-cite-order | pass | {"first_appearance_sequence": [], "monotonic": true} |
| G6 | pass | {"hits": []} |
| G3-abstract | pass | {"unverified": [], "words": 444, "placeholders_resolved": ["A_MAX", "H |
| G3c-abstract-physics | pass | {"implausible": [], "sj_limit_pct": 29.4} |
| G3d-illumination | pass | {"non_one_sun_values": []} |
| G3b-abstract-form | pass | {"words": 444, "band": [380, 520], "citation_markers": 0} |
| G7-abbrev | pass | {"expanded_automatically": ["SAM", "HTL", "ISOS", "SAM", "ISOS", "SAMs |
| G8-novelty | pass | worst section 0.038 vs 0.25, abstract 0.006 vs 0.3, 0 shared shingles |
| G9a-notation | pass | {"residual_defects": {}, "ambiguous_for_human_review": {}, "substituti |
| G9b-cite-links | pass | {"hyperlinked_markers": 291, "unlinked_markers": [], "works_without_do |
| G9c-figure-unique | pass | {"attached": ["F1_certified_frontier.pdf", "F4_stability_evidence.pdf" |
| G9d-model-names | pass | {"bare_slugs_found": [], "declared": ["qwen3.8-flash", "gemini-3.8-fla |
| G10-title-block | pass | {"gaps_pt": {"author_to_affil": 14.42, "affil_to_date": 22.52, "date_t |
| G5 | pass | 34 pages, 22.6 content |

Gate definitions. G1 requires every citation marker in the main text to resolve to an extraction record carrying its own source quotation. G2 enforces length and structure ceilings and records a SHA-256 fingerprint of each drafted section, so a gate result is permanently bound to the text it judged. G4 enforces prose hygiene: em-dash count, a banned vocabulary list, and detection of leaked model self-commentary. G6 forbids first-person experimental claims, since this is a review of other groups' work. The main-text abstract carries the additional numeric gate described in Note S2.

## Note S8. Why a half-year edition, and how it was assembled

This review covers six consecutive months rather than one. The reason is not simply scale. A single month can report where a quantity stands; it cannot report whether that quantity moved. Six months of the same measurement, assembled on identical criteria, can distinguish a ceiling that rose from a ceiling that was restated, and can show which physical problems gained and lost attention. Those are the questions this edition is built to answer, and they are the reason the trajectory and cross-cutting sections exist in the main text.

The corpus was not harvested as one six-month query. Each month was collected, filtered, ranked and extracted separately, on the same criteria, at the time that month was current; the half-year corpus is the union of those six completed passes. This matters for a reason that is easy to overlook: publisher indexing is not stable in time. A retrieval diagnostic across months of differing age found that older months return automated requests less successfully than recent ones, so re-collecting January many months later would not recover January, it would lose part of it. Assembling from contemporaneous passes preserves what was actually visible in each month.

Because the six passes were independent, none of the extracted records was re-derived for this edition. Every quantitative claim here rests on the same verified record that supported it when its month was current, which also means the numbers in this issue agree by construction with the numbers in the corresponding monthly issues rather than by coincidence.

**Table S8.** Corpus contribution by month.

| Month | Indexed works in scope | Read closely |
| --- | --- | --- |
| January | 475 | 122 |
| February | 499 | 131 |
| March | 559 | 146 |
| April | 589 | 164 |
| May | 583 | 154 |
| June | 623 | 167 |
| **Total** | **3328** | **884** |

Month boundaries are exclusive, so no work appears in two months: 0 duplicate records were found across the six months, which is the expected result and was verified rather than assumed.

## Note S9. A date-precision limitation in the first month

One month of this window required a decision that affects what the edition may claim, and it is recorded here in full because it changes a reported count.

Bibliographic databases assign a placeholder publication date when a record carries only a year, or an issue date without a day. For the first month of this window that placeholder is the first of January, and a scope-filtered query returned 1311 works for the month of which 823 -- roughly two thirds -- carried exactly that placeholder date. Inspection of a sample confirmed these are real, in-scope papers published in leading venues; the problem is not relevance but date precision.

Two options were available. Including them would inflate January and attribute to it papers that may have appeared at any point in the year. Excluding them understates January. This edition excludes them: a review titled for a specific span of months should not assert a publication month that the underlying record cannot support, and a count that is too low is a stated limitation whereas a count that is wrongly attributed is an error. January is therefore represented by the 488 works carrying a resolved day, and its contribution to this edition should be read as a lower bound.

The consequence is visible and small: January contributes 12.6% of the closely read papers against 19.2% for June, where even representation would be 16.7%. That spread also reflects genuine indexing maturity, since recent months are more completely indexed than older ones. No month falls below the coverage floor set for this edition, so the period title describes the corpus honestly, but the earliest month is the least complete and comparisons that hinge on January alone should be treated with corresponding caution.

## Note S10. How device families were assigned

The main text is organised by device family rather than by mechanism, so the assignment rule determines what every headline number means. It is deliberately conservative, and the reasoning is worth stating because the obvious approach is wrong.

A paper's title describes the paper. It does not necessarily describe the device that a particular number was measured on, and in this literature the difference is common rather than exotic: an abstract reporting a new contact layer may quote its own single-junction result and, in the same breath, the tandem record that motivates the work. Assignment therefore uses the verbatim quotation bound to each individual number, falling back to the reported architecture and only then to the title. A number and the device it is attributed to must come from the same sentence.

Three consequences follow, each of which changed a reported value.

First, tandems are separated by partner. A perovskite paired with a second perovskite absorber faces different limits from a perovskite paired with silicon, and both differ from a perovskite paired with an organic, chalcopyrite, telluride or kesterite absorber. Grouping all non-silicon partners with all-perovskite devices, which a simpler rule would do, misdescribed nineteen papers in this corpus as all-perovskite tandems when their partner was an organic or chalcopyrite cell.

Second, module classification requires an area. A module is a size, so a module claim is credited only when the quotation carrying the device area names one, and only when that area is at least one square centimetre. Without the area condition, papers reporting both a laboratory cell and a module in one sentence were credited as modules at sub-0.1 square centimetre areas, which would corrupt precisely the cell-to-module comparison the module section exists to make.

Third, a value whose own quotation names a different family than its paper is excluded from that family's frontier rather than reassigned. In one case a genuine module study quoted a certified tandem-cell record; reported as a module result it would have asserted a module efficiency that does not exist. Exclusion costs a superlative, whereas admission would create a record.

**Table S10.** Device-family assignment.

| Device family | Papers | Assigned from |
| --- | --- | --- |
| Single junction | 692 | device named in the quotation carrying each number |
| All-perovskite tandem | 60 | device named in the quotation carrying each number |
| Perovskite/silicon and other hybrid tandems | 77 | device named in the quotation carrying each number |
| Module | 43 | device named in the quotation carrying each number |

A further 47 papers describe a tandem without naming the partner anywhere in the text available to this review. They are not silently assigned: they are grouped with all-perovskite tandems for section purposes and counted separately here, because in this corpus a silicon or chalcopyrite partner is almost always named in the title, being the point of the work. Readers who need a strict all-perovskite count should use 13 rather than the section total.

## Note S11. Illumination conditions, and why some efficiencies are excluded from every table and figure

Efficiencies in this edition are one-sun values measured under the standard terrestrial reference spectrum. Several papers in the corpus report efficiencies measured under indoor or low-light illumination instead, and those values are excluded from every table, every figure and every frontier statement in the main text. They are not excluded because they are wrong. They are excluded because they are not comparable, and the distinction matters enough to explain.

The efficiency limit that bounds a single-junction solar cell is derived for a specific incident spectrum. Indoor illumination from a light-emitting diode or a fluorescent lamp is spectrally narrow and several orders of magnitude weaker than sunlight, and it is far better matched to a wide-bandgap absorber. A conversion efficiency measured under such a source can therefore legitimately exceed the one-sun single-junction limit while the absolute power delivered is on the order of microwatts per square centimetre rather than tens of milliwatts. The highest such value in this corpus is more than 44%, which is a correct result for its measurement condition and would be impossible for the same device under sunlight.

Placing such a value in a column of one-sun records would invite exactly the wrong conclusion, and a table cell has no room to carry the qualification that makes it meaningful. Deleting the work altogether would misrepresent the literature in the opposite direction, since indoor photovoltaics is an active application area with its own figures of merit. This edition therefore excludes these values from all quantitative displays and discusses them in the main text with their illumination condition stated alongside the number.

**Table S11.** Indoor and low-light efficiencies identified in the corpus (4 values across 4 papers), excluded from all main-text tables and figures.

| Reported PCE | Device family | Illumination stated | Source |
| --- | --- | --- | --- |
| 44.36% | Single junction | pce(i), pipvs, μw cm | [10.1007/s40820-026-02225-5](https://doi.org/10.1007/s40820-026-02225-5) |
| 41.6% | Module | indoor, lux, tl84 | [10.1002/smtd.70654](https://doi.org/10.1002/smtd.70654) |
| 16.36% | Single junction | lx | [10.1021/acsenergylett.5c04174](https://doi.org/10.1021/acsenergylett.5c04174) |
| 12.53% | Hybrid tandem | indoor, lux | [10.1016/j.rineng.2026.110377](https://doi.org/10.1016/j.rineng.2026.110377) |

A further 3 papers report an indoor and a one-sun efficiency within a single sentence. For these the review cannot establish which condition the extracted value belongs to, so they are excluded from both the one-sun statistics and the indoor list above. This is a reporting-practice observation as much as a methodological one: a sentence that pairs two illumination conditions with two efficiencies leaves any automated or human reader to guess.

The same principle governs simulated results. Studies reporting device efficiencies from numerical modelling rather than fabricated hardware are excluded from every measured-performance figure and from all frontier values, and their count is reported per family in the main text. A modelled efficiency and a measured one answer different questions, and the corpus contains modelled single-junction efficiencies above the practical one-sun limit that would otherwise appear beside certified hardware.

## Note S14. Which denominator applies to which number

This review reports rates against four different denominators, and using the wrong one changes a percentage substantially. They are set out here so that any figure quoted from this edition can be reproduced exactly.

**Table S14.** Corpus quantities and what each one counts.

| Quantity | Value | What it counts |
| --- | --- | --- |
| Works in scope | 3328 | records passing the topical filter across the six months |
| With a usable abstract | 2238 | the denominator for all corpus-level reporting rates |
| Eligible for close reading | 2213 | works meeting the criteria for individual assessment |
| Read closely | 884 | the depth tier, and the denominator for all depth-level rates |
| Yielding a verified record | 872 | papers with at least one quantity provable from their own abstract |

A worked distinction: a reporting rate described as a share of the corpus is computed against works with a usable abstract, because a record with no abstract cannot be scanned for a reporting practice and including it would understate every rate. The same practice measured across the closely read papers uses the depth tier as its denominator instead, which is why the two tiers give different percentages for the same property. Both are reported, and the difference between them is itself informative: closely read papers report more completely than the corpus average, which is consistent with the selection favouring higher-visibility venues.

The gap between papers read closely (884) and papers yielding a verified record (872) is not a processing failure. It is the count of papers whose abstracts contained no quantity that could be proved from the abstract itself. Those papers informed the reading but are not cited for numbers they did not state in a form this review could verify.

## Note S12. What was verified automatically, and what was not

This edition was produced by an automated pipeline, and the honest description of its reliability is that verification is uneven: some properties are checked exhaustively and mechanically, others rest on judgement, and a reader is entitled to know which is which.

Checked exhaustively, on every record, with the build refusing to complete on any failure: that each citation in the main text resolves to an extraction record; that each such record carries a quotation reproduced word for word from the cited paper's own abstract; that each numeric value appears inside its own quotation and within a twenty-five word window of it; that no numeral in the abstract exists without a corresponding statistic or record; that no efficiency presented as a single-junction result exceeds the physical limit for one junction; that no value presented as a performance record was measured under indoor illumination; that every reference in the list is cited in the text and every citation resolves to a listed reference; that citation numbering increases monotonically; that units and chemical formulae are typeset rather than written as plain text; and that the prose contains no first-person experimental claim, since this reviews other groups' work.

Checked mechanically but reported rather than enforced: the reporting completeness rates of Note S3 and their per-family breakdown. These are pattern-detection rates over abstracts. They are lower bounds, and they measure what authors chose to summarise rather than what was done in the laboratory.

Not verified automatically, and stated as such: whether the mechanistic interpretations in the main text are correct. The pipeline can prove that a number is real, that it belongs to the device and the illumination condition it is attributed to, and that it is quoted from the paper that reported it. It cannot prove that the physical explanation assembled around those numbers is the right one. That remains a matter for the reader's judgement and for the cited literature, which is why every claim in the main text carries its citation and every number in this Supplementary Information can be traced to a quotation.

The extraction and drafting steps used language models; the corpus construction, filtering, ranking, statistics, figures, tables and all verification described above are deterministic procedures that produce the same output from the same inputs. No figure or table in this edition is a model-generated image or a model-written number: every panel and cell is plotted or filled directly from the extraction records. The declaration in the main text names the models used for the steps that used them, derived from what actually ran rather than from configuration.

## Note S13. How to check any number in this review

Every quantitative claim in the main text can be traced by a reader with no access to the pipeline, using the data files distributed with this edition.

To check a cited claim, take the citation number, read the corresponding reference, and locate that paper's record in the extraction file supplied with the data package. The record carries each extracted quantity together with the verbatim sentence from that paper's abstract in which the quantity appears. Comparing the sentence with the published abstract verifies both the number and the context it was taken from.

To check a statistic, consult the statistics file, which contains every number this review is permitted to quote, including all rates with their numerators and denominators, the per-month series behind every trajectory statement, and the per-family aggregates behind every table. To check a figure, use the corresponding data file, which contains the plotted rows and, where values were excluded, the exclusions with the reason for each.

Two properties of the aggregates are worth knowing when checking them. Rates spanning the six months are computed by summing numerators and denominators across months, not by averaging the six monthly percentages: the months differ in size, from 475 to 623 works in scope, so an average of rates would weight a thin month equally with a thick one. And every rate is reported with its monthly range alongside the pooled value, because a quantity that varied widely across the period and one that stayed flat are different findings that share the same mean.

