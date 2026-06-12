# Checkpoint — Sprint 2 Completed

**Date:** 2026-06-12  
**Branch:** `main`  
**Last commit:** `3f0345a` — "Sprint 2 completed"  
**Remote:** synced (`origin/main` up to date)

---

## Trạng thái máy cá nhân cần biết

Máy cá nhân dừng ở commit trước `3f0345a`. Sau khi pull về, **không cần làm gì thêm** — toàn bộ Sprint 2 đã merged vào `main` và worktree sạch.

```bash
git pull origin main
```

---

## Những gì Sprint 2 đã tạo ra (files mới trong commit `3f0345a`)

### Source code — `src/features/`

| File | Mô tả |
|---|---|
| `src/features/commit_extractor.py` | `CommitFeatureExtractor` — code churn + author history features (S2-01, S2-02) |
| `src/features/test_history_extractor.py` | `TestHistoryFeatureExtractor` — rolling failure stats per test (S2-03) |
| `src/features/dependency_extractor.py` | `DependencyFeatureExtractor` — import overlap + package coupling (S2-04) |
| `src/features/feature_joiner.py` | `FeatureJoiner` — assembles master DataFrame, writes Parquet (S2-05) |
| `src/features/validation.py` | `validate_features()` — data integrity assertions post-build (S2-07) |

### Scripts & entry point

| File | Mô tả |
|---|---|
| `scripts/data_pipeline.py` | Single-command pipeline: `--project`, `--db-path`, `--rtp-path`, `--output-path`, `--force` (S2-06) |
| `scripts/add_timestamps.py` | Timestamp resolution từ cloned repos → UPDATE `test_runs` (S2-00, tạo từ sprint trước) |

### Tests — `tests/`

| File | Cases |
|---|---|
| `tests/test_commit_extractor.py` | ≥8 cases |
| `tests/test_test_history_extractor.py` | ≥10 cases |
| `tests/test_dependency_extractor.py` | ≥6 cases |
| `tests/test_feature_joiner.py` | ≥4 integration tests |

**Kết quả:** `40 passed in 3.43s` — xem `docs/test-results-sprint2.txt`

### Artifacts đã generated (trong `.gitignore`, **không có trong repo**)

Các file sau tồn tại trên máy lab nhưng KHÔNG được commit — máy cá nhân sẽ không có:

```
data/features/neuland@jade4j_features.parquet
data/features/deeplearning4j@deeplearning4j_features.parquet
data/features/l0rdn1kk0n@wicket-bootstrap_features.parquet
data/features/adamfisk@LittleProxy_features.parquet
data/features/thinkaurelius@titan_features.parquet
data/features/full_features.parquet
data/test_history.db          (DuckDB database)
data/repos/                   (cloned git repos)
```

Để tái tạo trên máy cá nhân, cần:
1. Clone các repos: xem `README.md` phần "Project selection"
2. Load DuckDB: `python data/scripts/load_rtp_dataset.py`
3. Populate timestamps: `python scripts/add_timestamps.py`
4. Chạy pipeline cho từng project: `python scripts/data_pipeline.py --project <user>@<project> ...`

### Notebook & docs

| File | Mô tả |
|---|---|
| `notebooks/02_eda_features.ipynb` | EDA đã executed — shape, label dist, heatmap, MI ranking, scatter (S2-08) |
| `docs/decisions-log.md` | Thêm Sprint 1 retrospective + Sprint 2 decisions |
| `docs/test-results-sprint2.txt` | Output của `pytest --tb=short -q` |

---

## Definition of Done — Sprint 2 (tất cả đã pass)

- [x] `timestamp` populated ≥ 70% trên 5 projects (S2-00)
- [x] `data_pipeline.py` chạy end-to-end, ≤ 5 phút mỗi project (S2-06)
- [x] Feature matrix ≥ 20 columns, không data leakage (S2-07 validation)
- [x] `pytest tests/` → 40 passed, 0 failures (S2-09)
- [x] `02_eda_features.ipynb` executed end-to-end (S2-08)

---

## Tiếp theo — Sprint 3

Sprint 3 backlog: `docs/backlog/sprint-3-backlog.md`

Bước đầu tiên của Sprint 3 là **temporal split** (`TimeSeriesSplit` per project, split by `commit_sha` không phải row-level). Feature pipeline **đóng băng** từ Sprint 3 — không sửa extractor logic trừ khi có critical bug.

---

## Key decisions đã ghi nhận

- **RTPTorrent** thay vì `mvn test` replay (Decision 1 — 2026-05-01)
- **5 projects** với threshold ≥1% failure rate (Decision 2 — 2026-05-10):
  - `deeplearning4j@deeplearning4j` (7.76%)
  - `l0rdn1kk0n@wicket-bootstrap` (21.16%)
  - `neuland@jade4j` (19.61%)
  - `adamfisk@LittleProxy` (1.61%)
  - `thinkaurelius@titan` (1.25%)
- **`timestamp` NULL fallback** dùng `job_sequence` (Decision 3 — 2026-05-20)
- `feature_source` column là audit column — **không dùng làm model input**
