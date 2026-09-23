# Supplementary Information

## Perovskite Photovoltaics in 2025: Annual Mechanism and Reporting Audit

This document states the method, the per-period audit tables and the limitations of the accompanying review. Every number here is computed by script from the run records; no part of this document is model-written.

## Note S0. How to read this review

This review was produced by an automated pipeline under human review, and the pipeline is not a language model asked to write about perovskites. It is a sequence of deterministic stages -- literature retrieval, scope filtering, ranked selection, structured extraction, statistics, figures and format gates -- with a language model used at exactly two points: extracting structured records from abstracts, and writing the prose of the numbered sections. Everything else is script output.

The distinction matters for how much weight to place on any number you read, so three categories run through the whole document:

- **Verified.** The value appears word for word in a cited paper's own abstract, and an independent script re-confirmed that quotation against the source. Every efficiency, area and lifetime in the main text is in this category.
- **Computed.** The value was calculated by script from verified values -- counts, pooled percentages, month-by-month series, so it can be recomputed from the data pack.
- **Detected.** A regular expression found a phrase in an abstract, and the reporting-practice rates in Note S4 are in this category: they are lower bounds rather than measurements. Note S4 explains why.

No number in the main text was produced by a language model reasoning about physics. Where the prose interprets, the interpretation is the model's; where the prose states a quantity, the quantity came from a quotation.

### What this review can and cannot tell you

It **can** tell you what the year's abstracts reported, how much of it was independently verified, and where the reported evidence is internally inconsistent or thin.

It **cannot** tell you what happened in experimental sections, supporting information or figures, because those were not read. A paper that measured a quantity carefully but did not mention it in its abstract is recorded here as not reporting it. Every rate in Note S4 should be read with that ceiling in mind.

## Note S1. Corpus construction and selection

The corpus came from an OpenAlex title-and-abstract search for perovskite AND ("solar cell" OR photovoltaic), restricted to 2025 publication dates and to the work types article, preprint and review. The search returned 7931 works in a single annual sweep. Exclusion terms are applied in Python after retrieval, never inside the query: an exclusion placed in the query returns a count of zero rather than a filtered set, and a zero is indistinguishable from a legitimately empty period.

**This issue was assembled retrospectively:** it was compiled from the complete 2025 publication record after the year had closed, not by monitoring the literature month by month during 2025. Readers should not treat the month-by-month series in the main text as a record of contemporaneous monitoring.

Of 7931 works meeting the scope gate, 5062 carried a usable abstract of at least forty words (63.8% of the corpus), and 450 met the depth-review threshold.

The depth tier is built on abstracts by decision, not by omission: a full-text retrieval probe succeeds for roughly five per cent of papers, and the failure is publisher refusal of automated retrieval rather than indexing delay. Abstract coverage of about two thirds therefore supports a far tighter confidence interval than a full-text tier of one twentieth the size.

### The selection funnel, stage by stage

Four numbers describe how the corpus narrowed, and each drop has a stated reason:

1. **7931 works** matched the topical query for 2025.
2. **7931 works** survived the scope gate. The gate removes non-English records, retracted records, and papers where perovskite photovoltaics is mentioned only in passing.
3. **5062 works** carried a usable abstract of at least forty words. An abstract shorter than that cannot support a quotation-bound claim.
4. **450 works** entered the depth tier and were read closely enough to extract structured records.

Nothing was discarded for being uninteresting. The narrowing is mechanical, and the counts at each stage are in the data pack so the funnel can be audited rather than trusted.

![**Figure S1.** The selection funnel. Percentages are of the works retrieved. The depth tier is a small fraction of the corpus, which is the honest framing of what this review read.](yearly/runs/2025_6cb0e6ed/fig/S1_corpus_funnel.pdf){width=88%}

### What each month contributed

The annual figures above are sums over twelve monthly passes. The breakdown is given here so that any annual number in this review can be traced to the months that produced it, rather than taken on trust.

| Month | In corpus | Usable abstract | Read closely | Certified reports |
|---------|---------|---------|-------|---------|
| 2025-01 | 480 | 316 | 34 | 8 |
| 2025-02 | 478 | 322 | 36 | 4 |
| 2025-03 | 544 | 368 | 35 | 6 |
| 2025-04 | 614 | 450 | 37 | 4 |
| 2025-05 | 607 | 422 | 37 | 0 |
| 2025-06 | 567 | 383 | 27 | 3 |
| 2025-07 | 576 | 411 | 25 | 8 |
| 2025-08 | 555 | 367 | 33 | 6 |
| 2025-09 | 550 | 406 | 42 | 7 |
| 2025-10 | 621 | 434 | 35 | 7 |
| 2025-11 | 600 | 398 | 29 | 7 |
| 2025-12 | 650 | 453 | 43 | 5 |
| Dated to year only | 1,089 | -- | -- | -- |
| **Total** | **7,931** | **4,730** | **413** | **65** |

Every column in this table reconciles against a figure stated elsewhere in the review, and the build fails rather than printing a breakdown that does not add up. The corpus column plus the year-only works equals the annual corpus, and the usable-abstract column sums to the audit denominator used throughout Note S4. The read-closely column plus the depth-tier papers carrying no month equals the depth tier, and the certified column sums to the count of certified papers in Table 1 of the main text.

Month boundaries are exclusive, so no work is counted twice: 0 duplicate records were found across the twelve months, which was verified rather than assumed.

### Why those particular papers were read closely

The depth tier is not the top-cited papers, and it is not a random sample. It is a constrained draw that scores each eligible paper on three things: the citation percentile of its publication venue, how central the paper is to one of the mechanism axes the pipeline tracks, and whether it introduces vocabulary the corpus has not seen.

Two constraints then apply. Each mechanism axis has a minimum number of papers, so a small but real subfield cannot be crowded out by a large one. And no single journal or institution may exceed a fixed share of the tier, so a prolific group cannot dominate the reading list, while the draw is seeded so that the same corpus reproduces the same selection.

**Venue quality informs selection only:** it is never a reported metric, a ranking key, or an axis on a figure. A journal-level statistic cannot be traced to a quotation in an individual paper's abstract, so it has no place in a claim a reader is asked to check. Its legitimate use is deciding which papers get read closely, and that use is disclosed here rather than hidden.

### Stability of the selection

The draw was repeated many times with different random seeds to test whether the reading list is an artefact of one lucky draw. The overlap between draws is reported in the statistics file: a high overlap means the selection is driven by the scoring rather than by chance, while a low overlap would mean the tier is arbitrary and the review's coverage claims would be correspondingly weaker.

## Note S2. Publication-date precision

OpenAlex stores an imprecise publication date as the first of January, and in the raw 2025 record January carried roughly three times the works of any other month, which is an artefact of that default rather than a January surge in publication.

Every work therefore carries a date-precision flag. 1089 works are dated only to the year. They remain in the corpus, because they are real papers, and they are excluded from every month-by-month series, because their month is unknown. No date is silently reassigned. The month-resolved corpus covers 12 months.

## Note S3. The evidence chain

Every number in the main text traces to a verbatim quotation from the cited paper's own abstract. Extraction is guarded in a fixed order:

1. the quotation must appear word for word in the source abstract;
2. the numeric value must appear inside its own quotation;
3. quotations are truncated to twenty-five words BEFORE check 2 is applied;
4. a device label is taken from the value's own quotation, never from the paper's title;
5. where a certified value's quotation names a multi-junction stack, the recorded architecture is corrected to match the number.

Guard order is not cosmetic. Applying check 2 before truncation admits fields whose quotation ends immediately before its own number.

### A worked example

Suppose an abstract contains the sentence:

> *Buried-interface homogenisation yields inverted cells reaching 25.8 per cent, and we further demonstrate a certified 32.95 per cent perovskite/silicon tandem efficiency.*

One sentence, two devices, two numbers. Handled naively this is where a review acquires a false record: the paper is about inverted single-junction cells, so a device label taken from the paper would attach 32.95 per cent to a single junction. That value is impossible for a single junction, and the error would be invisible to any check that only asked whether the number appeared in the source.

The guards resolve it as follows: guard 1 confirms the quotation exists word for word. Guard 3 truncates the quotation to twenty-five words. Guard 2 then confirms that 32.95 lies inside its own truncated quotation, not merely somewhere in the abstract. Guard 4 reads the device label from that quotation, which names a perovskite/silicon tandem. Guard 5 corrects the recorded architecture to match, so the value is filed as a tandem.

Each number therefore carries the device its own sentence described, and the two values in this example end up in different sections of the review, compared against different physical limits.

### Illumination conditions

A physical limit is defined for a set of measurement conditions, not for a number. The Shockley-Queisser ceiling quoted throughout this review is derived for the AM1.5G solar spectrum. Under indoor or weak artificial light the incident spectrum is narrow and far better matched to a wide-gap absorber, and a device can exceed the solar ceiling without anything being wrong.

The pipeline therefore records the illumination condition attached to each value, read from the value's own quotation. Indoor and weak-light measurements are excluded from every figure and table that draws a solar limit line, and the number of exclusions is recorded per device class in the data pack.

Two subtleties are worth stating, because both were found the hard way: first, papers routinely report a solar value and an indoor value in the same sentence, so the condition must be read from the text immediately around each number rather than from the sentence as a whole; otherwise a legitimate solar measurement is discarded along with the indoor one. Second, a value with no stated condition is treated as a standard-conditions measurement, because that is the overwhelming default in this literature. The residual risk is therefore an indoor value surviving onto a solar figure, not a solar value being deleted.

Independent re-verification of the extracted set, by a script sharing no code with the extraction stage: 450 cards carrying 1655 anchors, of which 1655 were confirmed verbatim, 0 exceeded the twenty-five-word limit and 0 had a value missing from its own quotation. Status: pass.

## Note S4. Reporting-practice audit

This note reports how completely the 2025 papers describe their own measurements. The audit reads ABSTRACTS, so it measures what authors chose to summarise, not what appears in an experimental section or in supporting information.

**Because the hand-labelled validation set for the detector is not yet complete, every percentage below is a lower bound.** Each is written as "detected in at least", with no precision or recall figure attached, because a bare percentage would imply a validated detector.

An annual percentage here is the summed numerator over the summed denominator, never the mean of the monthly percentages. Months carry different denominators, so averaging the rates would weight a thin month equally with a thick one.

| Quantity | Detected in at least | Denominator | Monthly range |
|-------------------|--------|-----------|-------|
| an efficiency value | 51.6% | 4730 | 47.8% to 54.0% |
| independent certification | 5.8% | 4730 | 3.4% to 7.6% |
| a stabilised or maximum-power-point value | 8.8% | 4730 | 6.2% to 12.0% |
| a device area | 7.3% | 4730 | 5.2% to 9.3% |
| a named ISOS stability protocol | 1.1% | 4730 | 0.2% to 3.2% |
| hysteresis or scan-direction information | 3.1% | 4730 | 1.6% to 4.3% |

The thin rows are the finding. A reporting quantity that almost no abstract states is a fact about the field's practice, and the monthly range distinguishes a rate that sat flat all year from one that swung.

![**Figure S2.** Reporting completeness. Diamonds mark the pooled annual rate, bars the monthly range, and the figures at the right give the detected count over the denominator. Every rate is a lower bound: the detector reads abstracts only.](yearly/runs/2025_6cb0e6ed/fig/S2_reporting_audit.pdf){width=88%}

### How these rates are obtained, and what could go wrong

Each quantity has a pattern that searches an abstract for the language authors use when they report it. Independent certification is looked for as a claim of certification by a named test centre; a stated area is looked for as a number followed by a unit of area; a stability protocol is looked for as an ISOS label. The patterns are applied by script, and the model's own view of whether a paper reported something is discarded.

Two failure modes follow, and they pull in opposite directions: a pattern can **miss** a paper that reported the quantity in unusual words. This is the dominant error, and it is why every rate is a lower bound: the true share is at least what is printed here, probably somewhat higher. A pattern can also **over-count** by matching language that looks like a report but is not, such as a sentence describing what other groups have certified.

One over-counting case has been fixed and is worth stating because it shows the class of problem. A current density written as milliamps per square centimetre contains a unit of area, so a naive area pattern counted it as a stated device area, and current densities are now excluded. Others of this kind may remain.

The honest position is that the direction of the error is known but its size is not. Quantifying it requires a set of papers labelled by hand, which does not yet exist. Until then these rates should be read as evidence that a practice is rare or common, never as a measurement of how rare or common.

### Why the annual figure is not an average of the months

Months differ in size. Adding twelve monthly percentages and dividing by twelve would give a thin month the same weight as a thick one, and the answer can be badly wrong: a month reporting ten of a hundred and a month reporting none of nine hundred average to five per cent, while the true pooled share is one per cent.

Every annual figure here is the total number of papers reporting the quantity divided by the total number of abstracts examined. The monthly range is printed alongside so a reader can see whether the pooled figure describes a steady practice or an average across a wide swing.

## Note S5. The certified-efficiency trajectory, and every certified value behind it

| Month | Best certified | Best self-reported | Certified reports |
|-------|---------|-------------|---------|
| 2025-01 | 30.26 | 30.78 | 8 |
| 2025-02 | 27.17 | 31.5 | 4 |
| 2025-03 | 28.78 | 30.3 | 6 |
| 2025-04 | 28.31 | 28.55 | 4 |
| 2025-05 | none reported | 33.2 | 0 |
| 2025-06 | 28.81 | 30.49 | 3 |
| 2025-07 | 26.56 | 31.56 | 8 |
| 2025-08 | 33.15 | 33.15 | 6 |
| 2025-09 | 31.47 | 32.33 | 7 |
| 2025-10 | 28.9 | 29.6 | 7 |
| 2025-11 | 26.96 | 32.39 | 7 |
| 2025-12 | 30.1 | 33.5 | 5 |

Values in this table are drawn from measured reports only, and simulation and review studies are excluded from the measured frontier: a computed efficiency standing beside certified hardware would misrepresent both.

A month showing no certified value is a month in which no closely read paper reported one. It is a gap in the evidence, not a zero.

That distinction is deliberate and matters for how the trajectory should be read, because a zero would assert that the best certified device that month achieved nothing. A gap asserts only that the depth tier contains no certified value for that month, which given how few papers report certification at all is an ordinary outcome rather than a finding, and figures render such months as gaps and never interpolate across them.

### What the month axis does and does not mean

The month attached to each paper is its publication date as recorded by the indexing service, not the date the work was done. A device measured in one quarter and published in the next appears in the later month. The series therefore describes when results entered the literature, which is the only thing a literature review can observe.

Works whose publication date is known only to the year carry no month and are absent from every point on the series while remaining in the corpus totals. Note S2 gives the count, and this is why the month-by-month figures do not sum to the annual corpus.

### Every certified efficiency reported in the year

The trajectory above plots one point per month, the best certified value that month, and the complete set behind it is listed here, 65 certified values in all, grouped by device class and ordered highest first within each class. The top row of each block is therefore the class champion quoted in Table 1 of the main text, and the build fails if it is not.

Rows are one per extracted value, not one per paper. Table 1 counts papers. The two agree here because no paper in this corpus reported more than one certified value, which was checked rather than assumed.

| Device class | Certified PCE (%) | Area (cm2) | DOI |
|------------------|---------|------|------------------------------------------------------------------------------|
| Single-junction cells | 26.96 | not stated | [10.1038/s41566-025-01791-1](https://doi.org/10.1038/s41566-025-01791-1) |
|  | 26.79 | not stated | [10.1002/adma.202505115](https://doi.org/10.1002/adma.202505115) |
|  | 26.65 | not stated | [10.1002/aenm.202503252](https://doi.org/10.1002/aenm.202503252) |
|  | 26.56 | not stated | [10.1016/j.esci.2025.100451](https://doi.org/10.1016/j.esci.2025.100451) |
|  | 26.48 | not stated | [10.1038/s41467-025-64550-4](https://doi.org/10.1038/s41467-025-64550-4) |
|  | 26.35 | not stated | [10.1002/adfm.202510458](https://doi.org/10.1002/adfm.202510458) |
|  | 26.33 | not stated | [10.1002/anie.202518592](https://doi.org/10.1002/anie.202518592) |
|  | 26.3 | not stated | [10.1002/aenm.202503780](https://doi.org/10.1002/aenm.202503780) |
|  | 26.28 | not stated | [10.1038/s41467-025-66421-4](https://doi.org/10.1038/s41467-025-66421-4) |
|  | 26.23 | not stated | [10.1002/adma.202514735](https://doi.org/10.1002/adma.202514735) |
|  | 26.21 | not stated | [10.1002/adma.202419413](https://doi.org/10.1002/adma.202419413) |
|  | 26.12 | not stated | [10.1002/anie.202510255](https://doi.org/10.1002/anie.202510255) |
|  | 26.12 | not stated | [10.1002/anie.202519875](https://doi.org/10.1002/anie.202519875) |
|  | 26.05 | not stated | [10.1002/adfm.202425443](https://doi.org/10.1002/adfm.202425443) |
|  | 26.03 | not stated | [10.1002/aenm.202502409](https://doi.org/10.1002/aenm.202502409) |
|  | 26.03 | not stated | [10.1002/aenm.202503781](https://doi.org/10.1002/aenm.202503781) |
|  | 26.02 | not stated | [10.1038/s41467-024-55653-5](https://doi.org/10.1038/s41467-024-55653-5) |
|  | 25.59 | not stated | [10.1002/anie.202425605](https://doi.org/10.1002/anie.202425605) |
|  | 25.44 | not stated | [10.1038/s41467-025-56409-5](https://doi.org/10.1038/s41467-025-56409-5) |
|  | 25.38 | not stated | [10.1002/anie.202511317](https://doi.org/10.1002/anie.202511317) |
|  | 25.18 | not stated | [10.1038/s41467-025-55815-z](https://doi.org/10.1038/s41467-025-55815-z) |
|  | 25.13 | not stated | [10.1021/acsenergylett.5c01081](https://doi.org/10.1021/acsenergylett.5c01081) |
|  | 25.11 | not stated | [10.1021/jacs.5c20051](https://doi.org/10.1021/jacs.5c20051) |
|  | 25.0 | not stated | [10.1002/aenm.202500572](https://doi.org/10.1002/aenm.202500572) |
|  | 24.9 | not stated | [10.1002/adma.202508740](https://doi.org/10.1002/adma.202508740) |
|  | 24.7 | not stated | [10.1002/adma.202500988](https://doi.org/10.1002/adma.202500988) |
|  | 24.08 | not stated | [10.1126/sciadv.adr2290](https://doi.org/10.1126/sciadv.adr2290) |
|  | 24.01 | not stated | [10.1021/acsami.5c07089](https://doi.org/10.1021/acsami.5c07089) |
|  | 22.9 | not stated | [10.1038/s41467-024-55652-6](https://doi.org/10.1038/s41467-024-55652-6) |
| All-perovskite tandems | 29.2 | not stated | [10.1038/s41467-025-62661-6](https://doi.org/10.1038/s41467-025-62661-6) |
|  | 28.9 | not stated | [10.1038/s41467-025-64274-5](https://doi.org/10.1038/s41467-025-64274-5) |
|  | 28.52 | not stated | [10.1126/sciadv.adv4501](https://doi.org/10.1126/sciadv.adv4501) |
|  | 28.31 | not stated | [10.1038/s41467-025-58810-6](https://doi.org/10.1038/s41467-025-58810-6) |
|  | 28.11 | not stated | [10.1038/s41467-025-56549-8](https://doi.org/10.1038/s41467-025-56549-8) |
|  | 27.92 | not stated | [10.1038/s41467-025-62391-9](https://doi.org/10.1038/s41467-025-62391-9) |
|  | 27.17 | not stated | [10.1021/acsenergylett.4c03370](https://doi.org/10.1021/acsenergylett.4c03370) |
|  | 19.72 | not stated | [10.1126/sciadv.ady3621](https://doi.org/10.1126/sciadv.ady3621) |
| Perovskite/silicon and other hybrid tandems | 33.15 | not stated | [10.1038/s41467-025-62389-3](https://doi.org/10.1038/s41467-025-62389-3) |
|  | 31.47 | not stated | [10.1002/anie.202509782](https://doi.org/10.1002/anie.202509782) |
|  | 31.4 | not stated | [10.1021/acsenergylett.5c01244](https://doi.org/10.1021/acsenergylett.5c01244) |
|  | 30.26 | not stated | [10.1038/s41467-024-55377-6](https://doi.org/10.1038/s41467-024-55377-6) |
|  | 30.1 | not stated | [10.1038/s41467-025-67350-y](https://doi.org/10.1038/s41467-025-67350-y) |
|  | 28.9 | not stated | [10.1038/s41467-025-63673-y](https://doi.org/10.1038/s41467-025-63673-y) |
|  | 28.81 | not stated | [10.1002/adma.202504321](https://doi.org/10.1002/adma.202504321) |
|  | 28.06 | not stated | [10.1002/adma.202513281](https://doi.org/10.1002/adma.202513281) |
|  | 28 | not stated | [10.1021/jacs.5c13264](https://doi.org/10.1021/jacs.5c13264) |
|  | 27.3 | not stated | [10.1021/acs.accounts.5c00612](https://doi.org/10.1021/acs.accounts.5c00612) |
|  | 25.45 | not stated | [10.1002/anie.202504237](https://doi.org/10.1002/anie.202504237) |
|  | 21.42 | not stated | [10.1002/inf2.12656](https://doi.org/10.1002/inf2.12656) |
| Modules and large-area devices | 28.78 | not stated | [10.1038/s41467-025-58111-y](https://doi.org/10.1038/s41467-025-58111-y) |
|  | 26.65 | not stated | [10.1038/s41467-025-63389-z](https://doi.org/10.1038/s41467-025-63389-z) |
|  | 26.4 | not stated | [10.1038/s41467-025-64728-w](https://doi.org/10.1038/s41467-025-64728-w) |
|  | 25.9 | not stated | [10.1126/science.ado2351](https://doi.org/10.1126/science.ado2351) |
|  | 25.81 | not stated | [10.1002/anie.202512660](https://doi.org/10.1002/anie.202512660) |
|  | 25.67 | not stated | [10.1002/adma.202501057](https://doi.org/10.1002/adma.202501057) |
|  | 25.24 | not stated | [10.1021/acsenergylett.5c01711](https://doi.org/10.1021/acsenergylett.5c01711) |
|  | 25.2 | not stated | [10.1002/adma.202505475](https://doi.org/10.1002/adma.202505475) |
|  | 22.09 | not stated | [10.1021/acsnano.5c07208](https://doi.org/10.1021/acsnano.5c07208) |
|  | 22.06 | not stated | [10.1002/adma.202419750](https://doi.org/10.1002/adma.202419750) |
|  | 21.39 | not stated | [10.1002/adma.202419329](https://doi.org/10.1002/adma.202419329) |
|  | 20.95 | not stated | [10.1038/s41467-025-66752-2](https://doi.org/10.1038/s41467-025-66752-2) |
|  | 19.5 | not stated | [10.1038/s41467-025-64111-9](https://doi.org/10.1038/s41467-025-64111-9) |
|  | 18.83 | not stated | [10.1002/adfm.202423397](https://doi.org/10.1002/adfm.202423397) |
|  | 18.73 | not stated | [10.1002/aenm.202500598](https://doi.org/10.1002/aenm.202500598) |
|  | 15.3 | not stated | [10.1002/cey2.70123](https://doi.org/10.1002/cey2.70123) |

Each DOI is a live link. The verbatim quotation supporting every one of these values, together with the area and the illumination condition read from that same quotation, is in `extracted_claims.csv` in the data pack: one row per number, carrying the sentence it came from. The quotations are not reprinted here because the table would run to several pages while adding nothing a reader cannot already check.

An area of *not stated* means the abstract reported a certified efficiency without an aperture area. It is a gap in the source, not a gap in the extraction, and Note S4 gives the rate at which this happens across the corpus.

## Note S6. How device classes were assigned

Every table and figure in the main text is organised by device class, because a single number means different things in different architectures. A power conversion efficiency of 33.15% is impossible for a single junction and unremarkable for a tandem, so a review that pools them reports a frontier that belongs to no real device.

| Device class | Papers read | Measured | Simulation or review | Detailed-balance limit |
|------------------|------|--------|----------|----------------|
| Single-junction cells | 332 | 278 | 54 | 29.4% |
| All-perovskite tandems | 28 | 24 | 4 | 47.6% |
| Perovskite/silicon and other hybrid tandems | 47 | 44 | 3 | 47.6% |
| Modules and large-area devices | 43 | 41 | 2 | 47.6% |

The class is read from each value's OWN quotation, never from the paper's title: a paper about inverted single-junction cells that also reports a certified tandem contributes its tandem number to the tandem class and its single-junction number to the single-junction class. Note S3 works through exactly that case.

The limit in the last column is the detailed-balance ceiling that applies to that architecture under the AM1.5G spectrum. It is the number against which any claim in that class should be read, and it is why the classes are never pooled.

## Note S7. Illumination conditions, and the values excluded because of them

A detailed-balance limit is defined for a spectrum, not for a number, and the ceilings quoted in this review are derived for AM1.5G. Under indoor or weak artificial light the incident spectrum is narrow and far better matched to a wide-gap absorber, so a device can exceed the solar ceiling without anything being wrong with the device, the measurement, or the extraction.

**4 values across 4 papers were identified as indoor or weak-light measurements and excluded from every main-text table and figure that draws a solar limit.** They are listed here in full rather than silently dropped: an excluded value is not an erased one, and a reader who finds one of these numbers in the source should be able to see that the pipeline saw it too.

| Paper | Device class | Value (%) | Condition detected |
|--------------------------|---------------|-----|---------|
| 10.1007/s40820-025-01775-4 | Single-junction cells | 33.2 | indoor |
| 10.1002/adma.202419573 | Single-junction cells | 30.3 | unknown |
| 10.1002/adfm.202515665 | Single-junction cells | 21.9 | indoor |
| 10.1002/adfm.202527433 | Single-junction cells | 21.1 | unknown |

Two of these carry a detected condition of *unknown* rather than *indoor*, which is the truncation case described in Note S3: the quotation cap can cut the illumination marker off the end of an otherwise clear sentence, so the condition is read from the full source abstract, which the pipeline holds and has already verified. The quotation shown to a reader stays capped; what the pipeline may KNOW is not limited to what it may QUOTE.

Had these values been left in, the highest would have sat above the single-junction solar ceiling and made the issue appear to have found a field-wide integrity problem. It had not. The devices are real and the numbers are correctly reported by their authors; only the comparison would have been wrong.

An unmarked value is treated as a standard-conditions measurement, because that is the overwhelming default in this literature. The residual risk is therefore an indoor value surviving onto a solar figure, not a solar value being deleted.

## Note S8. What the closely read papers were about

The depth tier is drawn with a minimum quota per mechanism axis, so a small but real subfield cannot be crowded out by a large one. The distribution below is therefore a property of the SELECTION as much as of the literature, and should not be read as a measurement of what the field worked on in 2025.

| Mechanism axis | Papers read closely | Share of the depth tier |
|------------|-------|-----|
| defects | 172 | 38.2% |
| interfaces | 150 | 33.3% |
| architecture | 43 | 9.6% |
| composition | 30 | 6.7% |
| scale up | 29 | 6.4% |
| stability | 26 | 5.8% |

These counts sum to more than the depth tier where a paper is central to more than one axis, and the axis is assigned from the paper's own abstract rather than from its journal or keywords.

## Note S9. Which denominator applies to which number

This review reports counts drawn from five different populations, and a rate is meaningless without knowing which one it was divided by. Every quantity below is stated somewhere in the main text or in these notes, and each one enumerates something different.

| Quantity | Count | What it enumerates |
|-----------|-----|--------------|
| Works retrieved | 7931 | records returned by the 2025 topical query |
| Corpus | 7931 | works surviving the scope gate; the denominator for nothing except itself |
| Usable abstract | 5062 | works carrying an abstract of at least forty words |
| Audit denominator | 4730 | works with BOTH a usable abstract and a resolved month; the denominator of every rate in Note S4 |
| Depth tier | 450 | works read closely enough to extract structured records |
| Year-only dated | 1089 | works absent from every month-resolved count, including the audit denominator |

The audit denominator is smaller than the count of works with a usable abstract, and the difference is exactly the works dated only to the year. A monthly rate cannot be computed for a work with no month, so those works are excluded from the audit rather than assigned a month they do not have. This is why the reporting rates in Note S4 are divided by a number no other section uses.

No percentage in this review is a mean of monthly percentages, and every one is a summed numerator over a summed denominator, for the reason given in Note S4.

## Note S10. Limitations

1. **Abstract-based extraction.** Every claim comes from an abstract. A paper that reports a quantity only in its experimental section is recorded as not reporting it, so all audit rates are lower bounds.
2. **No validated detector.** The reporting-flag regular expressions have no hand-labelled precision or recall figure, which is the single highest-value outstanding task for the project.
3. **Retrospective assembly.** See Note S1. The month-by-month series reflects publication dates, not contemporaneous monitoring.
4. **Date precision.** Works dated only to the year are absent from every monthly series, as recorded in Note S2.
5. **No prior annual issue.** This is the first annual issue of this review, so it contains no year-over-year comparison. A comparison against a raw publication count from an earlier year would not be equivalent to a comparison against a prior audited issue.
6. **Venue coverage.** Some venues carry no citation percentile and score zero in selection, so they can enter the depth tier only through mechanism centrality.

## Note S11. Automated gate report

Each gate encodes a defect that reached a rendered page at least once, and a gate is never widened to admit output; the output is fixed instead.

| Gate | Status |
|--------------------|----------|
| G4 | pass |
| G1 | pass |
| G2c-cite-count | pass |
| G2 | pass |
| G2b-cite-order | pass |
| G6 | pass |
| G3-abstract | pass |
| G3c-abstract-physics | pass |
| G3b-abstract-form | pass |
| G7-abbrev | pass |
| G8-novelty | cold-start |
| G9a-notation | pass |
| G9b-cite-links | pass |
| G9c-figure-unique | pass |
| G9e-figures-present | pass |
| G9f-tables-present | pass |
| G9d-model-names | pass |
| G11-coverage | pass |
| G10-title-block | pass |
| G5 | pass |

A gate reported as *cold-start* could not run because it compares against a prior issue and none exists. It is deliberately not reported as a pass.

## Note S12. Data availability and reproduction

The accompanying data pack contains the corpus table, one row per extracted number WITH ITS VERBATIM QUOTATION, the per-month series, the frontier trajectory, the reporting audit with denominators, and the axis distribution. Abstract text and full texts are not redistributed.

The main text cites 170 of 170 listed references. Bracketed numbers above the reference count are chemical or crystallographic nomenclature, not citation markers, and are excluded from that count.

Section map fingerprint: `2382b7c2c99a0970`. The section structure is generated from the evidence mass, so the same corpus reproduces the same map.
