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

The consequence is visible and small. January contributes 12.6% of the closely read papers against 19.2% for June, where even representation would be 16.7%. That spread also reflects genuine indexing maturity, since recent months are more completely indexed than older ones. No month falls below the coverage floor set for this edition, so the period title describes the corpus honestly, but the earliest month is the least complete and comparisons that hinge on January alone should be treated with corresponding caution.

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
