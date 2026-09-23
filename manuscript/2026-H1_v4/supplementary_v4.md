# Supplementary Information

For "Perovskite Photovoltaics in January-June 2026: Defect passivation, interface and contact engineering"

Havid Aqoma, September 11, 2026

This Supplementary Information contains the corpus construction and selection method (Note S1), the extraction and evidence-chain method (Note S2), the full reporting audit (Note S3), the corpus statistics (Note S4), the complete certified-record table (Note S5), the limitations (Note S6), and the automated gate report for this build (Note S7).

## Note S1. Corpus construction and selection

The corpus came from an OpenAlex title-and-abstract search for perovskite AND ("solar cell" OR photovoltaic), restricted to January-June 2026 publication dates and to the work types article, preprint and review. That set was unioned with records from Semantic Scholar, Crossref and arXiv and de-duplicated by DOI. Exclusion terms are applied in Python after retrieval, never inside the query. Of 3328 works meeting the scope gate, 2238 had a usable abstract and 884 met the depth-review threshold.

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
| Cited in the main text | 0 |
| Audited but not cited individually | 872 |

![**Figure S1.** Corpus construction funnel.](runs/2026-H1/fig/S2_corpus_funnel.pdf){width=85%}

## Note S2. Extraction and the evidence chain

Every closely read paper was passed through a structured extraction step that returned numeric fields, each bound to a verbatim quotation from that paper's own abstract. Three deterministic guards were then applied by script, never by the extracting model. First, the quotation must appear word for word in the source abstract. Second, the numeric value must appear inside its own quotation. Third, the quotation is truncated to 25 words before that check rather than after it, so a value can never be separated from the words that prove it. Any field failing a guard is nulled and counted, and a paper whose extraction left no verifiable claim was dropped from the cited set rather than shipped with an unprovable record (12 of 884 this month).

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

Axis assignment uses weighted keyword scoring over title and abstract across six fixed axes, with the title weighted twice. Mechanism centrality is the winning axis score normalised by that axis maximum. Selection into the depth tier scores venue citation percentile (0.40), mechanism centrality (0.35) and novelty (0.25), subject to a floor of 12 papers per axis, a preprint reservation, and per-venue and per-institution caps.

One caveat on the selection statistics is worth stating plainly. In this first issue the novelty term is constant, because it is defined against a cumulative history of extracted records that does not yet exist, so ranking reduces to venue percentile plus mechanism centrality. Repeating the selection under 200 perturbed weightings therefore returns a selection overlap of 1.0 with 819 papers selected in almost every draw. That number should be read as a consequence of the flat novelty term, not as evidence that the selector is robust; it becomes informative from the third issue onward.

## Note S5. Every certified efficiency reported in the month

Of 872 closely read papers, 114 reported an independently certified efficiency. The complete list follows, highest first. Each DOI is a live link.

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

Four limitations are specific to this build. First, the reporting audit is unvalidated pending the human label set (Note S3). Second, the depth tier is built on abstracts by decision: a full-text retrieval probe succeeded for only 5% of the month's papers, and a diagnostic across three months of differing age showed the failure is publisher refusal of automated retrieval rather than indexing delay, since a fourteen-month-old month retrieved worse than a two-month-old one. The audit therefore measures reported summaries, and the extraction records quote abstracts rather than full texts. Third, operational stability evidence is thin in an absolute sense: 39 papers reported a T80 lifetime and 39 named an ISOS protocol, which limits what any review can conclude about degradation this month. Fourth, this issue covers a single month, so nothing in it is a trend; the first month-over-month comparison becomes possible with the next issue.

## Note S7. Automated gate report for this build

| Gate | Status | Summary |
| --- | --- | --- |
| G4 | pass | em-dash 0, banned 0, self-report leaks 0 |
| G1 | pass | 209 citations resolved, 0 unresolved |
| G2c-cite-count | pass | 209 cited, target [150, 250], 49.4 words per citation |
| G2 | pass | 10331 words, 11 sections within 135% of ceiling |
| G2b-cite-order | pass | {"first_appearance_sequence": [], "monotonic": true} |
| G6 | pass | {"hits": []} |
| G3-abstract | pass | {"unverified": [], "words": 462, "placeholders_resolved": ["A_MAX", "H |
| G3c-abstract-physics | pass | {"implausible": [], "sj_limit_pct": 29.4} |
| G3d-illumination | pass | {"non_one_sun_values": []} |
| G3b-abstract-form | pass | {"words": 462, "band": [380, 520], "citation_markers": 0} |
| G7-abbrev | pass | {"expanded_automatically": ["TCO", "HTL", "SAMs", "SAM", "SAM", "SAM", |
| G8-novelty | pass | worst section 0.04 vs 0.25, abstract 0.023 vs 0.3, 0 shared shingles |
| G9a-notation | pass | {"residual_defects": {}, "ambiguous_for_human_review": {}, "substituti |
| G9b-cite-links | pass | {"hyperlinked_markers": 301, "unlinked_markers": [], "works_without_do |
| G9c-figure-unique | pass | {"attached": ["F4_stability_evidence.pdf", "F2_area_penalty.pdf", "F3_ |
| G9d-model-names | pass | {"bare_slugs_found": [], "declared": ["qwen3.8-flash", "gemini-3.8-fla |
| G10-title-block | pass | {"gaps_pt": {"author_to_affil": 14.42, "affil_to_date": 22.52, "date_t |
| G5 | pass | 36 pages, 22.6 content |

Gate definitions. G1 requires every citation marker in the main text to resolve to an extraction record carrying its own source quotation. G2 enforces length and structure ceilings and records a SHA-256 fingerprint of each drafted section, so a gate result is permanently bound to the text it judged. G4 enforces prose hygiene: em-dash count, a banned vocabulary list, and detection of leaked model self-commentary. G6 forbids first-person experimental claims, since this is a review of other groups' work. The main-text abstract carries the additional numeric gate described in Note S2.
