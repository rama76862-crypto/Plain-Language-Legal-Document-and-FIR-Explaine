# Curated official reference set

This small Backend 2 demo set contains short English excerpts from official Indian government sources. `references.json` keeps each Contract v1 `ReferenceRecord` under `record`; sibling `provenance` fields document how the source was located and checked. The runtime's curated-reference loader reads the `law` and `record` fields and ignores the provenance metadata.

## Source and retrieval notes

| Reference ID | Official source and locator | Version and retrieval evidence |
| --- | --- | --- |
| `bnss_2023_s173` | [India Code, Bharatiya Nagarik Suraksha Sanhita, 2023](https://www.indiacode.nic.in/bitstream/123456789/21544/1/the_bharatiya_nagarik_suraksha_sanhita%2C_2023.pdf), printed p. 67, §173(2) | Act 46 of 2023; enacted 2023-12-25; generally in force from 2024-07-01. Official PDF text and printed page locator checked 2026-10-30. |
| `crpc_1973_s154` | [India Code, Code of Criminal Procedure, 1973](https://www.indiacode.nic.in/bitstream/123456789/21613/1/the_code_of_criminal_procedure%2C_1973.pdf), PDF page index 77, §154(2), with amendment footnote on the following page | Act 2 of 1974. The section 154 copy carries amendment notes through Act 22 of 2018; state amendments may differ. Official PDF text and footnote checked 2026-10-30. |
| `bns_2023_s316` | [India Code, Bharatiya Nyaya Sanhita, 2023](https://www.indiacode.nic.in/bitstream/123456789/20062/1/a2023-45.pdf), printed p. 94, §316(1) | Act 45 of 2023; enacted 2023-12-25; generally in force from 2024-07-01. The India Code PDF states text as on 2025-10-06; checked 2026-10-30. |
| `ecommerce_rules_2020_r2_1_a` | [Department of Consumer Affairs, Consumer Protection (E-Commerce) Rules, 2020](https://consumeraffairs.nic.in/sites/default/files/E%20commerce%20rules_0.pdf), rule 2(1)(a) | G.S.R. 462(E), 2020-07-23. The official PDF's indexed text exposed the excerpt, but opening the PDF timed out during this review. The official 2021 amendment checked here concerns rule 4(1), not a full later-amendment audit. Reopen and verify the direct PDF before release. |
| `ecommerce_rules_2020_r4_9` | [Department of Consumer Affairs, Consumer Protection (E-Commerce) Rules, 2020](https://consumeraffairs.nic.in/sites/default/files/E%20commerce%20rules_0.pdf), rule 4(9) | Same source and limitation as above. Rule 4(9) addresses consent in the E-Commerce Rules; it should not be generalized to every agreement. |
| `nalsa_faq_11` | [National Legal Services Authority FAQs](https://nalsa.gov.in/faqs/), FAQ 11 | The page displays no version date. FAQ text checked 2026-10-30; recheck before release because contact information may change. |

The `excerpt_sha256_utf8` values in the JSON are SHA-256 hashes of the exact UTF-8 excerpt strings, including punctuation, for change detection. They are not hashes of the source documents. Source URLs, locators, query strings, method, access date, and reuse note are retained in the manifest. Legal reproduction terms were not independently established; keep these excerpts short and attributed and check applicable reuse terms before wider distribution.

## Coverage and matching limits

- This is a small, English-only demonstration set, not a complete law database or an exhaustive update service. It covers central legislation and one official agency FAQ only.
- CrPC §154 and BNSS §173 are kept as separate source records. A section-number match does not establish that provisions have equivalent scope or effect.
- The E-Commerce Rules are kept with their nested rule locators (`2(1)(a)` and `4(9)`). Current pipeline citation parsing may not attach these rule records automatically.
- The NALSA FAQ is agency contact information, not legislation. It does not establish eligibility for services or guarantee a response.
- Retrieval's `exact_section_match` reports equality of curated metadata fields. It does not show that a source applies to a particular person or facts, or that a legal interpretation is correct. Semantic retrieval results remain candidates for review.
- The manifest contains no private documents and no synthetic source excerpts. Synthetic test queries below are lookup fixtures only, not legal evidence or citation claims.
