# Requirements to ontology and query traceability

These representative examples connect stakeholder requirements to ontology relationships and executable competency-question (CQ) tests. They document the current correspondence between the retained requirement statements and the implemented model. They are an explanatory mapping, rather than a claim that each complete interface requirement has been implemented or approved by its originator.

The requirement identifiers and summaries come from the WP2 co-design requirements extract supplied to T3.2. The extract contains 14 requirements and is not a register of workshop dates, attendance or all workshop outputs. Only requirement summaries are reproduced here; internal assessment comments are not included.

## Representative mappings

| Source requirement and summary | Source CQ to canonical CQ | Ontology representation | Query behaviour on fictional data |
|---|---|---|---|
| RO-CDW-03-01: facilitate access to educational content supporting health literacy | T32-CQ-04 → CQ-020 | `HealthLiteracyResource` → `healthLiteracyResourceAddressesNeed` → `HealthLiteracyNeedType`; knowledge-resource and social-context modules | Retrieves `InformationComprehensionSupportNeed` for the example resource. This supplies a need annotation for resource selection; it does not implement website access or establish improved literacy. |
| FI-CDW-01-07 and DE-CDW-03-08: show the sources of health information and suggestions | T32-CQ-03 and T32-CQ-10 → CQ-014; proposal-derived CQ-013 is also consolidated here | `KnowledgeResource` → `knowledgeResourceSupportsRecommendation` → `Recommendation`; knowledge-resource module | Retrieves the resource supporting the example walking recommendation. Source display is a consuming-interface function and is not tested by this query. |
| UK-CDW-01-03: curate information, avoid overwhelming lists and signpost for detailed advice | T32-CQ-07 → CQ-023 | `KnowledgeResource` → `knowledgeResourceHasComplexityLevel` → `ContentComplexityLevel`; knowledge-resource module | Retrieves `FoundationalComplexity` for the example resource. This represents one contribution to the broader requirement; it does not test cognitive burden, list length or professional referral. |
| IT-CDW-03-02: provide validated assessment tools | T32-CQ-16 → CQ-048 and T32-CQ-19 → CQ-051 | `MeasurementEvent` → `measurementEventUsesInstrument` → `MeasurementInstrument`; `MeasurementInstrument` → `measurementInstrumentHasValidationEvidence` → `EvidenceSource`; measurement-biomarker and knowledge-resource modules | CQ-048 retrieves the example measurement instrument. CQ-051 retrieves explicit validation evidence and excludes an unrelated background citation. These fictional records do not establish the clinical validity of a real instrument or implement its administration. |

## Inspecting the evidence

- [Canonical CQ register](../sources/icareonto_final_consolidated_competency_questions_v5.xlsx): “Final CQs” identifies ontology paths and source CQ identifiers; “Consolidation trace” records how source CQs became canonical questions.
- Queries: [CQ-014](cq-tests/queries/CQ-014.rq), [CQ-020](cq-tests/queries/CQ-020.rq), [CQ-023](cq-tests/queries/CQ-023.rq), [CQ-048](cq-tests/queries/CQ-048.rq) and [CQ-051](cq-tests/queries/CQ-051.rq).
- [Test cases and separately specified expected answers](cq-tests/cases.json).
- [Recorded query results](reports/cq-results.json), located by canonical CQ identifier.
- [Test methodology and reproduction guide](cq-tests/README.md).

The CQ register consolidates 59 proposal-derived source questions and 25 stakeholder-derived source questions into 78 canonical questions. The final set contains 54 proposal-only questions, 19 stakeholder-only questions and five questions supported by both sources. One shared question combines three source entries, accounting for six reductions across the five shared groups. These counts concern question entries, not numbers of workshops, people or independent requirements.

The direct requirement-to-CQ associations above explain the current model. The source-CQ-to-canonical-CQ links are retained in the versioned register. Query tests establish retrieval behaviour for the specified fictional graphs; clinical suitability and complete participant-facing functionality require their own assessment.

When requirements, canonical CQs or ontology relationships change, update these examples and check the referenced queries, expected answers and results together.
