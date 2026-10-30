# Local OCR validation

Runtime: app-local Tesseract 5.5.3.20260724 with pinned tessdata_fast eng/hin/pan. Exact upstream sources/hashes: `apps/api/scripts/setup_ocr.py` and ignored `tools/ocr/manifest.json`. No document is sent to an OCR/AI/translation service.

| Synthetic check | Observed result |
|---|---|
| English image-only PDF | PAYMENT anchor recognized, real page references, OCR review required |
| Hindi image-only PDF | अनुबंध and भुगतान anchors recognized, real page references, OCR review required |
| Punjabi image-only PDF | Payment/time anchors recognized; agreement word has an incorrect extra nasalization mark |
| Mixed native/scanned PDF | Native and OCR methods retained on actual pages, one completed OCR page |
| Selectable header over scanned body | Body is OCR'd rather than hidden by the short native header |

Punjabi follow-up: 18 actual local OCR runs across two synthetic text variants, 150/200/300 DPI and page-segmentation modes 3/6/11. The agreement-word mismatch persisted in all 18. Payment/period anchors were present in all runs; the nine numeric variants retained 15 and 30/10/2026. Higher resolution did not fix the observed error, so production was not changed to consume more resources without demonstrated benefit. No invented post-correction was applied.

The exact Punjabi anchor test remains an expected failure, not a pass. Other unexpected regressions (missing payment/time anchors, parser failures, unavailable assets) still fail normally. Human review remains mandatory for every OCR clause; these short fixtures do not establish general legal extraction accuracy or multilingual translation support.

Indic fixtures use the local Windows Nirmala UI font for shaping and rasterize to image-only PDF. No font is redistributed. Reproduce the included fixtures with:

```powershell
New-Item -ItemType Directory -Path work/verification -Force | Out-Null
.\.venv-api\Scripts\python.exe -m pytest apps/api/tests/test_extraction.py -q -rx --basetemp=work/verification/ocr-check -o cache_dir=work/verification/pytest-cache
```
