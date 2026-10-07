# План за изграждане на terminology-indexes (по итерации)

Принцип: първата итерация докарва един източник до публикуван, проверим Release и работещо сваляне от consumer-а — тънък вертикален срез, не хоризонтално разгръщане по 27 сайта наведнъж. Всяка следваща итерация добавя обхват върху вече работещ скелет.

---

Итерация 0 — Скелет на хранилището

Цел: структурата съществува, но не носи данни.

1. Инициализирай git repo terminology-indexes (public).
2. Създай директориите: sources/, builders/, indexes/, schema/, manifests/, LICENSES/, .github/workflows/.
3. Дефинирай schema/candidate.schema.json с полетата: source, candidate_id, term, normalized_term, aliases, title, url, fragment, definition_excerpt, source_version, retrieved_at, license, attribution, content_policy (metadata_only | excerpts_allowed | licensed).
4. README с едно изречение за ролята на repo-то: build dependency, не публичен сайт.
5. .gitignore: изключи всякакви *.sqlite, *.sqlite.zst.

Край на итерацията: празен, но валиден скелет, без код за парсене.

---

Итерация 1 — Един адаптер, край до край

Избери най-лесния източник за пръв опит — препоръка: Git Glossary или Python objects.inv (стабилен формат, малък обем, няма лицензионни усложнения).

1. builders/<source>.py: изтегля суровия източник, парсира go, записва indexes/<source>.jsonl (един кандидат на ред, сортиран стабилно по candidate_id).
2. Валидация на изхода срещу schema/candidate.schema.json (брой записи > 0, уникални candidate_id, валидни URL формати).
3. manifests/snapshot.json: версия на snapshot-а, списък на включените source, timestamp.
4. Ръчно изпълнение локално, преглед на резултата — без workflow все още.

Край: един JSONL файл, доказано правилен формат.

---

Итерация 2 — Build на SQLite + GitHub Actions

1. Builder скрипт, който взема всички indexes/*.jsonl (в момента 1 файл) и строи indexes.sqlite с FTS5 virtual table върху term/normalized_term/aliases/definition_excerpt.
2. Компресия: zstd → terminology-indexes-<snapshot>.sqlite.zst.
3. SHA256SUMS за всички release assets.
4. .github/workflows/update-indexes.yml:
   - ръчен workflow_dispatch тригер засега (не scheduled още — пести ненужни runs докато е нестабилно);
   - стъпки: checkout → run builder(s) → build SQLite → compress → създай GitHub Release с manifest.json + .sqlite.zst + SHA256SUMS.
5. Включи immutable releases в repo settings.

Край: push на tag → автоматичен, проверим Release asset.

---

Итерация 3 — Consumer flow в основния сайт

1. В project-site repo: indexes.lock.yaml с schema_version, snapshot, asset, sha256.
2. Workflow стъпка там: сваля asset по фиксиран tag (не latest), проверява SHA-256, разкомпресира, отваря SQLite за заявки от LLM-обогатяващия процес.
3. Тест: ръчно обнови indexes.lock.yaml към новия snapshot и провери, че workflow-ът минава.

Край: доказан пълен цикъл produce → release → consume → verify, с един източник. Това е моментът да спреш и прегледаш дали форматът/схемата се нуждаят от промяна — преди да умножиш адаптерите.

---

Итерация 4 — Разширяване с още 3–4 локални адаптера

Добави по сходен модел (всеки е отделен малък PR, не един голям commit):

1. Unicode Glossary — само term, fragment, url; content_policy: metadata_only (без definition_excerpt), заради Unicode Terms of Use.
2. NIST DADS (или директно NIST CSRC bulk JSON export, ако е по-просто).
3. PostgreSQL Glossary.
4. CNCF Glossary — CC BY 4.0, атрибуция в полето attribution.

За всеки: builder → JSONL → validation. Включи ги в update-indexes.yml build стъпката (всички builders се изпълняват последователно, резултатите се агрегират в едно SQLite).

---

Итерация 5 — Останалите адаптери, включително специалните случаи

1. RFC Editor (rfc-index.xml), WHATWG/Webref, Google ML Glossary, ECMA-262 biblio.
2. Etymonline — само sitemap → headword + canonical URL, без /api/, без определения, content_policy: metadata_only; документирай изрично в sources/etymonline.yaml забраната от robots.txt.
3. ISO — не влиза в индекса. Добави само sources/iso.yaml с enabled: false, reason, permitted_dataset: iso_open_data_metadata, за прозрачност и бъдеща референция — без действителен builder.

Край: 11 работещи адаптера + 1 документирано изключение (ISO).

---

Итерация 6 — Автоматизация, лицензи, поддръжка

1. Превключи workflow тригера от workflow_dispatch на schedule (честота според реалната нужда — напр. седмично, не ежедневно, освен за NIST, който вече има ежедневен export).
2. LICENSES/ — по един файл на източник с лиценза му; source_version/attribution полетата да се попълват автоматично от builder-а, не ръчно.
3. Добави проверка в workflow-а: ако нов snapshot има >X% спад в брой записи спрямо предходния за даден source → fail build (защита срещу счупен scraper, не срещу легитимна промяна).
4. Документирай в README таблицата от 12 изключени/условни сайта и защо не влизат (вече имаш тази преценка от проучването).
