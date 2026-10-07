# Media index: what lives on Drive, not in this repository

**Uploaded on 07.10.2026 by Gev** to the Drive of the project's Google account, as part of the folder `Kryuk24 / backup_2026-10-07 / media_for_drive` ([folder](https://drive.google.com/drive/folders/1Hth6IbSR6Vf-_i_v8iiRtqgl46z2SkFq)), together with `MANIFEST.sha256.txt`. The links open only for that account. **Not verified file by file:** the Drive page shows no hashes; what was seen is the folder, its five groups and the manifest. A verified copy is also on the external disk (`docs/OPERATIONS.md`). The same Drive folder holds, by Gev's decision, the git bundle and the private materials; they are not media and are not indexed here.
After the upload each row gets the Drive file id or link, and each file is checked against the sha256 here. Drive holds no second copy of code or decisions.

## Groups

| Old path | Files | MB | What | Access | Drive link |
|---|---|---|---|---|---|
| `04_Photo/00_real_source/` | 25 | 13.7 | originals from the owner: number plates and people visible | RESTRICTED | [parent folder](https://drive.google.com/drive/folders/1jJzABXLSy1A9q5KG_GLa7mQ89-1g6UXo) |
| `04_Photo/02_stories/` | 5 | 2.2 | rendered stories | normal | [parent folder](https://drive.google.com/drive/folders/1jJzABXLSy1A9q5KG_GLa7mQ89-1g6UXo) |
| `04_Photo/03_video/` | 2 | 16.1 | promo video, two sizes | normal | [parent folder](https://drive.google.com/drive/folders/1jJzABXLSy1A9q5KG_GLa7mQ89-1g6UXo) |
| `04_Photo/04_generated_mood/` | 6 | 14.1 | generated images, mood only; input of tools/make_landing_mood.py | normal | [parent folder](https://drive.google.com/drive/folders/1jJzABXLSy1A9q5KG_GLa7mQ89-1g6UXo) |
| `04_Photo/05_hero_bg/` | 1 | 2.4 | source of the hero background | normal | [parent folder](https://drive.google.com/drive/folders/1jJzABXLSy1A9q5KG_GLa7mQ89-1g6UXo) |
| `04_Photo/06_web_unused/` | 27 | 3.4 | web-size copies not used on the site | normal | [parent folder](https://drive.google.com/drive/folders/1jJzABXLSy1A9q5KG_GLa7mQ89-1g6UXo) |
| `05_Offers_and_forms/address_video_guide/` | 2 | 5.0 | two guide videos for the address confirmation | normal | [parent folder](https://drive.google.com/drive/folders/1os93vmlWX5cfTB1FD0DnoND6_kiV4dR0) |
| `07_Mockups/navy-light/` | 63 | 9.1 | design exploration before site v32 | normal | [parent folder](https://drive.google.com/drive/folders/1BnZDpW7Z6EqYxPJdqbr8LfGMF-t6YY0F) |
| `08_Reports/` | 12 | 2.0 | the report to the owner of 05.10 and its sources | normal | in `media_for_drive/08_Reports` |
| `_ARCHIVE/01_TASKS_2026-10-02.md/` | 1 | 0.0 | archive: earlier versions, already superseded | normal | [parent folder](https://drive.google.com/drive/folders/1JbU0-nHChmTB--BbAjgo7Z-ujPAZDxjs) |
| `_ARCHIVE/brand_v1_old_hook_2026-10-03/` | 93 | 13.5 | archive: earlier versions, already superseded | normal | [parent folder](https://drive.google.com/drive/folders/1JbU0-nHChmTB--BbAjgo7Z-ujPAZDxjs) |
| `_ARCHIVE/deploy_packages/` | 3 | 0.3 | archive: earlier versions, already superseded | normal | [parent folder](https://drive.google.com/drive/folders/1JbU0-nHChmTB--BbAjgo7Z-ujPAZDxjs) |
| `_ARCHIVE/landing_backups_v1-v25/` | 76 | 2.0 | archive: earlier versions, already superseded | normal | [parent folder](https://drive.google.com/drive/folders/1JbU0-nHChmTB--BbAjgo7Z-ujPAZDxjs) |
| `_ARCHIVE/landing_v17_package_README.md/` | 1 | 0.0 | archive: earlier versions, already superseded | normal | [parent folder](https://drive.google.com/drive/folders/1JbU0-nHChmTB--BbAjgo7Z-ujPAZDxjs) |
| `_ARCHIVE/rejected_logo_concepts/` | 17 | 0.2 | archive: earlier versions, already superseded | normal | [parent folder](https://drive.google.com/drive/folders/1JbU0-nHChmTB--BbAjgo7Z-ujPAZDxjs) |
| `_ARCHIVE/unused_scripts/` | 2 | 0.0 | archive: earlier versions, already superseded | normal | [parent folder](https://drive.google.com/drive/folders/1JbU0-nHChmTB--BbAjgo7Z-ujPAZDxjs) |

Total: 336 files, 84.1 MB.

## What needs these files

- `tools/polish_real.py` reads `photo/00_real_source/` (old `04_Photo/00_real_source/`): put the originals back there to run it.
- `tools/make_landing_mood.py` reads `photo/04_generated_mood/`.
- `tools/make_story.py` and `tools/make_video.py` write into `photo/02_stories/` and `photo/03_video/`; their input `photo/01_real_polished/` is in the repository.
- The site needs none of them: everything it shows is in `site/assets/`.

## Files

The full list with sha256 is `docs/inventory/FILES.csv` (rows whose path starts with `_drive_staging/`).
