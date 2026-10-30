/**
 * Development Mock Fixtures (Contract v1 Aligned)
 * ONLY imported or used when VITE_USE_FIXTURES=true.
 * Every fixture object carries __fixture: true.
 */

import type { ExtractionResponse, ResultObject, HealthResponse } from '../types';

export const fixtureHealth: HealthResponse = {
  status: 'healthy',
  extraction_ready: true,
  ocr_languages: ['eng', 'hin', 'pan'],
  model_ready: true,
  tested_matrix: {
    input: ['en', 'hi', 'pa'],
    output: ['en', 'hi', 'pa'],
  },
};

export const fixtureRentAgreementExtraction: ExtractionResponse = {
  document_id: 'doc_fixture_agreement_01',
  revision: 1,
  document_type: 'agreement',
  input_language: 'en',
  clauses: [
    {
      clause_id: 'c1',
      source_text: 'This Residential Lease Agreement is entered into on this 1st day of November 2026.',
      reviewed_text: 'This Residential Lease Agreement is entered into on this 1st day of November 2026.',
      source_ref: {
        page_number: 1,
        paragraph_index: null,
        bbox: [72.0, 700.0, 520.0, 725.0],
      },
      extraction_method: 'text',
      review_required: false,
    },
    {
      clause_id: 'c2',
      source_text: 'The Tenant agrees to pay a monthly rent of Rs. 25,000 payable on or before the 5th of each calendar month.',
      reviewed_text: 'The Tenant agrees to pay a monthly rent of Rs. 25,000 payable on or before the 5th of each calendar month.',
      source_ref: {
        page_number: 1,
        paragraph_index: null,
        bbox: [72.0, 640.0, 520.0, 680.0],
      },
      extraction_method: 'text',
      review_required: false,
    },
    {
      clause_id: 'c3',
      source_text: 'This lease shall automatically renew for successive terms of 12 months unless either party provides written notice of termination at least 60 days prior to the expiration.',
      reviewed_text: 'This lease shall automatically renew for successive terms of 12 months unless either party provides written notice of termination at least 60 days prior to the expiration.',
      source_ref: {
        page_number: 1,
        paragraph_index: null,
        bbox: [72.0, 560.0, 520.0, 610.0],
      },
      extraction_method: 'text',
      review_required: false,
    },
    {
      clause_id: 'c4',
      source_text: 'In the event of delay in rent beyond 10 days, a penalty of 18% per annum compounded monthly shall be levied.',
      reviewed_text: 'In the event of delay in rent beyond 10 days, a penalty of 18% per annum compounded monthly shall be levied.',
      source_ref: {
        page_number: 2,
        paragraph_index: null,
        bbox: [72.0, 720.0, 520.0, 755.0],
      },
      extraction_method: 'ocr',
      review_required: true,
    },
    {
      clause_id: 'c5',
      source_text: 'Tenant shall inspect the premises and report any preexisting damages within 15 days of receipt of keys.',
      reviewed_text: 'Tenant shall inspect the premises and report any preexisting damages within 15 days of receipt of keys.',
      source_ref: {
        page_number: 2,
        paragraph_index: null,
        bbox: [72.0, 650.0, 520.0, 690.0],
      },
      extraction_method: 'text',
      review_required: false,
    },
    {
      clause_id: 'c6',
      source_text: 'All disputes shall be referred to sole arbitration in New Delhi, and parties waive all rights to appeal before a civil court.',
      reviewed_text: 'All disputes shall be referred to sole arbitration in New Delhi, and parties waive all rights to appeal before a civil court.',
      source_ref: {
        page_number: 2,
        paragraph_index: null,
        bbox: [72.0, 580.0, 520.0, 625.0],
      },
      extraction_method: 'text',
      review_required: false,
    },
    {
      clause_id: 'c7',
      source_text: 'The Landlord reserves the unilateral right to amend house rules with 7 days electronic notice.',
      reviewed_text: 'The Landlord reserves the unilateral right to amend house rules with 7 days electronic notice.',
      source_ref: {
        page_number: null,
        paragraph_index: 7, // DOCX paragraph example
        bbox: null,
      },
      extraction_method: 'text',
      review_required: false,
    },
  ],
  warnings: ['Page 2 contained scanned text; OCR was applied to clause c4.'],
};

export const fixtureRentAgreementResult: ResultObject = {
  document_id: 'doc_fixture_agreement_01',
  analysis_id: 'a1_fixture_rent',
  document_revision: 1,
  input_language: 'en',
  output_language: 'en',
  document_type: 'agreement',
  coverage: {
    analysed: 7,
    total: 7,
  },
  items: [
    {
      item_id: 'i1',
      clause_id: 'c1',
      kind: 'explanation',
      category: null,
      explanation: 'States the agreement date as 1 November 2026 between landlord and tenant.',
      evidence: [
        {
          clause_id: 'c1',
          quote: 'entered into on this 1st day of November 2026.',
        },
      ],
      reference_ids: [],
      review_status: 'supported',
      detector: 'rule',
      model_score: null,
      limitations: [],
    },
    {
      item_id: 'i2',
      clause_id: 'c2',
      kind: 'explanation',
      category: null,
      explanation: 'Sets the monthly rent amount at Rs. 25,000, due by the 5th day of every month.',
      evidence: [
        {
          clause_id: 'c2',
          quote: 'monthly rent of Rs. 25,000 payable on or before the 5th of each calendar month.',
        },
      ],
      reference_ids: [],
      review_status: 'supported',
      detector: 'rule',
      model_score: null,
      limitations: [],
    },
    {
      item_id: 'i3',
      clause_id: 'c3',
      kind: 'attention',
      category: 'automatic_renewal',
      explanation: 'The lease automatically renews for an entire additional year unless you submit written cancellation notice at least 60 days before the contract ends.',
      evidence: [
        {
          clause_id: 'c3',
          quote: 'automatically renew for successive terms of 12 months unless either party provides written notice of termination at least 60 days prior',
        },
      ],
      reference_ids: [],
      review_status: 'supported',
      detector: 'model',
      model_score: 0.94,
      limitations: ['Classification model: LexGLUE unfair contract terms baseline'],
    },
    {
      item_id: 'i4',
      clause_id: 'c4',
      kind: 'attention',
      category: 'penalty',
      explanation: 'Imposes an 18% annual late penalty compounded monthly if rent payment is delayed past 10 days.',
      evidence: [
        {
          clause_id: 'c4',
          quote: 'penalty of 18% per annum compounded monthly shall be levied.',
        },
      ],
      reference_ids: [],
      review_status: 'needs_review',
      detector: 'rule',
      model_score: null,
      limitations: ['Low OCR confidence on digit values in clause c4; confirm exact penalty rate in original document.'],
    },
    {
      item_id: 'i5',
      clause_id: 'c5',
      kind: 'explanation',
      category: null,
      explanation: 'Gives the tenant a window to document pre-existing damages counting from the date keys are handed over.',
      evidence: [
        {
          clause_id: 'c5',
          quote: 'report any preexisting damages within 15 days of receipt of keys.',
        },
      ],
      reference_ids: [],
      review_status: 'supported',
      detector: 'rule',
      model_score: null,
      limitations: [],
    },
    {
      item_id: 'i6',
      clause_id: 'c6',
      kind: 'attention',
      category: 'arbitration',
      explanation: 'Restricts all legal dispute resolution to private arbitration in New Delhi and waives rights to ordinary civil court appeals.',
      evidence: [
        {
          clause_id: 'c6',
          quote: 'disputes shall be referred to sole arbitration in New Delhi, and parties waive all rights to appeal',
        },
      ],
      reference_ids: ['ref_arb_01'],
      review_status: 'supported',
      detector: 'model',
      model_score: 0.89,
      limitations: [],
    },
    {
      item_id: 'i7',
      clause_id: 'c7',
      kind: 'attention',
      category: 'unilateral_change',
      explanation: 'Allows the landlord to alter rules at will with only 7 days electronic notice.',
      evidence: [
        {
          clause_id: 'c7',
          quote: 'unilateral right to amend house rules with 7 days electronic notice.',
        },
      ],
      reference_ids: [],
      review_status: 'supported',
      detector: 'model',
      model_score: 0.92,
      limitations: ['Extracted from DOCX paragraph 7'],
    },
  ],
  deadlines: [
    {
      deadline_id: 'd1',
      clause_id: 'c2',
      source_quote: 'on or before the 5th of each calendar month.',
      display_text: '5th of each month (Rent payment)',
      anchor: 'monthly_cycle',
      resolved_date: null,
      status: 'explicit',
      missing_information: [],
    },
    {
      deadline_id: 'd2',
      clause_id: 'c3',
      source_quote: 'at least 60 days prior to the expiration.',
      display_text: '60 days before contract expiry (Renewal opt-out)',
      anchor: 'expiration',
      resolved_date: null,
      status: 'needs_information',
      missing_information: ['expiration_date'],
    },
    {
      deadline_id: 'd3',
      clause_id: 'c5',
      source_quote: 'within 15 days of receipt of keys.',
      display_text: '15 days after receipt of keys (Damage notice)',
      anchor: 'receipt_of_keys',
      resolved_date: null,
      status: 'needs_information',
      missing_information: ['receipt_date'],
    },
  ],
  warnings: [],
  legal_aid: [
    {
      title: 'NALSA - National Legal Services Authority',
      url: 'https://nalsa.gov.in/legal-aid/',
    },
  ],
  references: [
    {
      reference_id: 'ref_arb_01',
      title: 'Arbitration and Conciliation Act, 1996',
      url: 'https://www.indiacode.nic.in/handle/123456789/1978',
      section: 'Section 7',
      version: '1996',
      excerpt: 'An arbitration agreement must be in writing and signed by the parties to be enforceable under Indian law.',
    },
  ],
  provenance: {
    classifier_version: 'baseline-unfair-tos-v1',
    generator: 'qwen3-4b-instruct-q4_k_m',
    rules_version: 'v1.0.2',
  },
  __fixture: true,
};

export const fixtureFirResult: ResultObject = {
  document_id: 'doc_fixture_fir_02',
  analysis_id: 'a2_fixture_fir',
  document_revision: 1,
  input_language: 'en',
  output_language: 'en',
  document_type: 'fir',
  coverage: {
    analysed: 3,
    total: 3,
  },
  items: [
    {
      item_id: 'fir_i1',
      clause_id: 'f1',
      kind: 'allegation',
      category: null,
      explanation: 'Complainant Rajesh Kumar alleges that on 24 October 2026, unknown persons trespassed onto agricultural plot No. 42.',
      evidence: [
        {
          clause_id: 'f1',
          quote: 'complainant alleges criminal trespass onto agricultural plot No. 42 on 24-10-2026.',
        },
      ],
      reference_ids: ['ref_bns_329'],
      review_status: 'supported',
      detector: 'rule',
      model_score: null,
      limitations: ['FIR records allegations only; does not establish guilt or findings of fact.'],
    },
    {
      item_id: 'fir_i2',
      clause_id: 'f2',
      kind: 'allegation',
      category: null,
      explanation: 'Police registered complaint under section 329(3) Bharatiya Nyaya Sanhita (criminal trespass).',
      evidence: [
        {
          clause_id: 'f2',
          quote: 'Registered under Section 329(3) BNS',
        },
      ],
      reference_ids: ['ref_bns_329'],
      review_status: 'supported',
      detector: 'rule',
      model_score: null,
      limitations: [],
    },
    {
      item_id: 'fir_i3',
      clause_id: 'f3',
      kind: 'explanation',
      category: null,
      explanation: 'Investigation assigned to Sub-Inspector Sharma at Police Station Civil Lines.',
      evidence: [
        {
          clause_id: 'f3',
          quote: 'Investigation handed over to SI Sharma',
        },
      ],
      reference_ids: [],
      review_status: 'supported',
      detector: 'rule',
      model_score: null,
      limitations: [],
    },
  ],
  deadlines: [
    {
      deadline_id: 'fir_d1',
      clause_id: 'f1',
      source_quote: 'incident date: 24-10-2026',
      display_text: '24 October 2026 (Alleged Incident Date)',
      anchor: 'incident',
      resolved_date: '2026-10-24',
      status: 'explicit',
      missing_information: [],
    },
  ],
  warnings: ['FIR contains allegations under investigation; legal presumption of innocence applies.'],
  legal_aid: [
    {
      title: 'NALSA - Free Legal Defense for Accused & Victims',
      url: 'https://nalsa.gov.in/legal-aid/',
    },
  ],
  references: [
    {
      reference_id: 'ref_bns_329',
      title: 'Bharatiya Nyaya Sanhita (BNS), 2023',
      url: 'https://bprd.nic.in/page/new_criminal_laws',
      section: 'Section 329(3)',
      version: '2023',
      excerpt: 'Criminal trespass involves unlawful entry into property in possession of another with intent to commit an offence.',
    },
  ],
  provenance: {
    classifier_version: 'fir-extractor-v1',
    generator: 'qwen3-4b-instruct-q4_k_m',
    rules_version: 'v1.0.0',
  },
  __fixture: true,
};

export const fixtureNoticeResult: ResultObject = {
  document_id: 'doc_fixture_notice_03',
  analysis_id: 'a3_fixture_notice',
  document_revision: 1,
  input_language: 'en',
  output_language: 'en',
  document_type: 'notice',
  coverage: {
    analysed: 2,
    total: 2,
  },
  items: [
    {
      item_id: 'not_i1',
      clause_id: 'n1',
      kind: 'notice_action',
      category: null,
      explanation: 'The notice demands vacation of the shop premises within 15 days of notice receipt.',
      evidence: [
        {
          clause_id: 'n1',
          quote: 'you are hereby called upon to quit and vacate the said shop premises within 15 days of receipt of this notice.',
        },
      ],
      reference_ids: [],
      review_status: 'supported',
      detector: 'rule',
      model_score: null,
      limitations: ['Describes the sender\'s demand; this is not an official court eviction order.'],
    },
    {
      item_id: 'not_i2',
      clause_id: 'n2',
      kind: 'notice_action',
      category: null,
      explanation: 'Demands payment of outstanding arrears amounting to Rs. 45,000.',
      evidence: [
        {
          clause_id: 'n2',
          quote: 'clear outstanding arrears of Rs. 45,000 failing which legal proceedings shall be initiated.',
        },
      ],
      reference_ids: [],
      review_status: 'supported',
      detector: 'rule',
      model_score: null,
      limitations: [],
    },
  ],
  deadlines: [
    {
      deadline_id: 'not_d1',
      clause_id: 'n1',
      source_quote: 'within 15 days of receipt of this notice.',
      display_text: '15 days after receipt of notice (Vacation Demand)',
      anchor: 'receipt_of_notice',
      resolved_date: null,
      status: 'needs_information',
      missing_information: ['receipt_date'],
    },
  ],
  warnings: [],
  legal_aid: [
    {
      title: 'NALSA Legal Aid',
      url: 'https://nalsa.gov.in/legal-aid/',
    },
  ],
  provenance: {
    classifier_version: 'notice-extractor-v1',
    generator: 'qwen3-4b-instruct-q4_k_m',
    rules_version: 'v1.0.0',
  },
  __fixture: true,
};
