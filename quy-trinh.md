Quy trình doc hieu Google Form Automation Tool

  Giai doan 1: Tong quan (20 phut)

  1. README.md                         -> (dang trong) nen bo sung overview + lenh chay
  2. CLAUDE.md                         -> Architecture, tech stack, workflow, rules

  Ket qua: Hieu tool lam gi va flow chinh: extract -> configure -> submit.

  ---
  Giai doan 2: App factory + routing (20 phut)

  3. app/__init__.py                   -> create_app, Babel, locale, blueprint
  4. app/main_routes.py                -> Tat ca route UI + API, flow session

  Ket qua: Hieu entry point request/response va flow UI -> backend.

  ---
  Giai doan 3: Data contracts (15 phut)

  5. app/models.py                     -> Pydantic models: Form, Page, Question...
  6. app/utils.py                      -> deterministic ID tu URL

  Ket qua: Hieu cau truc du lieu xuyen suot he thong.

  ---
  Giai doan 4: Storage layer (15 phut)

  7. app/services/storage_service.py   -> TinyDB CRUD, context manager

  Ket qua: Hieu cach luu/lay form va submission history.

  ---
  Giai doan 5: Form extraction (25 phut)

  8. app/core/form_extractor.py        -> Selenium parse data-params, multi-page

  Ket qua: Hieu cach extract cau hoi va mapping question types.

  ---
  Giai doan 6: Response generation (20 phut)

  9. app/core/form_processor.py        -> Random response, CSV/JSON mapping, edits
  10. app/core/ai_responder.py          -> Gemini AI responses (optional)

  Ket qua: Hieu logic tao cau tra loi theo type va data-driven mode.

  ---
  Giai doan 7: Submission engine (25 phut)

  11. app/core/form_submitter.py        -> Multi-thread submit, retry, status

  Ket qua: Hieu co che submit hang loat va tracking success/fail.

  ---
  Giai doan 8: Monitoring (15 phut)

  12. app/monitoring/metrics_collector.py -> Facade cho CPU/Network/Thread
  13. app/monitoring/cpu_monitor.py       -> CPU sampling
  14. app/monitoring/network_monitor.py   -> Network rates
  15. app/monitoring/thread_monitor.py    -> Thread stats

  Ket qua: Hieu he thong metrics va cach UI lay real-time data.

  ---
  Giai doan 9: Frontend flow (20 phut)

  16. app/templates/form_filling.html   -> UI 4 buoc, form config, monitor
  17. app/static/js/form_filling/main.js -> Dieu phoi workflow frontend
  18. app/static/js/form_filling/*.js   -> extract, config, submit, navigation

  Ket qua: Hieu luong thao tac tu UI den API va trang thai UI.

  ---
  Giai doan 10: Entry points + deploy (10 phut)

  19. wsgi.py                           -> entry point Flask
  20. config.py                         -> load env, Chrome paths
  21. Dockerfile, docker-compose.yml    -> Docker runtime, volume, env vars

  Ket qua: Hieu cach chay app local va container.

  ---
  Giai doan 11: CLI + Tests (15 phut)

  22. extract_form.py                   -> CLI extract doc lap
  23. tests/test_form_extractor.py      -> Integration test (can Chrome)
  24. tests/test_form_processor.py      -> Random response + file mapping
  25. tests/test_storage_service.py     -> TinyDB CRUD

  Ket qua: Hieu cach test va debug tung layer.

  ---
  Diem can doc khi muon cai tien

  - Them question type moi: form_extractor.py (_parse_question) + form_submitter.py (_fill_question)
  - Them cach nhap du lieu: form_processor.py (load_data_from_file) + main_routes.py (/load_data)
  - Them metrics/monitor: metrics_collector.py + *_monitor.py
  - Thay doi luong UI: form_filling.html + js/form_filling/*.js
  - Thay doi luu tru: storage_service.py + models.py

  ---
  📊 Tom tat theo thoi gian

  ┌───────────┬───────────┬──────────────────────────────┐
  │ Giai doan │ Thoi gian │ Focus                        │
  ├───────────┼───────────┼──────────────────────────────┤
  │ 1-3       │ 55 phut   │ Overview + Data contracts    │
  ├───────────┼───────────┼──────────────────────────────┤
  │ 4-6       │ 60 phut   │ Storage + Extract + Response │
  ├───────────┼───────────┼──────────────────────────────┤
  │ 7-8       │ 40 phut   │ Submit + Monitoring          │
  ├───────────┼───────────┼──────────────────────────────┤
  │ 9-11      │ 45 phut   │ Frontend + Deploy + Tests    │
  └───────────┴───────────┴──────────────────────────────┘

  Tong: ~3-3.5 gio de doc hieu toan bo codebase.

  ---
  🎯 Quick Path (neu chi co 1 gio)

  CLAUDE.md -> app/main_routes.py -> app/core/form_extractor.py ->
  app/core/form_submitter.py -> app/core/form_processor.py -> app/templates/form_filling.html

  Day la critical path cua workflow chinh: Extract -> Configure -> Submit.