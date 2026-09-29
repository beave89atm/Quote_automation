# Quote load QC: intake to done (SecturaFAB)

Owner: Quote Automation PO. Draft 2, Mon 9/28/2026. Checker and session guard: `e995b21` / `8b75d82`. Rule for every step: **invent=false**. A check that can't prove a value **fails closed** (FLAG, stop). It never fills in a guess. Protected quotes are never reminted or PATCHed (golds a7dc46bf/8bcc226b, a7d6ca50; PDF PASSes 1020250-1, 21684-1, 1007922-3, 29743-2, 1007471-1, 34602-2, 1007756-1, 1001898-4, 1008763-1, 1020243-1; Q10429/a24c6896; Q10435; spent leftovers).

## 0. Session check (before any action)
- **Check:** open the quote URL. If the page is `/Account/Login*`, or the title is `SecturaFAB-Login`, or any XHR returns a 302 to login, the session is **dead**. Stop all writes.
- **Recovery:** when the session is dead (`/Account/Login` or no Sectura tab), the app tries **exactly one** Incognito sign-in for that run. Chrome is on display `:2`. CDP is `127.0.0.1` and the port comes from `SECTURA_WEB_CDP_PORT` (default `9224`). If CDP is down, relaunch Chrome with `--incognito` and `--remote-debugging-port` and open `https://www.secturafab.com/Account/Login?ReturnUrl=%2FQuote`. Fill Email and Password through CDP `Runtime.evaluate` (JSON-encoded). Use `SECTURA_WEB_EMAIL` and `SECTURA_WEB_PASSWORD` when both are set. If either is missing, read `/home/box/agent-data/box-secrets.json` (`SECTURA_WEB_SECRETS_PATH` overrides that path). The keys are `card.SECTURA_WEB_EMAIL` and `card.SECTURA_WEB_PASSWORD`, either nested under `card` or as dotted top-level keys. Env values win over the file. The values never go on a command line. Check Remember Me. Click Log In once. Success is a URL on `/Quote`, not `/Account/Login`. The website password is not the API vault login. Don't read or export cookies. Don't print, log, or screenshot the email or password.
- **Fail closed:** missing credentials, a missing, unreadable, or malformed secrets file, an email-code or verification page, a login error, or a session that is still dead stops the run. The error names that page state and does not include credential values. An alert goes to Chief of Staff through the `on_alert` callback and a file under `/workspace/quote-load-qc/alerts/`. The attempt is recorded under `/workspace/quote-load-qc/locks/`. A second attempt inside `SECTURA_RELOGIN_COOLDOWN_S` (default 12 hours) is refused. This must not loop: every sign-in logs out any other AI.Agent session.
- **Watch for:** the banner "Another user has logged in with your credentials on a different system. If you login, they will be logged out." That means the AI Agent license (`[REDACTED]`) is in use somewhere else. Don't log in over it without CoS clearing it.
- **Human only:** an email code/MFA, missing vault credentials, or a license conflict goes to Chief of Staff. CoS decides whether to involve Kyle.
- **Past miss:** the session died mid-day and Finish got a 302, which left empty assembly shells.

## 1. RFQ / drawing intake
- Search the customer's emails and SharePoint **Customer Drawings** for a **STEP first**. Use the PDF only when no STEP exists.
- Read the RFQ for **quote scope**: full assembly or steel only. Record it on the job. If it's unclear, FLAG `scope_unknown`.
- If a LIST OF MATERIAL exists, clip it to `*-LOM.xlsx` from the rendered grid. PDF text regex doesn't count as takeoff.
- **Fails closed:** 0 LOM rows means `needs_info`. Never default part_count to 1. No LOM means no invented BOM.

## 2. PDF vs STEP path
- STEP present: use the CAD Files path (section 3).
- PDF only: `secturafab/chrome_cdp.py upload_pdf_via_page_add_files`, then `stamp_pdf_kendo_flats`, then `invoke_page_pdf_finish` (template `/workspace/inbox-eod/live_mint_crossdrain_image_files.py`, box CDP `SECTURA_CHROME_DEBUG=http://127.0.0.1:9231`). Tubes/bars go through Long (`/Quote/AddItem_Linear`).
- **Upload limit 32 MB.** Check file size before upload. Over the limit: FLAG (split per part or ask for a smaller file). Never let a truncated upload through.

## 3. STEP explode / assembly structure
- Split the assembly into part STEPs, but keep the parent/child structure (see section 8). Record the expected part list (name, qty) from the STEP/LOM.
- **Units:** export with `"INCH"`. **Past miss:** `"IN"` made the exporter silently write mm. **Check:** read the STEP header `SI_UNIT`/`CONVERSION_BASED_UNIT` and FLAG anything that isn't inch. Also call `SetDXFFileUnits(SourceDataID,'inch')` after upload.

## 4. ItemType to Cad, plus thickness (the proven page-native recipe, Q10488, 9/25)
All steps run via CDP `Runtime.evaluate` on the signed-in tab:
1. `upload_dxf_via_page_add_files`
2. `SetDXFFileUnits(SourceDataID,'inch')`
3. `createAllParts()`
4. Select the row, set `#DXFItemType` kendoDropDownList to `'cad'`, then `.trigger('change')`. This runs POST `/Part/UpdateItemType`, which returns the server-unfolded flat Width and ErrorStatus 0.
5. On the `#ThicknessEdit` kendoComboBox, `select()` the gauge entry, then `trigger('change')`. This runs `onThicknessChangeDXF` and GET `/Quote/GetBorderSize`, and the row gets ErrorStatus 0.
6. Verify ErrorStatus 0 and that the page is still the right quote, then call the page's `OnAddDXFClick()` (`/Quote/AddItem_DXFFiles`).

What can go wrong:
- **Row left as Component (not Cad):** thickness came from the model depth, ErrorStatus stayed 2, and the page's Finish silently skipped the row. **Check:** before Finish, every plate/sheet row on the live `#gridDXFParts` is Cad. Otherwise refuse (`producttype_still_component`).
- **Writing the thickness field directly doesn't clear ErrorStatus.** Only the combobox `change` event does. **Check:** re-read the row and require ErrorStatus 0. FLAG if it isn't.
- **Wrong quote in the tab:** check the quote ID in the URL and header before Finish.

## 5. Bends on formed parts
- **Past miss:** bends missed on AIM Crossdrain. **Check:** any part the STEP shows as formed (bend faces/flanges, or LOM "formed/brake") must have a Bend op after Finish (grid op `PRBend`). If it doesn't, FLAG. Never add a guessed bend count.
- Flat L/W must be the **server flat pattern** from UpdateItemType. **Past miss:** L/W invented from the STEP bounding box (AABB). **Check:** reject AABB-only dims and park the line.

## 6. Material
- Every line needs material (e.g. A36) and a thickness gauge from the combobox list. If either is missing, FLAG. Never default the material.

## 7. Contours, Long/Linear and renest
- Laser parts need `Contours >= 1` and non-empty InternalData. **Past miss:** Q10383/Q10460, where AddItem_DXFFiles returned empty and got Contours 0. **Check:** after Finish, re-read the tree. Contours 0 or empty InternalData means FLAG and wait/retry the Add Files. Never write Contours by hand.
- **1xN flats:** a line that comes out 1 x N (degenerate width), or a bar that went down the laser path, gets FLAGGED so it can be re-routed to Long/Linear. Renest after any change.

## 8. Weldment parent/child
- Proven recipe: the page's **Add Item**, then **Assembly** view. Name it with the parent number (e.g. `A-11949-000`), Copy All, Add. This moves the existing lines under the parent with their qty, and totals stay the same (Q10488 total $1,087.70 before and after).
- **Past miss (Kyle correction, Q10488):** the assembly was split and loose top-level lines went in with no parent. **Check:** when an assembly exists, no child line has an empty parent (`AID`).

## 9. Weld labor
- Weld minutes come from the app's weld takeoff or from Kyle, applied on the **parent**. **Check:** if the parent has no weld op, FLAG `weld_labor_pending`. Never guess minutes.

## 10. Finish / primary costs
- Use only the **page's own** Finish (`OnAddDXFClick` / `invoke_page_pdf_finish`).
- **Past miss:** the app's own Finish rewrote L/W into meters, which made a **$7.2M line on Q10488** (later deleted). That path is removed or fails closed. **Check:** every line has `U == inch` and plausible dims (0 < L <= 240 in, 0 < W <= 120 in). Unit price over the per-line sanity cap means FLAG.

## 11. Pricing
- Every line needs nonzero cost and price. No duplicate lines. The parent unit price must equal the sum of (child unit price × child qty) within $0.01, otherwise FLAG. Any zero line means FLAG.

## 12. Final pre-handoff check (per quote, read-only)
Tool: `python -m secturafab.quote_qc --quote <id> --expected <LOM/STEP list>`. It reads `/Quote/QuoteItem_ReadTreeListData?ParentID=<quote id>` and **writes nothing**.
| Check | Rule |
|---|---|
| Part count | matches the STEP/LOM (name + qty) |
| Material / thickness / cost | present and > 0 on every part |
| Bends | every formed part has a Bend op |
| Weld | weld labor on the parent, otherwise FLAG |
| Lines | no zero-price, no duplicates, no loose top-level lines when an assembly exists |
| Pricing | parent unit price = sum of (child unit price × child qty) within $0.01, otherwise FLAG |
| Dims | inch units, plausible |
| Laser | Contours >= 1; ErrorCount 0 |
| Quote header | Quote Number is the top-level part or assembly number. Description is the title-block or BOM description. FLAG when Description is blank or equals that part number, or when Quote Number does not match it |

Output (30-second read):
```
Q10488 Diamond C — FLAG
 - A-11949-000: weld labor not on parent (waiting on Kyle; not guessed)
 8 parts / 10 pcs match LOM · all inch · Contours ok · 4/4 formed have Bend · Err 0 · $1,087.70
```

## 13. Quote header (Kyle, 9/28)
When the app creates or names a Sectura quote:
- **Quote Number** is the top-level part or assembly number (for example `A-11949-000`). It is not the drawing title.
- **Description** is the title-block or BOM description passed in with the RFQ or drawing (for example `NECK WINCH BOX ASSEMBLY (CENTERED)`). It is not the part number.
- If that description is not on the input, leave Description blank. Do not invent one, and do not copy the part number into Description.
- **Check:** FLAG `quote Description blank`, `quote Description is the part number`, or `Quote Number … does not match top-level part …`. The tree read stays read-only. Line-only snapshots that omit `QuoteNumber` and `HeaderDescription` do not invent a header.

## References
`docs/sectura-api-coverage.md` (PR 18); skill `secturafab-time-weldment-quote`; artifacts `/workspace/q10488/` (p3/p4/p5 json, `p5_tree_after_assembly.json`).
