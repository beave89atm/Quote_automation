"""SecturaFAB website MVC helpers — Kyle's CAD Files / Finish / Long / Nest path.

Recovered from QuoteOrderEdit JS (not in public OpenAPI). controllerName = '/Quote'.

CadImport MVC lives on the signed-in UI host (www.secturafab.com), same
cookie as Quotes. api.secturafab.com accepted Upload (200, List=1) on
live 1007756-3 but SetUnits 500, GetDXFData 404, and Next/Data 200 with
a string body the FileList parser treated as 0 rows. Prefer www; do not
treat an API 500/404 as final. CadImport stays on www — do not fall
through SetUnits/GetDXFData 500/404 to the API host (live 1002381-1
logged api after www already failed the same way).

Kyle CAD Files Next is QuoteOrderEdit createAllParts → DoCreateDXFParts
POST /part/create (form Location, IDList, unitList, OtherFileIDList,
Height, Width). success t.List is pushed onto #gridDXFParts — that is
the XHR that returns child FileList rows. ConvertTo(n) is units on
selected #gridDXF rows (IDList + Units). UpdateDXF_LoadNew is the CAD
editor next-file (ItemList + SourceID + ReturnItemID), not Kyle Next.
Live 34887-1 ConvertTo+Next JSON List 200 with FileList 0.

GetDXFData does not exist in /bundles/QuoteOrderEdit (0 hits; www 404).
#gridDXFParts is filled from DoCreateDXFParts t.List. Do not poll GetDXFData.
DoCreateDXFParts has no traditional / ajaxSetup; jQuery default is IDList[].
PartController 403+LogOnUrl (live 34639-1 / 11791-2) — kendo.antiForgeryTokens
reads hidden inputs on the Quote **layout** (GET /Quote?ID=), not the
GetItem_AddView partial. Cookie GET /Quote is 302 AccessDenied (aa86d56);
Chrome Quotes tab supplies AF and POSTs /part/create via in-page fetch.
Cookie-file HTTP POST 403s (wrong claims user, live 7b723b9). Fail closed
if chrome_dom is missing — do not POST and do not mint.
Live 34137-1: /part/create chrome_dom_fetch 200 t.List=31, then cookie-HTTP
Finish POST /Quote/AddItem_DXFFiles 200 empty str / ItemList 0.
Live 34137-2: Quotes-tab fetch Finish of reconstructed kids is the same
empty 200 — page success never bound #gridDXFParts.
Live 34632-2: page createAllParts on the Quotes list posted empty #gridDXF
IDList → t.List=0. Explode = fetch /part/create with Upload IDs; bind =
DoCreateDXFParts success onto #gridDXFParts in the CAD Files dialog
(click CAD Files in the live Quotes tab — cookie GetItem_AddView is the
wrong document, live 106386-1); then page Finish.
Do not Finish the raw STEP or a Root-only FileList.
Live 28110-2 (6c02c08): first /part/create FileList was only Root +
*ASSY* / *WELDMENT* (one-level nest). Finish 200 + GET ItemList 0.
Re-explode those nested IDs with the same DoCreateDXFParts /part/create
until leaf Cad/Linear nouns exist (plates/tubes) or no nested assembly
IDs remain. Do not Finish an assembly-only FileList; want_cad=0 is not
a license. Leave quote 75b3a938 / 28110-2. Live 107877-1 (1e76c96): pass 1
FileList 65 (Root / -28656 / GATE WELDMENT / REST WELDMENT) but
re-explode did not fire — child SourceDataID matched pass-1 used_ids
or Python rows lacked ID/FileID. Extract SourceDataID + ID + FileID;
unused child ID/FileID is the IDList. Unnamed -NNNN is a nest.
Leave e2cc0a7d / 107877-1. Live 1020249-1 (e21bc43): pass-2 IDList
of 14 job-PN kids returned List=0 and wiped #gridDXFParts 65→0.
Job-PN names are leaves after pass 1 — do not re-explode them.
Empty pass-2 keeps the prior grid (not the 34632-2 first-pass miss).
Leave e2305b3c / 1020249-1. Live 5003313-001 (526d139): job-PN leaves
held (Root + 11× 5003313-001, explode_passes=1) but Chrome was still
/Quote/EDIT/997f1eb7 — page Finish stamped 105918-1 (66→108). Minted
80eb38af GET 0. Before #but_dxf / bind / SetPartMode / Finish the tab
must be /Quote/EDIT/{minted_id} title *Quote-{PN}. Refuse leftover /
spent EDIT and leftover kendo (65 vs FileList 12). Leave 80eb38af /
5003313-001 and 997f1eb7 / 105918-1 (ItemList 108). No remint. Next
unused after the EDIT-id gate was P001545. Live P001545 (9735155):
EDIT-id gate held (105918-1 still 108). grid 53==FileList 53. Page
Finish 200 empty body / no NewItem on classified 52 kids. GET 0.
QuoteNumber landed POWER FRAME WELDMENT-1 (must be P001545). Header
landed WELDMENT, FRAME PLATE, INNER (child). Leave 31204345 / P001545.
Page Finish must invoke the 23b96a9 OnAddDXFClick fn when EDIT
matches; reconstructed FileList POST is not success. Live
BB2000-ASM (ad38881): skip-Finish after EDIT+grid 19 is a fail —
*ASM / *-ASM are nested assemblies (re-explode BB1000-ASM /
BB1010-ASM, not job-PN BB2000-ASM leaves). Leave a9497a26 /
BB2000-ASM. Live EHB3112 (83c9200): OnAddDXFClick page_fn 4==4
200 empty / GET 0 without SetPartMode notes. Leave cf8ec36e /
EHB3112-1. Live 11796-1 (4c79659): 1 Cad on EDIT, SetPartMode +
OnAddDXFClick, filelist_from_kendo=false / finish_af_present=false /
200 empty. Live 11796-2 (619ebf2): AF on the request, FileList
SourceDataID=0 / filelist_sourcedataid_n=0 / filelist_not_kendo /
200 empty. FileList must be EDIT #gridDXFParts dataSource.data()
with ID/FileID copied onto empty SourceDataID. Leave a8e1b40e /
11796-1 and 8de920f0 / 11796-2. Do not mint another unused STEP
until the kendo ID→SourceDataID fixture exists.
Live 107292-1 (ce5d2c1): checklist green (kendo+AF+SID+Cad FileType)
and Finish 200 empty / GET 0. Leave d59318c8 / 107292-1.
Live 16629-1 (76dd572 leftover EAR, aab5b3e2): CadType+Stock_X+Stock_Y
were on EDIT kendo and the posted FileList. Finish still 200 empty /
GET 0. Posted FileList and /part/create t.List lacked FileType and
Status. filelist_filetype Cad:1 was SetPartMode classify — that key
was not on the posted row. GetDXFData is not in QuoteOrderEdit (404).
OnAddDXFClick FileList is #gridDXFParts rows with ErrorStatus===0 and
Qty>0. Status>0 is Image Files GetPDFData / New Line Item, not CadImport.
105918-1 List,Result stamped 66 Component — those rows carried FileType
(page File type default Component). n=1 leftover with CadType+Stock and
no FileType is empty. SetPartMode POSTs {ID, PartMode} and paints
ItemType/Category; persist FileType onto the dataItem before
OnAddDXFClick. Do not invent Status. Leave aab5b3e2 / 16629-1.
Live 1001898-5 (491f6387 PDF-only): reconstructed FileList +
Update Item OnAddPDFClick HTTP-looked success without the
calculator. GET 8: 3 Cad unitcost filled, OperationCostList [],
no PR. Linear saw PASS is not DoD PASS. FileList must be
GetPDFData() / #gridPDF kendo rows with Status>0. Leave
491f6387. Gold look remains 1001898-1 a7dc46bf.
Kyle 2026-08-30: unpark STEP. Gold UI is CAD Files drop →
classify → Finish (OnAddDXFClick / AddItem_DXFFiles) with no
per-part #DXFEdit. Do not fire UpdateDataNext. Named analog:
type Stock_X/Stock_Y (CadImport flats) so UpdatePerimeterWeight
→ POST /Quote/GetPerimeterAndWeight fills CuttingLength /
OutsidePerimeter before OnAddDXFClick — same XHR as Image Files
L×W. Pack is on AddItem_DXFFiles List. Explode InternalData
empty is fail-closed after that stamp, not a park. Never POST
v1/quote ItemList after a gold stamp (wipe). Gold look remains
21678-1 a7d6ca50. Leave a7d6ca50 / leftover STEP empties.
Live 29743-1 (d2f7b031 SUBFRAME WELDMENT Time Waco): leftover
EDIT dump pack_xhr_named=false addrow_stamps_pr=false.
OnAddPDFClick success is only DisplaySummaryData + AddRow /
FastUpdateRow of the server List. PR + laser pack + UnitCost
must already be on AddItem_PDFFiles List (Tag, ProductionReady,
OperationCostList). QuoteOrderEdit has zero JS strings Laser /
Deburr / Sheet Loading / Laser-Setup. UpdatePerimeterWeight →
POST /Quote/GetPerimeterAndWeight fires on L×W change (not after
AddItem) and writes #OutsidePerimeter + CuttingLengthDisp.
dataItem.set L×W skipped that XHR → posted OutsidePerimeter
empty → server List Tag "" / OCL [] / UnitCost 0 / CuttingLength
0. Type L×W so UpdatePerimeterWeight runs before OnAddPDFClick.
Empty OutsidePerimeter/weight → do not Finish. Do not
AddOperation / nest / Operation→Profile. Leave d2f7b031. Gold
look remains 1001898-1 a7dc46bf.
Live 103535-1 (bd5c2e3e Q10095 GATE WELDMENT): leftover Image
Files dialog (read-only; closed; no Finish). GetItem_AddView
ItemType=pdf injects empty #gridPDF (Data:[] Total:0) plus
kendoUpload #files. jQuery("#files").kendoUpload({ success:
onSuccess_PDFUpload, complete: onComplete_PDFUpload, upload:
onUpload_PDFUpload, dropZone: ".dropZoneElement", async:
{ saveUrl: "/Attachment/UploadItem_PDFFiles", autoUpload:
true, batch: true } }). onSuccess_PDFUpload does
$("#gridPDF").data("kendoGrid").dataSource.add from
n.response.List — that is the only fill. transport.read.url
is "". GetPDFData() is not an XHR; it walks #gridPDF tbody
dataItem and keeps Status>0. Cookie HTTP POST
/Attachment/UploadItem_PDFFiles is only the widget saveUrl;
off-page cookie POST does not run onSuccess_PDFUpload →
datasource_n=0 / getpdfdata_n=0 / empty_dataSource. Kyle:
drag onto +Add Files (dropZoneElement), not Select files,
then type L×W → OnAddPDFClick. Leave bd5c2e3e / 103535-1.
Live 29340-1 (8fb3da71): GET ItemList 0. Image Files never ran.
Cookie GET /Quote/GetItem_AddView(pdf) 302 while Chrome 9224
*Quote-Q10xxx EDIT was signed in (not Login). API-mint then
cookie Finish aborted. Cookie HTTP that 302s is fail-closed —
do not mint via v1/quote then cookie Finish. In-page Chrome
mint is not gated on the cookie file. Gate is live Chrome
Quotes list footer amtech — leftover EDIT amtech is not
a mint session. Session is the page's own fetch/XHR
(HttpOnly cookies CDP Network.getCookies may omit, including
.AspNet.ApplicationCookie). Live 34603-2 was not minted
(cookie 302 after refresh) — that leftover class is 29340-1.
Login page still aborts. Do not ask Kyle to sign in. Leave
8fb3da71 / 29340-1. Do not PATCH. Do not remint.
Gold Cad pack (1001898-1 a7dc46bf first Cad 14501-1):
DataPartPDF NumberOfContours/Pierces 1/1 + BadgeString PR +
laser CalculatorNames + UnitCost>UnitWeightCost. Leftover
Cad misses that already had L×W/Weight/Machine still landed
0/0 + empty InternalData + empty pack. Missing pre-Finish
step: AddNewPDFFeature("Hole","cad") must wait for GET
/Quote/PDFInternal (not a 400ms race), then page PDFGetData()
onto InternalData. GetPDFData omits NumberOfContours/Pierces
(same as CuttingLength) — do not invent those FileList keys.
Do not cookie-POST /Quote/AddFeature. Do not invent
InternalData JSON. Pack is on AddItem_PDFFiles List[0].
Live 29341-1 (c23fba3d leftover): ProductID bound from v1/product/plate
PL1/4-A572 + AddNewPDFFeature InternalData n=1 + Weight. OnAddPDFClick
List[0] still BadgeString '' / OCL [] / UnitCost==UnitWeightCost 3.0.
QuoteOrderEdit GetPDFData copies dataItem.ProductID onto FileList
(not bag-only). HasSelectedProductID is 0 hits; ProductName is not a
GetPDFData key. Machine is copied as-is (leftovers already Laser -
Bay1). Gold GET OutsidePerimeter 0 is not the miss. Named miss:
InternalData n=1 is not gold 14501-1 NumberOfContours/Pierces 1/1.
AddNewPDFFeature writes JSON.stringify(PDFGetData()) immediately;
PDFGetData Dim1 is [data-edit='dim1'] (bundle has 0 Diameter).
GetPDFData omits NumberOfContours/Pierces. Fail-close if list0_pack
BadgeString empty after ProductID+hole. Leave c23fba3d / 29341-1.
Live 1020250-1: ProductID + Dim1 5.375 + InternalData + OP 69.5 /
Weight 17.98 + OnAddPDFClick 200 ItemList=1 still Contours=0 /
BadgeString '' / OCL [] / UnitCost==UnitWeightCost. Named miss:
UpdatePerimeterWeight posts Internal: PDFGetData() and reads
#length/#width form fields; onInternalDataChange then
UpdatePerimeterWeight(true, false). Last geometry XHR must include
filled Dim1 Internal. fc94ca9 1ca884cc: form_lw_synced=true +
OP 69.5 still Finish FileList n=0 — GetPDFData tbody Status>0
must be n≥1 before OnAddPDFClick. NumberOfContours is 0 hits
in QuoteOrderEdit — do not invent those FileList keys. Nest
is later. No graft.
Do not PATCH. Do not remint. Gold look remains 1001898-1 a7dc46bf.
Live 10098-1 (315cb19 leftover PIVOTING FOOT, 6a568912): posted FileList
had FileType=Cad (string) plus CadType/Stock_*/SID/FileID/ID/ErrorStatus/
Qty/ItemType/Category/PartMode and Cad-path keys InternalData,
InternalHTML, ImageString, HadOpenContours, OutsidePerimeter*. Finish
still 200 empty / GET 0. Unfold*/DXF*/GetDXF* child keys were absent.
FileType-on-the-row and Cad-path *keys* are not the List,Result miss.
105918-1 List,Result stamped 66 Component / 0 Cad — page File-type
default, not the Cad leftover spec. Gold Cad+PR+laser is 21678-1 /
Q10056 UI. Cited OnAddDXFClick filters ErrorStatus===0 && Qty>0 then
POSTs FileList — no emptiness check and no FileType token other than
the page/ItemType string. Persist FileType remains "Cad" from ItemType
when missing; do not guess "CAD" / 100. Named miss: Cad
AddItem_DXFFiles no-ops when InternalData/ImageString are empty.
Copy those keys through if present; log emptiness bools only; skip
Finish (fail closed) — do not invent unfold/geometry.
Bundle hunt: QuoteOrderEdit has no fill after DoCreateDXFParts
t.List. GridDXFPart_OnChangeUpdate reads InternalData/ImageString;
GET /part/PartImage is preview; GET /Quote/DXFInternal is Freestyle
only. 0 Unfold*/GetDXF*. Form keys are Location, IDList, unitList,
OtherFileIDList, Height, Width — no missing form key. Leftover n=1
Live SC0600 weldment explode n=143 still InternalData empty 143/143
(ImageString nonempty 141). Live FA Assembly 0d4b8a46 and Skin
Assembly 5b622a0d: page $.ajax on EDIT + #img H/W still empty
100%. Fetch-vs-$.ajax is not the miss. Server never fills
InternalData on explode. Keep skip. Gold 21678-1 / Q10056 GET
ItemList has no InternalData (FileList-at-Finish only). Kyle gold
Loom is CAD Files → classify → Finish with no per-part editor.
Kyle Loom c9d7c05a (Q10243 / 35145-1): blue Next → #gridDXFParts Part
Mode → green Finish. Do not Finish with PartMode still null (live
21785-2). Do not remint 35145-1 / Q10243 / 21785-1/2/3 / P904272-1 /
P904271-1 / 10289-4 / 28768-1 / 28769-1 (leftover c146ce6d) /
35136-1 (leftover 8973f890) / 14327-5 (leftover c5cd8689) /
14327-8 (leftover 1cd941c6) / Q10329 / 14327-3 / 75f07c2b /
Q10330 / 21841-1 / aed89628 / Q10331 / 14327-1 / 5e72fe39 /
Q10332 (ZZ-DEL-wrong-org-Time; ID unknown). Q10333 / H.6.38 /
b5f56ac3 Safe Cave is a Contours PASS protect (Cad / Contours=1 /
8 bends + Profile / Laser Bay1 / UC 176.96; unlock Component→Cad
then thickness inches then Contours fill) — never remint /
PATCH / ZZ-DEL. Cad-for-plate leftovers H638-CADPLATE / 5e7bfc0b
and Q10334 / e2683a3f stay forbidden (Cad classify ≠ Contours fill).
Server explode returning empty InternalData is the blocker
(step_explode_no_internaldata aliases cad_internaldata_empty_after_explode).
Optional GET /CadImport/Data + GET /CadImport/CADData after explode
may copy Contours/InternalData by SID/ID/FileID only if nonempty.
Empty GET is documentary — not a fill XHR. Do not invent Contours.
Kyle HAR leftover 35136-1 / 8973f890 (kids 35137 / 35138): Upload →
CadImport/Data OpenContourCount=0 → /part/create 3× bar InternalData
empty → AddItem_DXFFiles InternalData empty bar_flat. Contours never
filled. Confirms fail-close; does NOT unlock Contours fill.
Live 14327-5 / c5cd8689 (flat-plate STEP @ 7b59ff0): Upload →
/part/create n=1 InternalData empty 1/1, ImageString preview-only,
ProductType null → CadImport Data/CADData bindable=false,
OpenContourCount empty/null → Finish refused, invented=false,
ZZ-DEL-14327-5. Plate matches bar — no extra CadImport/UI XHR
between upload and /part/create, nor after explode. Exact missing
call: POST /part/create t.List InternalData+ImageString. Do not
silent-graft Contours. Leave 8973f890 / 35136-1, c5cd8689 /
14327-5, 1cd941c6 / 14327-8, 75f07c2b / Q10329 / 14327-3,
aed89628 / Q10330 / 21841-1, 5e72fe39 / Q10331 / 14327-1,
Q10332 is description-only
(ZZ-DEL-wrong-org-Time; quote ID not restated). Q10333 / H.6.38 /
b5f56ac3 is a Contours PASS protect (Cad / Contours=1 / 8 bends +
Profile / Laser Bay1 / UC 176.96) — never remint / PATCH / ZZ-DEL.
Cad-for-plate leftovers H638-CADPLATE / 5e7bfc0b and Q10334 /
e2683a3f stay forbidden. Do not POST UpdateDataNext / ConvertTo /
Detect* as a Finish substitute.
No live STEP t.List has yet arrived with nonempty InternalData+ImageString
(LIVE_PART_CREATE_TLIST_BIND is None). Until Kyle grabs a manual Finish
that shows Contours, persist the exact DevTools windows
(kyle_step_contours_devtools_capture) — key names / emptiness only.
UpdateDXF_LoadNew is editor-only (not gold): #DXFEdit open +
CADType==="DXF" + Previous/Next/combobox → UpdateDataNext.
Live leftover EDIT: WebGLCADDisp undefined, #DXFEdit hidden.
Do not fire UpdateDataNext. Classify→Finish without #DXFEdit
has no InternalData-fill XHR (needs_internaldata_fill_xhr).
Leave 5b622a0d / Skin Assembly,
0d4b8a46 / FA Assembly, b8a62e76 / SC0600, 6a568912 / 10098-1,
c146ce6d / 28769-1, 8973f890 / 35136-1, c5cd8689 / 14327-5,
1cd941c6 / 14327-8, 75f07c2b / Q10329 / 14327-3,
aed89628 / Q10330 / 21841-1, 5e72fe39 / Q10331 / 14327-1,
Q10332 description-only
(ZZ-DEL-wrong-org-Time; ID unknown). Q10333 / H.6.38 / b5f56ac3
is a Contours PASS protect (Cad / Contours=1 / 8 bends + Profile /
Laser Bay1 / UC 176.96) — never remint / PATCH / ZZ-DEL.
Cad-for-plate leftovers H638-CADPLATE / 5e7bfc0b and Q10334 /
e2683a3f stay forbidden. Do not remint. Do not mint.

SetUnits sends one query key `units`. Do not Finish the raw STEP row.

  GET  /Quote/GetItem_AddView?ID={quoteId}&ItemType=pdf
      injects empty #gridPDF + kendoUpload #files
  GET  /Quote/GetItem_AddView?ID={quoteId}&ItemType=dxf
  POST /Attachment/UploadItem_PDFFiles  (kendoUpload #files saveUrl only.
      onSuccess_PDFUpload is the only #gridPDF fill. Cookie HTTP
      off-page does NOT run onSuccess — live 103535-1.)
  POST /CadImport/UploadItem_DXFFiles   (STEP / DXF CAD Files only)
  POST /part/create   DoCreateDXFParts form → #gridDXFParts kids
  GET  /CadImport/Data
  GET  /CadImport/CADData   read-only after explode; copy Contours/
      InternalData by SID/ID/FileID only if nonempty. Empty is
      documentary (editor preview is not a fill).
  POST /CadImport/UpdateData, UpdateDataNext, SetPartMode, SetUnits, ConvertTo
  POST /Quote/AddItem_DXFFiles   data { ID, ItemID, customerMaterial, FileList }
  POST /Quote/AddItem_PDFFiles   urlencoded { ID, ItemID, FileList }
      FileList = GetPDFData() (#gridPDF tbody dataItem Status>0,
      not an XHR). Reconstructed FileList is fail-closed
      even if GET>0 (live 1001898-5 491f6387).
  POST /Quote/AddItem_Linear     page OnAddLinearClick / New Line Item
      after AddNewItemHTML('bar') / #but_bar → LinearProduct +
      LinearConfigList 20ft → cut length. Do NOT AddNewItemHTML('linear')
      (live 6d4373bc / d2ec4357). Cookie HTTP AddItem_Linear 302 is
      fail-closed (same leftover class as 29340-1). List[0] already
      has Saw + Saw-Setup in Primary Costs. Internal stays empty
      (no holes on Long). ItemID empty for new rows. Do not graft
      Operation→Saw.
  GET  /Product/Read_DataLinearlookup?ProductID=  (20ft/21ft productConfigID)
  GET  v1/product/plate  (Products → Sheets & Plates; live 1341 names.
      Bind FileList ProductID from local thickness+grade match.
      Gold PL7 Ga-A36. Quote-time POST /Product/ReadData_PlateConfig
      Total=3 is the wrong/filtered source — not the catalog.
      plate_sku_missing only after this full list has no ≤3/4 match.)
  POST /Quote/NestQuote_Edit
  POST /Nest/RenestLinear  (ModalLinearReNest: 20ft → 240; 40ft → 480)

FileList = #gridDXFParts rows with ErrorStatus===0 and Qty>0.
Finish writes Primary Costs (Laser/Drafting/… under PR; Saw + Saw Setup
under the linear calculator). The FileList must be the CadImport upload
grid row (SourceDataID / FileID / Stock_*). Slimming those IDs leaves
AddItem_DXFFiles / AddItem_PDFFiles with nothing to calculate. Cookie-less
addplate / addLinear fill Material/Length/UnitCost but do **not** write
OperationCostList. Do not graft those names as item-level OperationName tags.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

EMPTY_GUID = "00000000-0000-0000-0000-000000000000"
_GUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_FT_RE = re.compile(r"(?i)(\d+(?:\.\d+)?)\s*(?:'|ft|feet)\b")


def is_tenant_guid(value: Any) -> bool:
    text = str(value or "").strip()
    if not text or text == EMPTY_GUID:
        return False
    return bool(_GUID_RE.fullmatch(text))

# SetPartMode requires an integer (strings 500). Verified 0..4 HTTP 200 on empty guid.
# Mapping follows Kyle UI categories + Q10056 ProductType (100 Cad, 10/30/40 Linear, 200 Component).
# Long ProductType: 10 bar, 30 tube, 40 angle/channel. 20 (pipe) fails live GET.
# Do not force angles to 10 — QA that says "ProductType is 40, want 10" is wrong.
# Kyle Loom (original STP): after CAD Files → Geometry Cleanup → Adjust
# Properties, Sectura defaults ProductType to Component. Sheet/plate laser
# must be Cad (thickness inches, Machine Laser) or Contours/bends/profile
# stay empty. Live PASS Q10333 / b5f56ac3 / H.6.38 Safe Cave —
# ProductType Cad / Contours=1 / 8 bends + Profile / Laser Bay1 /
# UC 176.96 after Component→Cad then thickness inches then Contours
# fill. Protect forever; never remint / PATCH / ZZ-DEL.
# Automation writes the
# API/kendo ProductType field (100) + FileType/ItemType/Category=Cad +
# SetPartMode 0 — not a UI dropdown click. Cad classify ≠ Contours fill
# (live H638-CADPLATE / 5e7bfc0b SetPartMode Cad:1 InternalData empty;
# Q10334 / e2683a3f kendo Cad/100 + 0.1875 in + Laser-Bay1 Contours
# empty). Do not invent Contours; refuse Finish if InternalData still
# empty after Cad classify. Next: DevTools of Kyle's real dropdown click.
PART_MODE_CAD = 0
PART_MODE_LINEAR = 1
PART_MODE_COMPONENT = 2
LINEAR_PRODUCT_TYPE_BAR = 10
LINEAR_PRODUCT_TYPE_TUBE = 30
LINEAR_PRODUCT_TYPE_ANGLE = 40
VALID_LINEAR_PRODUCT_TYPES = frozenset(
    {
        LINEAR_PRODUCT_TYPE_BAR,
        LINEAR_PRODUCT_TYPE_TUBE,
        LINEAR_PRODUCT_TYPE_ANGLE,
    }
)

PART_MODE_BY_CATEGORY = {
    "Cad": PART_MODE_CAD,
    "Linear": PART_MODE_LINEAR,
    "Component": PART_MODE_COMPONENT,
}

WEBSITE_FINISH_PATHS = {
    "get_item_add_view": "/Quote/GetItem_AddView",
    "upload_pdf_attachment": "/Attachment/UploadItem_PDFFiles",
    "linear_lookup": "/Product/Read_DataLinearlookup",
    "plate_config": "/Product/ReadData_PlateConfig",
    "upload_dxf": "/CadImport/UploadItem_DXFFiles",
    "cadimport_data": "/CadImport/Data",
    "cadimport_caddata": "/CadImport/CADData",
    "cadimport_update_data": "/CadImport/UpdateData",
    "cadimport_update_data_next": "/CadImport/UpdateDataNext",
    "cadimport_set_part_mode": "/CadImport/SetPartMode",
    "cadimport_set_units": "/CadImport/SetUnits",
    "cadimport_convert_to": "/CadImport/ConvertTo",
    "part_create": "/part/create",
    "cadimport_get_dxf_data": "/CadImport/GetDXFData",
    "quote_get_dxf_data": "/Quote/GetDXFData",
    "add_item_dxf_files": "/Quote/AddItem_DXFFiles",
    "add_item_pdf_files": "/Quote/AddItem_PDFFiles",
    "get_perimeter_and_weight": "/Quote/GetPerimeterAndWeight",
    "add_item_linear": "/Quote/AddItem_Linear",
    "add_operation": "/Quote/AddOperation",
    "copy_move_to_assembly": "/Quote/CopyMoveItemToAssembly",
    "add_feature": "/Quote/AddFeature",
    "quote_item_read": "/Quote/QuoteItem_Read",
    "nest_quote_edit": "/Quote/NestQuote_Edit",
    "renest_linear": "/Nest/RenestLinear",
}

# ModalLinearReNest: check 40ft → Nest SheetSizeLength 480; check 20ft → 240.
LINEAR_RENEST_20FT_IN = 240.0
LINEAR_RENEST_40FT_IN = 480.0
_NEST_STOCK_LEN_KEYS = ("SheetSizeLength", "StockLength", "SheetLength")
_NEST_STOCK_HINT_KEYS = frozenset(
    {
        "SheetSizeLength",
        "SheetSizeWidth",
        "StockLength",
        "StockID",
        "SheetLength",
        "SheetWidth",
        "StockWidth",
    }
)


def _nest_stock_length_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return number


def collect_nest_stock_lengths(payload: Any) -> list[float]:
    """SheetSizeLength / StockLength from nest GET or quote StockList."""
    found: list[float] = []
    seen: set[int] = set()

    def walk(obj: Any, *, stock_ctx: bool) -> None:
        if isinstance(obj, dict):
            marker = id(obj)
            if marker in seen:
                return
            seen.add(marker)
            keys = set(obj)
            here_stock = stock_ctx or bool(keys & _NEST_STOCK_HINT_KEYS)
            for key in _NEST_STOCK_LEN_KEYS:
                number = _nest_stock_length_float(obj.get(key))
                if number is not None:
                    found.append(number)
            if here_stock:
                number = _nest_stock_length_float(obj.get("Length"))
                if number is not None:
                    found.append(number)
            for key, val in obj.items():
                child_stock = here_stock or str(key) in {
                    "StockList",
                    "Stocks",
                    "NestStock",
                }
                walk(val, stock_ctx=child_stock)
            return
        if isinstance(obj, list):
            for item in obj:
                walk(item, stock_ctx=stock_ctx)

    walk(payload, stock_ctx=False)
    return found


def nest_has_480_stock(payload: Any) -> bool:
    """True when nest/quote stock is the 40ft (480) ModalLinearReNest size."""
    return any(
        abs(number - LINEAR_RENEST_40FT_IN) < 0.5
        for number in collect_nest_stock_lengths(payload)
    )


def nest_task_ids(payload: Any) -> list[str]:
    """Nest task GUIDs from v1/Nest Results/Data."""
    rows: list[Any] = []
    if isinstance(payload, dict):
        raw = payload.get("Results") or payload.get("Data") or payload.get("List")
        if isinstance(raw, list):
            rows = raw
        elif is_tenant_guid(payload.get("ID")):
            rows = [payload]
    elif isinstance(payload, list):
        rows = payload
    ids: list[str] = []
    for task in rows:
        if not isinstance(task, dict):
            continue
        for key in ("ID", "NestID", "TaskID", "NestTaskID"):
            val = task.get(key)
            if is_tenant_guid(val):
                ids.append(str(val))
                break
    return ids


def build_renest_linear_payload(
    quote_id: str,
    *,
    nest_id: str | None = None,
) -> dict[str, Any]:
    """ModalLinearReNest submit: 20ft checked → Nest 240; 40ft unchecked."""
    target = str(nest_id or quote_id or "").strip() or str(quote_id)
    return {
        "QuoteID": quote_id,
        "ID": target,
        "Length20": True,
        "Length40": False,
        "SheetSizeLength": int(LINEAR_RENEST_20FT_IN),
        "StockLength": int(LINEAR_RENEST_20FT_IN),
    }


# Q10056 Weld calculator shape (website AddOperation, not grafted Laser).
WELD_CALC_PARAM_TYPE = "weld|perunittime|perunittime|fixedtime|perunitcost"
WELD_OPERATION_CODE = "op_weld"
WELD_EQUIPMENT = "Welding"
WELD_APPLY_TO = "ITEM"

WELD_ADD_FIELDS = (
    "ID",
    "ItemID",
    "operation_code",
    "Equipment",
    "ApplyTo",
    "CalcParamType",
    "weld",
    "perunittime",
    "perunittime2",
    "fixedtime",
    "perunitcost",
)

COPY_MOVE_FIELDS = (
    "ID",
    "ItemID",
    "AssemblyID",
    "Mode",
)

ADD_FEATURE_FIELDS = (
    "ID",
    "ItemID",
    "FeatureType",
    "Diameter",
    "Qty",
)

WEBSITE_SESSION_EXPIRED = "website session expired"

WEBSITE_AUTH_GAP = (
    "Finish needs SECTURA_WEBSITE_COOKIE (env or file) from the signed-in "
    "www.secturafab.com Chrome on this Linux box. "
    "Do not paste a cookie. Do not unwrap Windows Chrome. "
    "Do not use Kyle's quoting PC. "
    "GET /Quote/GetItem_AddView and POST /Quote/AddItem_DXFFiles, "
    "AddItem_PDFFiles, and AddItem_Linear 302 to /Account/Login or hit "
    "Cloudflare without that session (website session expired). "
    "Do not fall back to quickAddCAD. "
    "Do not graft Laser/Drafting/Saw Setup as item tags."
)

# Identity keys CadImport/UploadItem_DXFFiles returns. Finish needs these
# to attach DataPart and run the Profile / Saw calculators. Do not drop.
CADIMPORT_IDENTITY_FIELDS = (
    "SourceDataID",
    "FileID",
    "CadType",
    "FileType",
    "PartCount",
    "OpenContourCount",
    "Stock_X",
    "Stock_Y",
    "Stock_Z",
    "Stock_Units",
    "Stock_Length",
    "Stock_Diameter",
    "PartID",
    "ParentName",
    "Error",
)

# Field bag the JS copies from #gridDXFParts into FileList.
FILELIST_FIELDS = (
    "ErrorStatus",
    "Qty",
    "Quantity",
    "Machine",
    "Material",
    "MaterialGrade",
    "Thickness",
    "Thickness_Units",
    "ProductID",
    "SKU",
    "Name",
    "PartName",
    "FileName",
    "Description",
    "PartMode",
    "IsLinear",
    "IsPlate",
    "IsPart",
    "ItemType",
    "Category",
    "Length",
    "Width",
    "LinearLength",
    "LinearWidth",
    "LinearHeight",
    "Dim1",
    "Dim2",
    "Dim3",
    "Dim4",
    "Dim1_Units",
    "Dim2_Units",
    "Dim3_Units",
    "Dim4_Units",
    "ID",
    "ItemID",
    "Units",
    *CADIMPORT_IDENTITY_FIELDS,
)

# Posted FileList row key names to log (not values). Live 107292-1 vs 105918-1.
FINISH_FILELIST_COMPARE_KEYS = (
    "Status",
    "Thickness",
    "Material",
    "Width",
    "Length",
    "CadType",
    "FileType",
    "SourceDataID",
    "FileID",
    "Stock_X",
    "Stock_Y",
)
# CadImport identity (DoCreateDXFParts t.List). Live 16629-1: these were
# on kendo and the posted FileList — empty body was FileType missing.
CADIMPORT_FINISH_IDENTITY_KEYS = (
    "CadType",
    "Stock_X",
    "Stock_Y",
)
# Copy through from kendo / t.List — never invent values.
# Live 10098-1: InternalData/ImageString keys were on the posted FileList
# (emptiness unknown on 315cb19). Copy if present. Do not invent unfold.
CADIMPORT_KEEP_KEYS = (
    "CadType",
    "Stock_X",
    "Stock_Y",
    "Stock_Z",
    "Stock_Units",
    "Stock_Length",
    "Stock_Diameter",
    "FileType",
    "SourceDataID",
    "FileID",
    "ID",
    "InternalData",
    "InternalHTML",
    "ImageString",
    "HadOpenContours",
    "OutsidePerimeter",
    "OutsidePerimeter_Units",
    "OutsidePerimeter_UseLocal",
)
KENDO_IDENTITY_LOG_KEYS = CADIMPORT_KEEP_KEYS


def filelist_posted_row_keys(row: dict[str, Any] | None) -> list[str]:
    """Sorted FileList row key names — never token/cookie/AF values."""
    if not isinstance(row, dict):
        return []
    return sorted(str(k) for k in row if str(k) != "uid")


def filelist_missing_compare_keys(keys: list[str] | None) -> list[str]:
    have = {str(k) for k in (keys or [])}
    return [k for k in FINISH_FILELIST_COMPARE_KEYS if k not in have]


def filelist_missing_cadimport_identity_keys(keys: list[str] | None) -> list[str]:
    have = {str(k) for k in (keys or [])}
    return [k for k in CADIMPORT_FINISH_IDENTITY_KEYS if k not in have]


def kendo_identity_log_keys(row: dict[str, Any] | None) -> list[str]:
    """CadType/Stock_*/FileType/SID/FileID/ID names present on a kendo row."""
    if not isinstance(row, dict):
        return []
    named = [k for k in KENDO_IDENTITY_LOG_KEYS if k in row]
    extra = sorted(
        str(k)
        for k in row
        if str(k).startswith("Stock_") and str(k) not in named
    )
    return named + extra


def copy_cadimport_identity_through(
    src: dict[str, Any] | None,
    dest: dict[str, Any] | None,
) -> dict[str, Any]:
    """Copy CadType/Stock_* from src onto dest when dest dropped them.

    Do not invent Stock_X/Y or CadType. Only copy keys that exist on src.
    """
    out = dict(dest) if isinstance(dest, dict) else {}
    if not isinstance(src, dict):
        return out
    keep = list(CADIMPORT_KEEP_KEYS)
    keep.extend(
        str(k)
        for k in src
        if str(k).startswith("Stock_") and str(k) not in keep
    )
    for key in keep:
        if key in src and key not in out:
            out[key] = src[key]
    return out


def kendo_lacks_cadimport_identity(rows: list[dict[str, Any]] | None) -> list[str]:
    """Missing CadType/Stock_X/Stock_Y on EDIT kendo after explode — bind miss."""
    kids = [r for r in (rows or []) if isinstance(r, dict)]
    if not kids:
        return list(CADIMPORT_FINISH_IDENTITY_KEYS)
    return filelist_missing_cadimport_identity_keys(kendo_identity_log_keys(kids[0]))


class SecturaFabWebsiteAuthError(RuntimeError):
    """MVC Finish / Quote dialog requires a website session cookie."""

    def __init__(
        self,
        message: str = WEBSITE_AUTH_GAP,
        *,
        status_code: int | None = None,
        body: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body


def _qty_of(row: dict[str, Any]) -> float:
    for key in ("Qty", "Quantity", "qty"):
        if key in row and row.get(key) is not None:
            try:
                return float(row.get(key) or 0)
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def _error_status(row: dict[str, Any]) -> int:
    raw = row.get("ErrorStatus", row.get("errorStatus", 0))
    try:
        return int(raw or 0)
    except (TypeError, ValueError):
        return 0


def filter_finish_filelist(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """JS: #gridDXFParts rows with ErrorStatus===0 and Qty>0."""
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if _error_status(row) != 0:
            continue
        if _qty_of(row) <= 0:
            continue
        out.append(dict(row))
    return out


def is_cadimport_root_row(row: dict[str, Any] | None) -> bool:
    """Synthetic CadImport 'Root' node — not a Finish kid."""
    if not isinstance(row, dict):
        return False
    name = str(
        row.get("Name") or row.get("PartName") or row.get("Description") or ""
    ).strip()
    return name.casefold() == "root"


def finish_filelist_kids(
    rows: list[dict[str, Any]] | None,
    *,
    part_key: str = "",
    cad_filename: str = "",
) -> list[dict[str, Any]]:
    """Exploded kids for AddItem_DXFFiles — not raw STEP, not Root-only."""
    out: list[dict[str, Any]] = []
    for row in filter_finish_filelist(rows):
        if is_cadimport_root_row(row):
            continue
        if is_raw_step_upload_row(
            row, part_key=part_key, cad_filename=cad_filename
        ):
            continue
        out.append(row)
    return out


def slim_filelist_row(row: dict[str, Any]) -> dict[str, Any]:
    """Keep the CadImport / #gridDXFParts row. JS Finish posts the whole row."""
    slim: dict[str, Any] = dict(row)
    if "Qty" not in slim and "Quantity" in slim:
        slim["Qty"] = slim["Quantity"]
    if "Quantity" not in slim and "Qty" in slim:
        slim["Quantity"] = slim["Qty"]
    return slim


_CADIMPORT_ROW_KEYS = (
    "List",
    "FileList",
    "Data",
    "data",
    "Result",
    "Items",
    "rows",
    "d",
)

# #gridDXFParts / Next JSON embedded in an HTML dialog or Kendo init.
_FILELIST_JSON_RE = re.compile(
    r'"(?:FileList|List)"\s*:\s*(\[(?:[^[\]]|\[[^[\]]*\])*\])',
    re.DOTALL,
)
_SOURCEDATA_OBJ_RE = re.compile(
    r'\{[^{}]*"SourceDataID"\s*:\s*"(?:[^"\\]|\\.)+"[^{}]*\}',
)


def cadimport_payload_preview(payload: Any, *, limit: int = 160) -> str:
    """Short type/len note for explode logs. Never include cookies."""
    if payload is None:
        return "null"
    if isinstance(payload, dict):
        keys = ",".join(list(payload)[:8])
        return f"dict keys={keys!r} n={len(payload)}"
    if isinstance(payload, list):
        return f"list len={len(payload)}"
    text = str(payload).replace("\r", " ").replace("\n", " ").strip()
    return f"string {text[:limit]!r}"


def _filelist_rows_from_html(text: str) -> list[dict[str, Any]]:
    """Pull #gridDXFParts / FileList rows out of an HTML or JS-string body."""
    if not text:
        return []
    blob = text
    if "SourceDataID" not in blob and "FileList" not in blob and "gridDXFParts" not in blob:
        return []
    for match in _FILELIST_JSON_RE.finditer(blob):
        try:
            rows = json.loads(match.group(1))
        except ValueError:
            continue
        if isinstance(rows, list) and any(isinstance(r, dict) for r in rows):
            return [dict(r) for r in rows if isinstance(r, dict)]
    objs: list[dict[str, Any]] = []
    for match in _SOURCEDATA_OBJ_RE.finditer(blob):
        try:
            obj = json.loads(match.group(0))
        except ValueError:
            continue
        if isinstance(obj, dict) and obj.get("SourceDataID") not in (None, ""):
            objs.append(obj)
    return objs


def _coerce_cadimport_payload(payload: Any) -> Any:
    """Unwrap JSON-as-string / nested Data strings from Next and CadImport/Data."""
    cur: Any = payload
    for _ in range(5):
        if isinstance(cur, (bytes, bytearray)):
            cur = cur.decode("utf-8", errors="replace")
            continue
        if isinstance(cur, str):
            text = cur.strip()
            if not text:
                return cur
            try:
                cur = json.loads(text)
                continue
            except ValueError:
                html_rows = _filelist_rows_from_html(text)
                return html_rows if html_rows else cur
        if isinstance(cur, dict):
            for key in ("d", "Data", "data", "Result"):
                val = cur.get(key)
                if isinstance(val, str) and val.strip()[:1] in "{[":
                    try:
                        cur = json.loads(val)
                        break
                    except ValueError:
                        continue
            else:
                return cur
            continue
        return cur
    return cur


def _rows_from_cadimport_container(rows: Any) -> list[dict[str, Any]] | None:
    if isinstance(rows, str):
        try:
            rows = json.loads(rows)
        except ValueError:
            extracted = _filelist_rows_from_html(rows)
            return extracted or None
    if isinstance(rows, dict):
        for inner in _CADIMPORT_ROW_KEYS:
            val = rows.get(inner)
            if isinstance(val, list):
                rows = val
                break
        else:
            return None
    if isinstance(rows, list) and any(isinstance(r, dict) for r in rows):
        return [dict(r) for r in rows if isinstance(r, dict)]
    return None


def filelist_from_cadimport_upload(payload: Any) -> list[dict[str, Any]]:
    """Rows from CadImport Upload / Next / Data / GetDXFData / GetItem_AddView.

    Live Next/Data on the API host returned HTTP 200 with a *string* body
    (HTML dialog, JSON-as-string, or Kendo init). Unwrap those so FileList
    kids are visible; a dict/list with List/FileList/Data still wins.
    """
    payload = _coerce_cadimport_payload(payload)
    if isinstance(payload, list):
        return [dict(r) for r in payload if isinstance(r, dict)]
    if isinstance(payload, str):
        return _filelist_rows_from_html(payload)
    if not isinstance(payload, dict):
        return []
    for key in _CADIMPORT_ROW_KEYS:
        found = _rows_from_cadimport_container(payload.get(key))
        if found:
            return found
    return _filelist_rows_from_html(json.dumps(payload)) if payload else []


_INPUT_TAG_RE = re.compile(r"<input\b[^>]*>", re.I | re.S)
_META_TAG_RE = re.compile(r"<meta\b[^>]*>", re.I | re.S)
_INPUT_ATTR_RE = re.compile(
    r"""([^\s=]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""",
    re.I,
)
# kendo.core antiForgeryTokens (2023.3): e("input[name^='__RequestVerificationToken']")
# plus meta csrf-token/_csrf with csrf-param/_csrf_header as the data key.
# Does not set RequestVerificationToken header — merges into $.ajax data.
_JSON_AF_RE = re.compile(
    r"""['"](__RequestVerificationToken[^'"]*|afToken)['"]\s*[:=]\s*['"]([^'"]+)['"]""",
    re.I,
)
_AF_FORM_KEYS = frozenset(
    {
        "__RequestVerificationToken",
        "afToken",
        "csrf-token",
    }
)
_CSRF_TOKEN_META = frozenset({"csrf-token", "_csrf"})
_CSRF_PARAM_META = frozenset({"csrf-param", "_csrf_header"})


def _decode_markup_blob(text: str) -> str:
    """Unescape JSON/HTML wrappers so layout inputs are visible."""
    import html as html_lib

    blob = str(text or "")
    blob = (
        blob.replace("\\u0022", '"')
        .replace("\\u003c", "<")
        .replace("\\u003e", ">")
        .replace("\\\"", '"')
        .replace("\\'", "'")
    )
    return html_lib.unescape(blob)


def _tag_attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in _INPUT_ATTR_RE.finditer(tag):
        key = (match.group(1) or "").strip()
        val = match.group(2) or match.group(3) or match.group(4) or ""
        if key:
            attrs[key.lower()] = val
    return attrs


def _is_af_input_name(name: str) -> bool:
    n = str(name or "").strip()
    return n.startswith("__RequestVerificationToken") or n in _AF_FORM_KEYS


def form_has_antiforgery(form: list[tuple[str, str]] | None) -> bool:
    """True when form keys include an AF field with a value. Never log values."""
    for key, value in form or []:
        if _is_af_input_name(str(key)) and str(value or "").strip():
            return True
    return False


def client_antiforgery_extracted(client: Any) -> bool:
    """True when scraped AF fields/token are real strings (not MagicMock)."""
    fields = getattr(client, "_request_verification_fields", None)
    if isinstance(fields, (list, tuple)):
        for item in fields:
            if (
                isinstance(item, (list, tuple))
                and len(item) >= 2
                and _is_af_input_name(str(item[0]))
                and str(item[1] or "").strip()
            ):
                return True
    token = getattr(client, "_request_verification_token", None)
    return isinstance(token, str) and bool(token.strip())


_INVENTORY_LOCATION_RE = re.compile(
    r'id=["\']InventoryLocation["\'][^>]*value=["\']([^"\']*)["\']'
    r'|value=["\']([^"\']*)["\'][^>]*id=["\']InventoryLocation["\']',
    re.I,
)


def inventory_location_from_html(html: Any) -> str:
    """#InventoryLocation from GetItem_AddView — DoCreateDXFParts Location."""
    text = html if isinstance(html, str) else ""
    if not text:
        return ""
    match = _INVENTORY_LOCATION_RE.search(text)
    if not match:
        return ""
    return (match.group(1) or match.group(2) or "").strip()


def request_verification_fields(html: Any) -> list[tuple[str, str]]:
    """kendo.antiForgeryTokens() — same selectors, Quote layout not AddView.

    Cited from kendo.core.js 2023.3 (``s.antiForgeryTokens``):
    ``e("input[name^='__RequestVerificationToken']")`` plus
    ``meta[name=csrf-token],meta[name=_csrf]`` with
    ``meta[name=csrf-param],meta[name=_csrf_header]`` as the data key.
    Returns an object callers merge into $.ajax ``data`` — does **not**
    set a ``RequestVerificationToken`` header.

    Lives on GET ``/Quote?ID=`` (full page). GetItem_AddView is a partial
    (live 11791-2 AddView ~123k / af_extracted=false). Never log values.
    """
    if isinstance(html, dict):
        text = str(html.get("View") or html.get("view") or "")
        try:
            text = text + json.dumps(html)
        except TypeError:
            text = text + str(html)
    else:
        text = html if isinstance(html, str) else ""
    text = _decode_markup_blob(text)
    if not text:
        return []
    out: list[tuple[str, str]] = []
    seen: set[str] = set()

    def _add(name: str, value: str, *, allow_any: bool = False) -> None:
        name = str(name or "").strip()
        value = str(value or "").strip()
        if not name or not value or name in seen:
            return
        if not allow_any and not _is_af_input_name(name):
            return
        seen.add(name)
        out.append((name, value))

    for tag in _INPUT_TAG_RE.findall(text):
        attrs = _tag_attrs(tag)
        _add(attrs.get("name") or "", attrs.get("value") or "")

    csrf_token = ""
    csrf_param = ""
    for tag in _META_TAG_RE.findall(text):
        attrs = _tag_attrs(tag)
        meta_name = (attrs.get("name") or "").strip().lower()
        content = (attrs.get("content") or "").strip()
        if meta_name in _CSRF_TOKEN_META and content:
            csrf_token = content
        elif meta_name in _CSRF_PARAM_META and content:
            csrf_param = content
    if csrf_token:
        # kendo: tokens[csrf-param || csrf-header] = csrf-token content
        _add(csrf_param or "csrf-token", csrf_token, allow_any=True)

    if not out:
        for name, value in _JSON_AF_RE.findall(text):
            _add(name, value)
    return out


def request_verification_token(html: Any) -> str | None:
    """First AF field value — Quote layout or AddView. Never log it."""
    fields = request_verification_fields(html)
    if not fields:
        return None
    return fields[0][1]


def normalize_cadimport_list(value: Any) -> list[dict[str, Any]]:
    """Coerce List / ListOther to a list of row dicts.

    Live 1002381-1 request preview had List as Python ``str(rows)``
    (single quotes) and ListOther as ``\"[]\"``. That is not a JSON array
    and UpdateDataNext 200s with an empty body (no explode).
    """
    if value is None:
        return []
    if isinstance(value, list):
        return [dict(r) for r in value if isinstance(r, dict)]
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        text = value.strip()
        if not text or text in {"[]", "null", "None"}:
            return []
        parsed: Any
        try:
            parsed = json.loads(text)
        except ValueError:
            try:
                parsed = ast.literal_eval(text)
            except (ValueError, SyntaxError):
                return []
        if parsed is value:
            return []
        return normalize_cadimport_list(parsed)
    if isinstance(value, dict):
        for key in _CADIMPORT_ROW_KEYS:
            found = value.get(key)
            if found is not None and found is not value:
                rows = normalize_cadimport_list(found)
                if rows:
                    return rows
        if any(k in value for k in ("SourceDataID", "FileID", "FileName", "Name")):
            return [dict(value)]
    return []


def build_cadimport_next_payload(
    quote_id: str,
    rows: Any,
    *,
    list_other: Any = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Green Next / ConvertTo JSON: List is a native array, not dumps-text."""
    body: dict[str, Any] = {
        "ID": quote_id,
        "List": normalize_cadimport_list(rows),
        "ListOther": normalize_cadimport_list(list_other),
        "status": "OK",
    }
    if isinstance(extra, dict):
        status = extra.get("status") or extra.get("Status")
        if status not in (None, ""):
            body["status"] = status
        for key, val in extra.items():
            if key in body or key in {"List", "ListOther", "list_type", "Status"}:
                continue
            if isinstance(val, (list, dict)):
                continue
            if val is not None:
                body[key] = val
    return body


def cadimport_list_is_native_array(payload: Any) -> bool:
    """True when List is a list of dicts (live capture list_type must not be str)."""
    if not isinstance(payload, dict):
        return False
    rows = payload.get("List")
    return isinstance(rows, list) and all(isinstance(r, dict) for r in rows)


def cadimport_next_form(
    payload: dict[str, Any],
    *,
    token: str | None = None,
) -> list[tuple[str, str]]:
    """Do not use for Next. Live 34574-1: form List=dumps(rows) is still a string."""
    del payload, token
    raise RuntimeError(
        "CadImport Next/ConvertTo must POST json List as a native array; "
        "form List=json.dumps(rows) is list_type=str and does not explode"
    )


def _step_like_name(text: str | None) -> bool:
    raw = str(text or "").strip().lower()
    return raw.endswith(".step") or raw.endswith(".stp")


def is_raw_step_upload_row(
    row: dict[str, Any] | None,
    *,
    part_key: str = "",
    cad_filename: str = "",
) -> bool:
    """True when the row is the STEP file itself, not an exploded child PN.

    The job ``cad_filename`` is only a compare target. Do not treat every
    kid as raw just because the upload was a STEP (live 34137-1 t.List).
    """
    if not isinstance(row, dict):
        return False
    from .item_desc import normalize_part_token

    file_name = str(row.get("FileName") or "")
    name = str(
        row.get("Name") or row.get("Description") or row.get("PartName") or ""
    )
    stem = Path(cad_filename or file_name or name).stem
    name_tok = normalize_part_token(name)
    file_stem_tok = normalize_part_token(Path(file_name).stem) if file_name else ""
    stem_tok = normalize_part_token(stem)
    pk_tok = normalize_part_token(part_key)
    file_is_job_step = _step_like_name(file_name) and (
        file_stem_tok in {stem_tok, pk_tok}
        or (
            bool(cad_filename)
            and file_name.casefold() == str(cad_filename).casefold()
        )
    )
    own_step = file_is_job_step or _step_like_name(name)
    try:
        part_count = int(row.get("PartCount") or 0)
    except (TypeError, ValueError):
        part_count = 0
    if _step_like_name(name):
        return True
    if own_step and name_tok in {"", stem_tok, pk_tok}:
        return True
    if own_step and part_count > 1 and name_tok in {"", stem_tok, pk_tok}:
        return True
    return False


def empty_griddxf_explode_miss(
    *,
    grid_present: bool | None = None,
    n_grid: int | None = None,
    n_list: int | None = None,
) -> bool:
    """34632-2: Quotes-list empty ``#gridDXF`` / List=0 — not a 1-row Cad.

    Live 11796-1: single-plate STEP explodes to List=1 / EDIT Cad=1.
    That is Finishable. Abort only when the grid is missing or empty.
    """
    if grid_present is False:
        return True

    def _as_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    grd = _as_int(n_grid)
    lst = _as_int(n_list)
    if grd is not None:
        return grd <= 0
    if lst is not None:
        return lst <= 0
    return False


def sourcedataid_empty(value: Any) -> bool:
    """True when SourceDataID/ID/FileID is missing — including 0 (live 11796-2)."""
    if value is None:
        return True
    text = str(value).strip()
    return text in {"", "0"}


def fill_kendo_filelist_sourcedataid(
    rows: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Copy ID or FileID onto empty SourceDataID (105918-1 kendo rows)."""
    filled: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        copy = dict(row)
        if sourcedataid_empty(copy.get("SourceDataID")):
            for key in ("ID", "FileID"):
                val = copy.get(key)
                if not sourcedataid_empty(val):
                    copy["SourceDataID"] = val
                    break
        filled.append(copy)
    return filled


SETPARTMODE_FILETYPES = ("Cad", "Linear", "Assembly", "Component")


def persist_setpartmode_filetype(row: dict[str, Any] | None) -> dict[str, Any]:
    """Write FileType from SetPartMode ItemType/Category/PartMode.

    Live 16629-1: SetPartMode painted a badge (Cad:1 classify) but FileType
    was not on the posted FileList. Live 10098-1 posted FileType=Cad (str)
    and Finish was still empty — do not guess CAD / 100. Keep a page
    FileType if present. Do not invent Status, InternalData, or unfold.
    """
    out = dict(row) if isinstance(row, dict) else {}
    ft = out.get("FileType")
    if ft not in (None, ""):
        return out
    cat = str(out.get("ItemType") or out.get("Category") or "").strip()
    if cat in SETPARTMODE_FILETYPES:
        out["FileType"] = cat
        return out
    try:
        mode = int(out.get("PartMode"))
    except (TypeError, ValueError):
        return out
    mapped = {0: "Cad", 1: "Linear", 2: "Component"}
    if mode in mapped:
        out["FileType"] = mapped[mode]
    return out


# OnAddDXFClick filter values + FileType value/type. Live 10098-1 posted
# FileType="Cad" (str) and still empty. Do not guess "CAD" / 100.
# Cad-path key *names* only — never InternalData/unfold values.
CAD_PATH_LOG_KEYS = (
    "InternalData",
    "InternalHTML",
    "ImageString",
    "HadOpenContours",
    "OutsidePerimeter",
    "OutsidePerimeter_Units",
    "OutsidePerimeter_UseLocal",
    "Unfold",
    "HasUnfold",
    "Unfolded",
    "DXF",
    "DxfId",
    "DXFID",
    "DxfFileID",
    "HasDXF",
)
_EMPTY_CAD_PAYLOAD_STRINGS = frozenset({"", "[]", "{}", "null", "undefined", "none"})
CAD_INTERNALDATA_EMPTY_AFTER_EXPLODE = "cad_internaldata_empty_after_explode"
STEP_EXPLODE_NO_INTERNALDATA = "step_explode_no_internaldata"
# Exact missing call (QuoteOrderEdit + live 14327-5 plate + 35136-1 bar).
# createAllParts has no intervening CadImport/UI XHR. GET Data/CADData
# are copy-if-nonempty only. Do not invent Contours.
STEP_CONTOURS_MISSING_CALL = "POST /part/create t.List InternalData+ImageString"
STEP_CONTOURS_NO_EXTRA_XHR = "createAllParts_no_intervening_xhr"
# Alternate-path hunt (UpdateData / Data / CADData / ConvertTo / Unfold /
# /part/PartImage / PDFGetData) exhausted in-repo. Fill stays locked.
STEP_CONTOURS_FILL_UNLOCKED = False
STEP_CONTOURS_UNLOCK_REQUIRES = "kyle_contours_ge1_or_sectura_support"
# Kyle Loom lesson (Adjust Properties): Component→Cad is required for
# plate STEP Contours. Q10333 / b5f56ac3 / H.6.38 is a Contours PASS
# (Cad / Contours=1 / 8 bends + Profile / Laser Bay1 / UC 176.96).
# Never remint / PATCH / ZZ-DEL.
# Fill stays fail-close if Contours empty after Cad.
KYLE_LOOM_COMPONENT_TO_CAD = (
    "Kyle Loom: STEP CAD Files Adjust Properties defaults ProductType to "
    "Component; sheet/plate laser must be Cad (inches, Machine Laser) for "
    "Contours to fill. Live PASS Q10333 / b5f56ac3 / H.6.38 Safe Cave "
    "(Cad / Contours=1 / 8 bends + Profile / Laser Bay1 / UC 176.96). "
    "Cad is set via API/kendo ProductType=100 + SetPartMode 0, not a UI click. "
    "Automation Cad classify ≠ Contours fill (H638-CADPLATE / 5e7bfc0b, "
    "Q10334 / e2683a3f). Next: DevTools of Kyle's real Component→Cad "
    "dropdown click XHRs. Do not invent Contours."
)
_THICKNESS_VALUE_UNIT_RE = re.compile(
    r"^\s*([0-9]*\.?[0-9]+)\s*[:\s]\s*"
    r"(meters?|metres?|millimeters?|millimetres?|inches?|inch|mm|in|m)\s*$",
    re.I,
)
EMPTY_EXPLODE_INTERNALDATA_REASONS = frozenset(
    {
        CAD_INTERNALDATA_EMPTY_AFTER_EXPLODE,
        STEP_EXPLODE_NO_INTERNALDATA,
    }
)
CADIMPORT_GET_COPY_KEYS = (
    "InternalData",
    "InternalHTML",
    "Contours",
    "NumberOfContours",
)


def filelist_errorstatus_qty(row: dict[str, Any] | None) -> dict[str, Any]:
    """Posted ErrorStatus and Qty values — OnAddDXFClick filter (not keys)."""
    if not isinstance(row, dict):
        return {"filelist_errorstatus": None, "filelist_qty": None}
    return {
        "filelist_errorstatus": _error_status(row),
        "filelist_qty": _qty_of(row),
    }


def filelist_filetype_value_type(row: dict[str, Any] | None) -> dict[str, str]:
    """Exact FileType value and Python/JS type name — do not invent an enum."""
    if not isinstance(row, dict) or "FileType" not in row:
        return {"filelist_filetype_value": "", "filelist_filetype_type": "missing"}
    ft = row.get("FileType")
    if isinstance(ft, bool):
        typ = "bool"
    elif isinstance(ft, int) and not isinstance(ft, bool):
        typ = "int"
    elif isinstance(ft, float):
        typ = "float"
    elif isinstance(ft, str):
        typ = "str"
    else:
        typ = type(ft).__name__
    return {"filelist_filetype_value": str(ft), "filelist_filetype_type": typ}


def filelist_cad_path_keys(row: dict[str, Any] | None) -> list[str]:
    """InternalData / Unfold / DXF* key names present — never values."""
    if not isinstance(row, dict):
        return []
    return [k for k in CAD_PATH_LOG_KEYS if k in row]


def cad_payload_value_empty(value: Any) -> bool:
    """True when InternalData/ImageString has no payload — never log the value."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().casefold() in _EMPTY_CAD_PAYLOAD_STRINGS
    if isinstance(value, (bytes, bytearray)):
        return len(value) == 0
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) == 0
    return False


def step_explode_no_internaldata() -> str:
    """Status when DoCreateDXFParts t.List bind source has empty InternalData."""
    return STEP_EXPLODE_NO_INTERNALDATA


def empty_explode_internaldata_reason(*, bind_source: bool | None = None) -> str:
    """Alias: empty explode bind source → step_explode_no_internaldata."""
    if bind_source is False:
        return STEP_EXPLODE_NO_INTERNALDATA
    return CAD_INTERNALDATA_EMPTY_AFTER_EXPLODE


def is_empty_explode_internaldata_reason(why: str | None) -> bool:
    """True for cad_internaldata_empty_after_explode or its explode alias."""
    return str(why or "") in EMPTY_EXPLODE_INTERNALDATA_REASONS


def cadimport_get_field_empty(key: str, value: Any) -> bool:
    """True when a GET Contours/InternalData field has no copyable payload.

    OpenContourCount empty/null (live 14327-5) and 0 (live 35136-1) are
    emptiness, not a Contours fill. Do not treat 0 as bindable.
    """
    if cad_payload_value_empty(value):
        return True
    if key in ("NumberOfContours", "Contours", "OpenContourCount"):
        try:
            return int(value) < 1
        except (TypeError, ValueError):
            return cad_payload_value_empty(value)
    return False


def step_contours_missing_call() -> str:
    """Server /part/create t.List InternalData+ImageString — no extra JS step."""
    return STEP_CONTOURS_MISSING_CALL


def step_contours_no_extra_xhr() -> str:
    """createAllParts has no intervening CadImport/UI fill XHR."""
    return STEP_CONTOURS_NO_EXTRA_XHR


def step_contours_fill_unlocked() -> bool:
    """True only after a live nonempty t.List bind or a named fill XHR."""
    return STEP_CONTOURS_FILL_UNLOCKED


def step_contours_unlock_requires() -> str:
    """Kyle Contours≥1 capture or Sectura support naming the fill."""
    return STEP_CONTOURS_UNLOCK_REQUIRES


def cadimport_identity_tokens(row: dict[str, Any] | None) -> set[str]:
    """Nonempty SourceDataID / ID / FileID tokens — never invent."""
    fields = filelist_row_id_fields(row)
    return {
        val
        for val in fields.values()
        if val and not sourcedataid_empty(val)
    }


def cadimport_identity_match(
    src: dict[str, Any] | None,
    dest: dict[str, Any] | None,
) -> bool:
    """True when src and dest share a SID / ID / FileID token."""
    return bool(cadimport_identity_tokens(src) & cadimport_identity_tokens(dest))


def cadimport_get_payload_empty_bools(
    rows: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """GET /CadImport/Data or CADData emptiness — key names, never values.

    Kyle HAR leftover 35136-1: OpenContourCount=0 is emptiness, not a
    Contours fill. Live 14327-5: OpenContourCount empty/null is the same.
    Do not treat 0 / null as bindable.
    """
    kids = [r for r in (rows or []) if isinstance(r, dict)]
    idata_empty = (
        all(cad_payload_value_empty(r.get("InternalData")) for r in kids)
        if kids
        else True
    )
    contours_empty = (
        all(
            cadimport_get_field_empty("Contours", r.get("Contours"))
            and cadimport_get_field_empty(
                "NumberOfContours", r.get("NumberOfContours")
            )
            for r in kids
        )
        if kids
        else True
    )
    occ_empty = (
        all(
            cadimport_get_field_empty(
                "OpenContourCount", r.get("OpenContourCount")
            )
            for r in kids
        )
        if kids
        else True
    )
    bindable = any(
        not cad_payload_value_empty(r.get("InternalData"))
        or not cadimport_get_field_empty("Contours", r.get("Contours"))
        or not cadimport_get_field_empty(
            "NumberOfContours", r.get("NumberOfContours")
        )
        for r in kids
    )
    keys = sorted(str(k) for k in kids[0] if str(k) != "uid") if kids else []
    return {
        "n": len(kids),
        "internaldata_empty": idata_empty,
        "contours_empty": contours_empty,
        "opencontourcount_empty": occ_empty,
        "bindable": bindable,
        "keys": keys,
    }


def persist_cadimport_get_empty_shape(
    route_bools: dict[str, dict[str, Any]] | None,
    *,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    """Persist GET Data/CADData emptiness + key names. Never contour JSON."""
    out: dict[str, Any] = {}
    for route, bools in (route_bools or {}).items():
        if not isinstance(bools, dict):
            continue
        keys = [str(k) for k in (bools.get("keys") or [])]
        out[route] = {
            "n": int(bools.get("n") or 0),
            "internaldata_empty": bool(bools.get("internaldata_empty")),
            "contours_empty": bool(bools.get("contours_empty")),
            "opencontourcount_empty": bool(bools.get("opencontourcount_empty")),
            "bindable": bool(bools.get("bindable")),
            "keys": keys,
        }
        if notes is not None:
            line = f"{route}_bindable=" + (
                "true" if bools.get("bindable") else "false"
            )
            if line not in notes:
                notes.append(line)
            if keys:
                shape = f"{route}_keys=" + ",".join(keys[:24])
                if shape not in notes:
                    notes.append(shape)
            occ = f"{route}_opencontourcount_empty=" + (
                "true" if bools.get("opencontourcount_empty") else "false"
            )
            if occ not in notes:
                notes.append(occ)
    return out


def cadimport_get_is_editor_preview(row: dict[str, Any] | None) -> bool:
    """True when CADData is Length/Width/WebGL preview, not Contours fill."""
    if not isinstance(row, dict):
        return False
    has_preview = any(key in row for key in ("Length", "Width", "WebGL"))
    if not has_preview:
        return False
    return all(
        key not in row or cadimport_get_field_empty(key, row.get(key))
        for key in CADIMPORT_GET_COPY_KEYS
    )


_CADIMPORT_GET_UNWRAP_KEYS = (
    "SourceDataID",
    "FileID",
    "FileName",
    "Name",
    "InternalData",
    "InternalHTML",
    "Contours",
    "NumberOfContours",
    "WebGL",
    "Length",
    "Width",
)


def cadimport_get_rows(payload: Any) -> list[dict[str, Any]]:
    """Rows from GET /CadImport/Data or CADData — including a leftover object.

    A single editor-preview object (Length/Width/WebGL, InternalData empty)
    is returned so emptiness can be logged. Copy-through still requires
    SID/ID/FileID match and nonempty Contours/InternalData. ID-only wrappers
    are not rows. Never invent Contours.
    """
    rows = filelist_from_cadimport_upload(payload)
    if rows:
        return rows
    rows = normalize_cadimport_list(payload)
    if rows:
        return rows
    if not isinstance(payload, dict):
        return []
    if not any(key in payload for key in _CADIMPORT_GET_UNWRAP_KEYS):
        return []
    return [dict(payload)]


def copy_cadimport_get_payload_through(
    src_rows: list[dict[str, Any]] | None,
    dest: dict[str, Any] | None,
) -> dict[str, Any]:
    """Copy nonempty GET Contours/InternalData by SID/ID/FileID. Never invent."""
    out = dict(dest) if isinstance(dest, dict) else {}
    for src in src_rows or []:
        if not isinstance(src, dict):
            continue
        if not cadimport_identity_match(src, out):
            continue
        for key in CADIMPORT_GET_COPY_KEYS:
            if key not in src:
                continue
            if not cadimport_get_field_empty(key, out.get(key)):
                continue
            if cadimport_get_field_empty(key, src.get(key)):
                continue
            out[key] = src[key]
        break
    return out


def filelist_cad_payload_empty_bools(row: dict[str, Any] | None) -> dict[str, bool]:
    """Posted InternalData/ImageString emptiness bools only (live 10098-1)."""
    if not isinstance(row, dict):
        return {
            "filelist_internaldata_empty": True,
            "filelist_imagestring_empty": True,
        }
    return {
        "filelist_internaldata_empty": cad_payload_value_empty(row.get("InternalData")),
        "filelist_imagestring_empty": cad_payload_value_empty(row.get("ImageString")),
    }


def part_create_list_payload_empty_bools(
    rows: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Bind-time /part/create t.List emptiness — first-row bools plus counts.

    Live SC0600: first-row ImageString can be empty while 141/143 are not.
    Keep the two bools separate from ``*_empty_n``. Never log values.
    InternalData is required for Cad Finish (OnAddDXFClick copies it;
    cited bag has no ImageString). Nonempty ImageString is not enough.
    """
    kids = [r for r in (rows or []) if isinstance(r, dict)]
    first = kids[0] if kids else None
    finish = filelist_cad_payload_empty_bools(first)
    n = len(kids)
    idata_empty_n = sum(
        1 for r in kids if cad_payload_value_empty(r.get("InternalData"))
    )
    img_empty_n = sum(
        1 for r in kids if cad_payload_value_empty(r.get("ImageString"))
    )
    bind_rows = part_create_tlist_bind_source_rows(kids)
    producttype_empty = (
        all(cad_payload_value_empty(r.get("ProductType")) for r in kids)
        if kids
        else True
    )
    return {
        "internaldata_empty": finish["filelist_internaldata_empty"],
        "imagestring_empty": finish["filelist_imagestring_empty"],
        "n": n,
        "internaldata_empty_n": idata_empty_n,
        "imagestring_empty_n": img_empty_n,
        "internaldata_key_n": sum(1 for r in kids if "InternalData" in r),
        "imagestring_key_n": sum(1 for r in kids if "ImageString" in r),
        "internaldata_nonempty_n": n - idata_empty_n,
        "imagestring_nonempty_n": n - img_empty_n,
        "tlist_bind_source": bool(bind_rows),
        "tlist_bind_source_n": len(bind_rows),
        "tlist_bind_shape_keys": part_create_tlist_bind_shape_keys(kids),
        "producttype_empty": producttype_empty,
    }


def part_create_tlist_bind_source_rows(
    rows: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """``t.List`` Cad rows that already have InternalData **and** ImageString.

    QuoteOrderEdit binds ``t.List[e]`` as-is onto ``#gridDXFParts``. Only a
    row that already carries both shop-filled fields is a bind source for
    Finish FileList. ImageString-only leftover explodes are **not** this.
    Returns as-is copies — never invents keys or contour JSON.
    """
    if not isinstance(rows, list):
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if "InternalData" not in row or "ImageString" not in row:
            continue
        if cad_payload_value_empty(row.get("InternalData")):
            continue
        if cad_payload_value_empty(row.get("ImageString")):
            continue
        out.append(dict(row))
    return out


def part_create_tlist_is_bind_source(rows: list[dict[str, Any]] | None) -> bool:
    """True when ``t.List`` already has a nonempty InternalData+ImageString row."""
    return bool(part_create_tlist_bind_source_rows(rows))


def part_create_tlist_bind_shape_keys(
    rows: list[dict[str, Any]] | None,
) -> list[str]:
    """Key names on the first bind-source ``t.List`` row (never the values)."""
    bind = part_create_tlist_bind_source_rows(rows)
    if not bind:
        return []
    return sorted(str(k) for k in bind[0] if k != "uid")


def persist_part_create_tlist_bind_source(
    rows: list[dict[str, Any]] | None,
    *,
    notes: list[str] | None = None,
    client: Any = None,
) -> dict[str, Any]:
    """Persist a live nonempty ``t.List`` shape as the ``#gridDXFParts`` bind source.

    Call before ``AddItem_DXFFiles``. Key names only — never contour JSON.
    ImageString-only leftover explodes stay ``tlist_bind_source=false``.
    Empty InternalData still refuses Finish. ImageString-without-InternalData
    is preview only (live 21785-2).
    """
    bind_rows = part_create_tlist_bind_source_rows(rows)
    is_bind = bool(bind_rows)
    keys = part_create_tlist_bind_shape_keys(rows)
    preview_only = tlist_imagestring_without_internaldata(rows)
    out = {
        "tlist_bind_source": is_bind,
        "tlist_bind_source_n": len(bind_rows),
        "tlist_bind_shape_keys": keys,
        "imagestring_without_internaldata": preview_only,
    }
    if client is not None:
        client._tlist_bind_source = is_bind
        client._tlist_bind_shape_keys = list(keys)
        payload = getattr(client, "_part_create_payload", None)
        if isinstance(payload, dict):
            merged = dict(payload)
            merged.update(out)
            client._part_create_payload = merged
    if notes is not None:
        line = "tlist_bind_source=" + ("true" if is_bind else "false")
        if line not in notes:
            notes.append(line)
        if is_bind and keys:
            shape = "tlist_bind_shape_keys=" + ",".join(keys)
            if shape not in notes:
                notes.append(shape)
        preview = "imagestring_without_internaldata=" + (
            "true" if preview_only else "false"
        )
        if preview not in notes:
            notes.append(preview)
        if not is_bind:
            alias = STEP_EXPLODE_NO_INTERNALDATA
            if alias not in notes:
                notes.append(alias)
            persist_kyle_step_contours_capture_gap(notes)
    return out


KYLE_STEP_CONTOURS_CAPTURE = "kyle_step_contours_capture"
STEP_CONTOURS_CAPTURE_WINDOWS = (
    "upload_to_next",
    "part_create",
    "explode_to_finish",
    "additem_dxffiles",
)
STEP_CONTOURS_NOT_FILL_PATHS = frozenset(
    {
        "/CadImport/ConvertTo",
        "/CadImport/UpdateData",
        "/CadImport/UpdateDataNext",
        "/CadImport/SetPartMode",
        "/CadImport/SetUnits",
        "/CadImport/GetDXFData",
        "/part/PartImage",
        "/Quote/DXFInternal",
        "/Quote/GetPerimeterAndWeight",
        "/Quote/GetDXFData",
    }
)
STEP_CONTOURS_KNOWN_PATHS = frozenset(
    {
        "/CadImport/UploadItem_DXFFiles",
        "/part/create",
        "/CadImport/Data",
        "/CadImport/CADData",
        "/Quote/AddItem_DXFFiles",
        "/CadImport/SetPartMode",
        "/CadImport/SetUnits",
    }
)
STEP_CONTOURS_CAPTURE_NEVER_SAVE = (
    "InternalData JSON",
    "ImageString base64",
    "Contours geometry",
    "cookies",
    "anti-forgery tokens",
    "file bytes",
)


def cadimport_capture_path(url: Any) -> str:
    """Path only — drop host and query. Never log values."""
    from urllib.parse import urlparse

    text = str(url or "").strip()
    if not text:
        return ""
    if "://" not in text and not text.startswith("/"):
        text = "/" + text
    parsed = urlparse(text if "://" in text else "https://dummy.invalid" + text)
    path = parsed.path or text.split("?", 1)[0]
    if not path.startswith("/"):
        path = "/" + path
    return path


def kyle_step_contours_devtools_capture() -> dict[str, Any]:
    """Exact DevTools XHRs Kyle must save on a manual STEP Finish with Contours.

    Bind source is still POST /part/create t.List with nonempty InternalData
    and ImageString. No live capture of that bind exists. Kyle HAR leftover
    35136-1 / 8973f890: Upload → CadImport/Data OpenContourCount=0 →
    /part/create 3× bar InternalData empty → AddItem_DXFFiles InternalData
    empty bar_flat. Live 14327-5 / c5cd8689 flat plate: /part/create n=1
    InternalData empty, ImageString preview-only, ProductType null,
    CadImport Data/CADData bindable=false, OpenContourCount empty/null.
    QuoteOrderEdit createAllParts has no intervening CadImport/UI XHR.
    Exact missing call: POST /part/create t.List InternalData+ImageString.
    Contours never filled — confirms fail-close; does not unlock Contours
    fill. Contours UI leftovers Q10329 / 14327-3, Q10330 / 21841-1,
    Q10331 / 14327-1 never showed a Contours column and never clicked
    Finish. Q10333 / H.6.38 / Safe Cave is a Contours PASS protect
    (Cad / Contours=1 / 8 bends + Profile / Laser Bay1 / UC 176.96;
    unlock Component→Cad then thickness inches then Contours fill) —
    never remint / PATCH / ZZ-DEL. Automation sets Cad via API/kendo field.
    Cad classify ≠ Contours fill (H638-CADPLATE / 5e7bfc0b, Q10334 /
    e2683a3f). Next: DevTools of Kyle's real dropdown click XHRs.
    Q10332 is a wrong-org Time mint (ZZ-DEL-wrong-org-Time; ID unknown).
    Do not invent Contours. Do not remint spent STEP leftovers.
    """
    return {
        "purpose": (
            "Manual Time STEP Finish that shows Contours "
            "(GET DataPartPDF.NumberOfContours >= 1) — save these XHRs"
        ),
        "fresh_pn_only": True,
        "windows": list(STEP_CONTOURS_CAPTURE_WINDOWS),
        "must_save": (
            {
                "method": "POST",
                "path": "/CadImport/UploadItem_DXFFiles",
                "window": "upload",
                "save": (
                    "response List key names",
                    "InternalData/ImageString/Contours emptiness bools",
                ),
            },
            {
                "method": "POST",
                "path": "/part/create",
                "window": "part_create",
                "role": "expected_bind_source",
                "save": (
                    "request keys Location/IDList[]/unitList[]/"
                    "OtherFileIDList[]/Height/Width (types+zero, not values)",
                    "t.List n + key names",
                    "InternalData empty_n/nonempty_n",
                    "ImageString empty_n/nonempty_n",
                    "Contours/NumberOfContours emptiness",
                ),
                "bindable_when": "InternalData nonempty AND ImageString nonempty",
            },
            {
                "method": "*",
                "path": "*",
                "window": "upload_to_next",
                "save": (
                    "every XHR between upload success and blue Next: "
                    "method, path, request key names, response key names, "
                    "InternalData/ImageString/Contours emptiness"
                ),
            },
            {
                "method": "*",
                "path": "*",
                "window": "explode_to_finish",
                "save": (
                    "every XHR between /part/create success and green Finish: "
                    "same emptiness summary"
                ),
            },
            {
                "method": "GET",
                "path": "/CadImport/Data",
                "window": "explode_to_finish",
                "role": "copy_if_nonempty",
            },
            {
                "method": "GET",
                "path": "/CadImport/CADData",
                "window": "explode_to_finish",
                "role": "copy_if_nonempty_or_editor_preview",
            },
            {
                "method": "POST",
                "path": "/Quote/AddItem_DXFFiles",
                "window": "additem_dxffiles",
                "role": "copy_only",
                "save": (
                    "FileList key names + InternalData/Contours emptiness "
                    "(not JSON)"
                ),
            },
        ),
        "never_save": STEP_CONTOURS_CAPTURE_NEVER_SAVE,
        "ui_notes": (
            "Did #DXFEdit open?",
            "Did a thumbnail/part preview click happen?",
            "Units inch vs mm?",
            "Spinner after Next? How long until Contours appeared?",
        ),
        "not_fill_xhr": (
            "ConvertTo",
            "UpdateData",
            "UpdateDataNext",
            "Detect*",
            "Remove*",
            "GetDXFData",
            "PartImage",
            "Quote/DXFInternal",
            "GetPerimeterAndWeight",
            "SetPartMode",
            "CADData editor preview",
        ),
        "image_files_analog": (
            "Image Files Contours come from PDFGetData/PDFInternal onto "
            "FileList InternalData",
            "STEP analog is DoCreateDXFParts t.List InternalData+ImageString "
            "as-is",
            "Do not copy PDFGetData onto STEP FileList",
        ),
        "must_save_bind": (
            "POST /part/create t.List InternalData+ImageString emptiness "
            "(key names only) on a Finish that shows Contours"
        ),
        "missing_call": STEP_CONTOURS_MISSING_CALL,
        "no_extra_cadimport_xhr": STEP_CONTOURS_NO_EXTRA_XHR,
        "fill_unlocked": STEP_CONTOURS_FILL_UNLOCKED,
        "unlock_requires": STEP_CONTOURS_UNLOCK_REQUIRES,
        "invent": False,
        "fail_close_if_empty": True,
    }


def persist_kyle_step_contours_capture_gap(
    notes: list[str] | None,
) -> dict[str, Any]:
    """Documentary capture gap after empty explode. Never invent Contours."""
    recipe = kyle_step_contours_devtools_capture()
    if notes is not None:
        token = KYLE_STEP_CONTOURS_CAPTURE + "=" + str(recipe["must_save_bind"])
        if token not in notes:
            notes.append(token)
        windows = "kyle_capture_windows=" + ",".join(recipe["windows"])
        if windows not in notes:
            notes.append(windows)
        missing = "missing_call=" + STEP_CONTOURS_MISSING_CALL
        if missing not in notes:
            notes.append(missing)
        no_extra = "no_extra_cadimport_xhr=" + STEP_CONTOURS_NO_EXTRA_XHR
        if no_extra not in notes:
            notes.append(no_extra)
        unlocked = "fill_unlocked=" + (
            "true" if STEP_CONTOURS_FILL_UNLOCKED else "false"
        )
        if unlocked not in notes:
            notes.append(unlocked)
        requires = "unlock_requires=" + STEP_CONTOURS_UNLOCK_REQUIRES
        if requires not in notes:
            notes.append(requires)
    return recipe


def _capture_response_rows(xhr: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(xhr, dict):
        return []
    for key in ("response_rows", "List", "rows"):
        raw = xhr.get(key)
        if isinstance(raw, list):
            return [r for r in raw if isinstance(r, dict)]
    resp = xhr.get("response")
    if resp is None:
        return []
    return cadimport_get_rows(resp)


def summarize_cadimport_capture_xhr(xhr: dict[str, Any] | None) -> dict[str, Any]:
    """Sanitize one DevTools XHR: key names + emptiness. Never values."""
    if not isinstance(xhr, dict):
        return {
            "method": "",
            "path": "",
            "request_keys": [],
            "response_keys": [],
            "n": 0,
            "internaldata_empty": True,
            "imagestring_empty": True,
            "contours_empty": True,
            "opencontourcount_empty": True,
            "producttype_empty": True,
            "tlist_bind_source": False,
            "bindable": False,
            "editor_preview": False,
            "not_fill": False,
        }
    path = cadimport_capture_path(xhr.get("path") or xhr.get("url") or "")
    method = str(xhr.get("method") or "").upper()
    req_keys = [
        str(k)
        for k in (xhr.get("request_keys") or xhr.get("requestKeys") or [])
        if str(k)
        and not str(k).startswith("__Request")
        and str(k) != "afToken"
    ]
    rows = _capture_response_rows(xhr)
    get_bools = cadimport_get_payload_empty_bools(rows)
    tlist = part_create_list_payload_empty_bools(rows)
    pre_bind = xhr.get("tlist_bind_source")
    pre_id_non = xhr.get("internaldata_nonempty_n")
    pre_img_non = xhr.get("imagestring_nonempty_n")
    if rows:
        bindable = bool(
            tlist.get("tlist_bind_source") or get_bools.get("bindable")
        )
        tlist_bind = bool(tlist.get("tlist_bind_source"))
        id_empty = bool(tlist.get("internaldata_empty"))
        img_empty = bool(tlist.get("imagestring_empty"))
        contours_empty = bool(get_bools.get("contours_empty"))
        occ_empty = bool(get_bools.get("opencontourcount_empty"))
        producttype_empty = bool(tlist.get("producttype_empty"))
        n = int(tlist.get("n") or get_bools.get("n") or 0)
        keys = list(get_bools.get("keys") or [])
        editor = any(cadimport_get_is_editor_preview(r) for r in rows)
    else:
        try:
            id_non = int(pre_id_non or 0)
        except (TypeError, ValueError):
            id_non = 0
        try:
            img_non = int(pre_img_non or 0)
        except (TypeError, ValueError):
            img_non = 0
        tlist_bind = bool(pre_bind) or (id_non > 0 and img_non > 0)
        bindable = tlist_bind
        id_empty = id_non <= 0
        img_empty = img_non <= 0
        contours_empty = True
        occ_empty = True
        producttype_empty = True
        try:
            n = int(xhr.get("n") or 0)
        except (TypeError, ValueError):
            n = 0
        keys = [str(k) for k in (xhr.get("keys") or xhr.get("response_keys") or [])]
        editor = False
    return {
        "method": method,
        "path": path,
        "request_keys": req_keys,
        "response_keys": keys,
        "n": n,
        "internaldata_empty": id_empty,
        "imagestring_empty": img_empty,
        "contours_empty": contours_empty,
        "opencontourcount_empty": occ_empty,
        "producttype_empty": producttype_empty,
        "tlist_bind_source": tlist_bind,
        "bindable": bindable,
        "editor_preview": editor,
        "not_fill": path in STEP_CONTOURS_NOT_FILL_PATHS,
    }


def classify_step_contours_capture(
    xhrs: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Classify a sanitized DevTools capture. Empty stays fail-close.

    A bindable unexpected path is a *candidate* only — do not POST it.
    Never invent Contours/InternalData. Leftover 35136-1 HAR
    (OpenContourCount=0 / 3× bar empty / AddItem_DXFFiles bar_flat empty)
    and leftover 14327-5 (flat plate / OpenContourCount empty/null /
    ProductType null / Data+CADData bindable=false) stay fail-close.
    Exact missing call is POST /part/create t.List InternalData+ImageString
    — QuoteOrderEdit createAllParts has no extra CadImport/UI step.
    """
    summaries = [summarize_cadimport_capture_xhr(x) for x in (xhrs or [])]
    bind = next(
        (s for s in summaries if s.get("tlist_bind_source")),
        None,
    )
    if bind is None:
        bind = next((s for s in summaries if s.get("bindable")), None)
    candidates = [
        s["path"]
        for s in summaries
        if s.get("bindable")
        and s.get("path")
        and s["path"] not in STEP_CONTOURS_KNOWN_PATHS
        and not s.get("not_fill")
        and not s.get("editor_preview")
    ]
    present = {s.get("path") for s in summaries if s.get("path")}
    missing: list[str] = []
    if "/part/create" not in present:
        missing.append("part_create")
    if not any(
        s.get("path") == "/CadImport/UploadItem_DXFFiles" for s in summaries
    ):
        missing.append("upload")
    if "/Quote/AddItem_DXFFiles" not in present:
        missing.append("additem_dxffiles")
    finish_ok = bool(bind)
    return {
        "bind_source_path": str((bind or {}).get("path") or ""),
        "bindable": finish_ok,
        "candidate_fill_paths": candidates,
        "finish_ok": finish_ok,
        "finish_why": (
            ""
            if finish_ok
            else CAD_INTERNALDATA_EMPTY_AFTER_EXPLODE
        ),
        "step_explode_no_internaldata": not finish_ok,
        "kyle_capture_missing": missing,
        "missing_call": STEP_CONTOURS_MISSING_CALL,
        "no_extra_cadimport_xhr": STEP_CONTOURS_NO_EXTRA_XHR,
        "invent": False,
        "xhrs": summaries,
    }


def persist_cadimport_xhr_capture(
    xhrs: list[dict[str, Any]] | None,
    *,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    """Persist Next-hook XHR emptiness. Candidate paths are documentary only."""
    classified = classify_step_contours_capture(xhrs)
    if notes is not None:
        paths = []
        for row in classified.get("xhrs") or []:
            path = str(row.get("path") or "")
            if path and path not in paths:
                paths.append(path)
        notes.append(f"cadimport_xhr_n={len(classified.get('xhrs') or [])}")
        if paths:
            notes.append("cadimport_xhr_paths=" + ",".join(paths[:16]))
        for cand in classified.get("candidate_fill_paths") or []:
            line = f"cadimport_xhr_candidate={cand}"
            if line not in notes:
                notes.append(line)
        if not classified.get("bindable"):
            persist_kyle_step_contours_capture_gap(notes)
    return classified


def _tlist_name_token(value: Any) -> str:
    return str(value or "").strip()


def _tlist_token_is_root(value: str) -> bool:
    return value.casefold() == "root"


def _tlist_token_is_jobpn(value: str, part_key: str) -> bool:
    pn = str(part_key or "").strip()
    if not pn or not value:
        return False
    return value.casefold() == pn.casefold()


def part_create_list_name_tokens(
    rows: list[dict[str, Any]] | None,
    *,
    part_key: str = "",
) -> dict[str, int]:
    """t.List Name/PartName/FileName Root vs job-PN counts — not other nouns."""
    kids = [r for r in (rows or []) if isinstance(r, dict)]
    out = {
        "tlist_name_root_n": 0,
        "tlist_name_jobpn_n": 0,
        "tlist_name_other_n": 0,
        "tlist_partname_root_n": 0,
        "tlist_partname_jobpn_n": 0,
        "tlist_partname_other_n": 0,
        "tlist_filename_root_n": 0,
        "tlist_filename_jobpn_n": 0,
        "tlist_filename_other_n": 0,
    }
    fields = (
        ("Name", "tlist_name"),
        ("PartName", "tlist_partname"),
        ("FileName", "tlist_filename"),
    )
    for row in kids:
        for src, prefix in fields:
            tok = _tlist_name_token(row.get(src))
            if _tlist_token_is_root(tok):
                out[f"{prefix}_root_n"] += 1
            elif _tlist_token_is_jobpn(tok, part_key):
                out[f"{prefix}_jobpn_n"] += 1
            elif tok:
                out[f"{prefix}_other_n"] += 1
    return out


def is_cad_filelist_row(row: dict[str, Any] | None) -> bool:
    """Posted FileType/ItemType/Category Cad — do not guess CAD / ProductType 100."""
    if not isinstance(row, dict):
        return False
    ft = str(row.get("FileType") or "").strip()
    if ft == "Cad":
        return True
    cat = str(row.get("ItemType") or row.get("Category") or "").strip()
    if cat == "Cad":
        return True
    try:
        return int(row.get("PartMode")) == 0
    except (TypeError, ValueError):
        return False


def cad_filelist_payload_blocks_finish(row: dict[str, Any] | None) -> bool:
    """Cad AddItem_DXFFiles no-ops when InternalData/ImageString keys are empty.

    Live 10098-1 posted those keys. Skip only when a key is present and empty.
    Do not invent unfold/geometry. Keys absent is not this miss.
    """
    if not isinstance(row, dict) or not is_cad_filelist_row(row):
        return False
    bools = filelist_cad_payload_empty_bools(row)
    if "InternalData" in row and bools["filelist_internaldata_empty"]:
        return True
    if "ImageString" in row and bools["filelist_imagestring_empty"]:
        return True
    return False


def cad_filelist_contours_would_be_zero(row: dict[str, Any] | None) -> bool:
    """True when Cad FileList InternalData is empty or NumberOfContours is 0.

    Do not invent Contours. Keys absent is not a contours-zero miss.
    Empty InternalData means Finish would land Contours 0.
    """
    if not isinstance(row, dict) or not is_cad_filelist_row(row):
        return False
    bools = filelist_cad_payload_empty_bools(row)
    if "InternalData" in row and bools["filelist_internaldata_empty"]:
        return True
    for key in ("NumberOfContours", "Contours"):
        if key not in row:
            continue
        try:
            if int(row.get(key) or 0) < 1:
                return True
        except (TypeError, ValueError):
            return True
    return False


def imagestring_without_internaldata_refuses_finish(
    row: dict[str, Any] | None,
) -> bool:
    """Preview ImageString is not InternalData. Live 21785-2: 13/13 vs 14/14 empty."""
    if not isinstance(row, dict) or not is_cad_filelist_row(row):
        return False
    if "InternalData" not in row:
        return False
    if not cad_payload_value_empty(row.get("InternalData")):
        return False
    return not cad_payload_value_empty(row.get("ImageString"))


def tlist_imagestring_without_internaldata(
    rows: list[dict[str, Any]] | None,
) -> bool:
    """True when t.List has preview ImageString and no nonempty InternalData."""
    kids = [r for r in (rows or []) if isinstance(r, dict)]
    if not kids:
        return False
    any_img = any(
        not cad_payload_value_empty(r.get("ImageString")) for r in kids
    )
    any_id = any(
        not cad_payload_value_empty(r.get("InternalData")) for r in kids
    )
    return bool(any_img and not any_id)


def filelist_row_partmode_set(row: dict[str, Any] | None) -> bool:
    """True when classify stamped PartMode (0 Cad is set, not null)."""
    if not isinstance(row, dict):
        return False
    if "PartMode" not in row:
        return False
    return not part_mode_is_null(row.get("PartMode"))


def filelist_kids_partmode_set(rows: list[dict[str, Any]] | None) -> bool:
    """True when every non-Assembly kid has PartMode set (0 Cad is set)."""
    return not classified_kids_missing_part_mode(rows) and any(
        isinstance(r, dict)
        and str(r.get("Category") or r.get("ItemType") or "") != "Assembly"
        for r in (rows or [])
    )


def filelist_post_key_shape(row: dict[str, Any] | None) -> dict[str, list[str]]:
    """Posted FileList key names + which are nonempty. Never values."""
    if not isinstance(row, dict):
        return {"keys": [], "nonempty_keys": [], "empty_keys": []}
    keys = sorted(str(k) for k in row if str(k) != "uid")
    nonempty = [k for k in keys if not cad_payload_value_empty(row.get(k))]
    empty = [k for k in keys if cad_payload_value_empty(row.get(k))]
    return {"keys": keys, "nonempty_keys": nonempty, "empty_keys": empty}


def page_dxf_finish_skip_why(rows: list[dict[str, Any]] | None) -> str | None:
    """Why page OnAddDXFClick is skipped. None means invoke the green Finish.

    Live 28768-1: PartMode Cad + page Finish with InternalData null /
    OutsidePerimeter 0 / ProductSubType bar_flat → HTTP 200 / GET 0 Cad.
    Cad explode InternalData empty is fail-close before Finish (do not
    invent). PartMode set still allows page Finish when InternalData is
    present even if CadType/Stock look empty (live 10289-4 reconstructed
    skip). PartMode null + empty payload still skip.
    """
    kids = [sanitize_cad_partmode_filelist_row(r) for r in (rows or []) if isinstance(r, dict)]
    if not kids:
        return "empty_dataSource"
    for row in kids:
        if cad_filelist_refuses_additem_dxf(row):
            return "cad_internaldata_empty_after_explode"
    if filelist_kids_partmode_set(kids):
        return None
    row0 = kids[0]
    ident = filelist_missing_cadimport_identity_keys(kendo_identity_log_keys(row0))
    if ident:
        return "filelist_missing_keys=" + "+".join(ident)
    if not is_cad_filelist_row(row0):
        return None
    if cad_filelist_payload_blocks_finish(row0) or (
        "ImageString" in row0 and cad_payload_value_empty(row0.get("ImageString"))
    ):
        return "filelist_cad_payload_empty"
    if cad_filelist_contours_would_be_zero(row0):
        return "filelist_contours_zero"
    return None


def product_type_is_component(value: Any) -> bool:
    """Sectura Adjust Properties default — 200 / Component."""
    if value in (200, "200"):
        return True
    return str(value or "").strip().casefold() == "component"


def product_type_is_cad(value: Any) -> bool:
    """Cad classify / bind — 100 or the Adjust Properties 'Cad' token."""
    if value in (100, "100"):
        return True
    return str(value or "").strip().casefold() == "cad"


def _format_bind_thickness_inches(val: float) -> str:
    """Bare inch number for the Adjust Properties thickness dropdown."""
    rounded = round(float(val), 4)
    if abs(rounded - val) < 1e-9 or abs(val - rounded) <= 0.00015:
        text = f"{rounded:.4f}".rstrip("0").rstrip(".")
        if "." not in text:
            text = f"{rounded:.4f}"
        return text
    return f"{val:.4g}"


def sanitize_bind_thickness_inches(
    raw: Any,
    units: Any = None,
) -> str | None:
    """Prefer inches. Do not leave broken ``0.0048:meter`` UI strings.

    Kyle Adjust Properties expects in. Meter/mm tokens convert; inch
    tokens stay numeric. Unparseable values return None (caller keeps
    the original). Never invent Contours.
    """
    if raw in (None, ""):
        return None
    text = str(raw).strip().replace('"', "").replace("″", "").replace("'", "")
    unit = str(units or "").strip().lower()
    matched = _THICKNESS_VALUE_UNIT_RE.match(text)
    if matched:
        try:
            val = float(matched.group(1))
        except (TypeError, ValueError):
            return None
        unit = str(matched.group(2) or unit).strip().lower()
    else:
        try:
            val = float(text)
        except (TypeError, ValueError):
            from quote_core.part_materials import _parse_thickness_token

            parsed = _parse_thickness_token(text)
            if parsed is None:
                return None
            val = float(parsed)
    if unit in {"meter", "metre", "meters", "metres", "m"}:
        val = val / 0.0254
    elif unit.startswith("mill") or unit == "mm":
        val = val / 25.4
    if val <= 0:
        return None
    return _format_bind_thickness_inches(val)


def bind_plate_step_product_type_cad(row: dict[str, Any] | None) -> dict[str, Any]:
    """STEP CAD Files Adjust Properties / part bind: Component default → Cad.

    Writes the API/kendo fields Kyle's dropdown persists (ProductType=100,
    PartMode 0, FileType/ItemType/Category Cad, Machine Laser, thickness
    inches). Does not invent InternalData / Contours / NumberOfContours.
    """
    out = dict(row) if isinstance(row, dict) else {}
    out["ProductType"] = 100
    out["PartMode"] = 0
    out["ItemType"] = "Cad"
    out["Category"] = "Cad"
    out["FileType"] = "Cad"
    out["IsPlate"] = True
    out["IsLinear"] = False
    out["IsPart"] = True
    machine = out.get("Machine") or "Laser - Bay1"
    if str(machine).casefold() == "laser":
        machine = "Laser - Bay1"
    out["Machine"] = machine
    inch = sanitize_bind_thickness_inches(
        out.get("Thickness"), out.get("Thickness_Units")
    )
    if inch is not None:
        out["Thickness"] = inch
        out["Thickness_Units"] = "inch"
    return out


def plate_step_left_component_refuses_contours(
    row: dict[str, Any] | None,
) -> str | None:
    """Component left on a Cad-classified plate is the Contours fail path.

    Kyle Loom: Component→Cad is required for plate STEP Contours. If
    FileType/PartMode is Cad but ProductType is still Component, Sectura
    does not fill Contours. Do not invent InternalData.
    """
    if not isinstance(row, dict):
        return None
    cad_classified = is_cad_filelist_row(row) or str(
        row.get("Category") or row.get("ItemType") or ""
    ).strip() == "Cad"
    if not cad_classified:
        return None
    if not product_type_is_component(row.get("ProductType")):
        return None
    return (
        "Plate STEP ProductType still Component after Cad classify — "
        "Contours fail path (Kyle Loom Component→Cad required; "
        "Q10333 / H.6.38 PASS Cad / Contours=1 / 8 bends + Profile / "
        "Laser Bay1 / UC 176.96). Do not invent Contours/InternalData."
    )


def cad_filelist_refuses_additem_dxf(row: dict[str, Any] | None) -> str | None:
    """Refuse AddItem_DXFFiles when Cad InternalData is empty.

    Live 28768-1: PartMode Cad + page Finish with InternalData null
    landed GET 0 Cad. Kyle Loom c9d7 Cad plates Finish with real
    profile geometry from explode — do not invent InternalData.
    ImageString-without-InternalData is preview only (live 21785-2).
    Component left after Cad classify is the Contours fail path
    (Kyle Loom Component→Cad; Q10333 / H.6.38 PASS Cad / Contours=1 /
    8 bends + Profile / Laser Bay1 / UC 176.96).
    """
    from secturafab.cadimport_js import NEEDS_INTERNALDATA_FILL_XHR

    left = plate_step_left_component_refuses_contours(row)
    if left:
        return left
    if not isinstance(row, dict) or not is_cad_filelist_row(row):
        return None
    if not cad_payload_value_empty(row.get("InternalData")):
        if cad_filelist_contours_would_be_zero(row):
            return (
                "Cad FileList Contours would be 0 — "
                "refusing AddItem_DXFFiles. "
                f"{NEEDS_INTERNALDATA_FILL_XHR}: classify→Finish has no named "
                "InternalData fill XHR (not UpdateDXF_LoadNew / UpdateDataNext / "
                "SetPartMode / unfold). "
                "Do not invent InternalData."
            )
        return None
    if not (
        filelist_row_partmode_set(row)
        or cad_filelist_payload_blocks_finish(row)
        or imagestring_without_internaldata_refuses_finish(row)
    ):
        return None
    return (
        "Cad FileList InternalData empty after explode — "
        "refusing AddItem_DXFFiles (live 28768-1; 28769-1 leftover "
        "c146ce6d; 35136-1 leftover 8973f890; 14327-5 leftover "
        "c5cd8689; 14327-8 leftover 1cd941c6; 14327-3 leftover "
        "75f07c2b; 21841-1 leftover aed89628; 14327-1 leftover "
        "5e72fe39; H638-CADPLATE leftover 5e7bfc0b; Q10334 leftover "
        "e2683a3f; ZZ-DEL). "
        f"{STEP_EXPLODE_NO_INTERNALDATA} aliases "
        f"{CAD_INTERNALDATA_EMPTY_AFTER_EXPLODE}. "
        "ImageString-without-InternalData is preview only (live 21785-2). "
        f"{NEEDS_INTERNALDATA_FILL_XHR}: classify→Finish has no named "
        "InternalData fill XHR (not UpdateDXF_LoadNew / UpdateDataNext / "
        "SetPartMode / unfold). "
        f"missing_call={STEP_CONTOURS_MISSING_CALL}. "
        f"no_extra_cadimport_xhr={STEP_CONTOURS_NO_EXTRA_XHR}. "
        "Do not invent InternalData."
    )


def cad_finish_notes_refuse_additem_dxf(
    notes: list[str] | None,
) -> str | None:
    """Push fail-close token after finish_cad_files refused AddItem_DXFFiles."""
    from secturafab.cadimport_js import NEEDS_INTERNALDATA_FILL_XHR

    for note in notes or []:
        text = str(note)
        if (
            NEEDS_INTERNALDATA_FILL_XHR in text
            or STEP_EXPLODE_NO_INTERNALDATA in text
            or CAD_INTERNALDATA_EMPTY_AFTER_EXPLODE in text
            or "refusing AddItem_DXFFiles" in text
            or "Contours fail path" in text
            or "ProductType still Component" in text
        ):
            return text
    return None


def cad_finish_notes_pack_missing(notes: list[str] | None) -> str | None:
    """Push fail-close after Finish landed 0 Cad / empty Contours / no pack."""
    markers = (
        "GET 0 Cad after Finish",
        "Cad Contours empty after Finish",
        "Cad PR+laser pack missing after Finish",
        "Linear Saw pack missing after Finish",
    )
    for note in notes or []:
        text = str(note)
        if any(marker in text for marker in markers):
            return text
    return None


def kendo_filelist_for_finish(
    rows: list[dict[str, Any]] | None,
    *,
    from_datasource: bool,
) -> dict[str, Any]:
    """EDIT kendo FileList for OnAddDXFClick — SID required after ID copy.

    Live 11796-2: row had FileType Cad but SourceDataID=0. filelist_from_kendo
    is true only when rows came from that dataSource and every row has a
    non-empty SourceDataID after the copy.
    """
    src_rows = [r for r in (rows or []) if isinstance(r, dict)]
    filled = fill_kendo_filelist_sourcedataid(src_rows)
    filled = [
        sanitize_cad_partmode_filelist_row(
            persist_setpartmode_filetype(
                copy_cadimport_identity_through(
                    src_rows[i] if i < len(src_rows) else {}, dest
                )
            )
        )
        for i, dest in enumerate(filled)
    ]
    n = len(filled)
    sid_n = sum(1 for r in filled if not sourcedataid_empty(r.get("SourceDataID")))
    id_n = sum(1 for r in filled if not sourcedataid_empty(r.get("ID")))
    fileid_n = sum(1 for r in filled if not sourcedataid_empty(r.get("FileID")))
    from_kendo = bool(from_datasource and n > 0 and sid_n == n)
    ident_miss = kendo_lacks_cadimport_identity(filled)
    row0 = filled[0] if filled else None
    payload_block = cad_filelist_payload_blocks_finish(row0)
    refuse = cad_filelist_refuses_additem_dxf(row0)
    # PartMode set still allows missing CadType/Stock (live 10289-4).
    # Empty Cad InternalData after explode is fail-close (live 28768-1).
    partmode_ready = filelist_kids_partmode_set(filled)
    why = ""
    if n > 0 and sid_n == 0:
        why = "filelist_missing_ids"
    elif refuse:
        if (
            row0 is not None
            and not cad_payload_value_empty(row0.get("InternalData"))
            and cad_filelist_contours_would_be_zero(row0)
        ):
            why = "filelist_contours_zero"
        elif payload_block and not partmode_ready:
            why = "filelist_cad_payload_empty"
        else:
            why = "cad_internaldata_empty_after_explode"
    elif payload_block and not partmode_ready:
        why = "filelist_cad_payload_empty"
    elif ident_miss and not partmode_ready:
        why = "filelist_missing_keys=" + "+".join(ident_miss)
    elif not from_kendo:
        why = "filelist_not_kendo"
    return {
        "FileList": filled,
        "filelist_from_kendo": from_kendo,
        "filelist_sourcedataid_n": sid_n,
        "filelist_id_n": id_n,
        "filelist_fileid_n": fileid_n,
        "finish_filelist_n": n,
        "finish_why": why,
        "step_explode_no_internaldata": bool(
            refuse and why == CAD_INTERNALDATA_EMPTY_AFTER_EXPLODE
        ),
        "filelist_missing_identity": ident_miss,
        "kendo_row_keys": kendo_identity_log_keys(filled[0]) if filled else [],
        "should_finish": bool(
            from_kendo
            and not refuse
            and (partmode_ready or (not payload_block and not ident_miss))
        ),
        **filelist_errorstatus_qty(filled[0] if filled else None),
        **filelist_filetype_value_type(filled[0] if filled else None),
        "filelist_cad_path_keys": filelist_cad_path_keys(
            filled[0] if filled else None
        ),
        **filelist_cad_payload_empty_bools(filled[0] if filled else None),
    }


def cadimport_filelist_exploded(
    rows: list[dict[str, Any]] | None,
    *,
    part_key: str = "",
    cad_filename: str = "",
) -> bool:
    """True when CadImport split the STEP into child FileList rows (Kyle Next).

    Multi-kid *ASSY* / *WELDMENT* only (live 28110-2) is one-level nest, not
    leaf-exploded. Callers must re-explode those IDs before Finish.
    """
    kids = [r for r in (rows or []) if isinstance(r, dict)]
    if not kids:
        return False
    if len(kids) >= 2:
        return True
    return not is_raw_step_upload_row(
        kids[0], part_key=part_key, cad_filename=cad_filename
    )


def filelist_row_display_name(row: dict[str, Any] | None) -> str:
    if not isinstance(row, dict):
        return ""
    return str(
        row.get("Name")
        or row.get("PartName")
        or row.get("Description")
        or row.get("FileName")
        or ""
    ).strip()


def is_nested_assembly_name(name: str | None) -> bool:
    """*ASSY* / *ASM* / *WELDMENT* / *ASSEMBLY* titles — not leaf nouns.

    ``*ASM`` / ``*-ASM`` is the same class as ``*ASSY*`` (live BB2000-ASM).
    Do not match the letters ASM inside PLASMA / ASSEMBLY.
    """
    text = str(name or "").strip().upper()
    if not text or text == "ROOT":
        return False
    if "WELDMENT" in text or "ASSEMBLY" in text:
        return True
    if "ASSY" in text:
        return True
    return bool(re.search(r"(?:^|[\s_\-/])ASM(?:$|[\s_\-/.,])", text))


def filelist_row_is_leaf_noun(name: str | None) -> bool:
    """Cad plate/gusset/mount/flat or Linear tube/channel — not an assembly title."""
    if is_nested_assembly_name(name):
        return False
    text = f" {str(name or '').upper()} "
    if re.search(r"\b(PLATE|GUSSET|SHEET)\b", text):
        return True
    if re.search(r"\bFLAT\b", text) and not re.search(r"\bFLAT\s+BAR\b", text):
        return True
    if re.search(r"\bMOUNT\b", text) and not re.search(
        r"\b(CHANNEL|TUBE|PIPE|BARS?|ANGLE|BEAM|HSS)\b", text
    ):
        return True
    if re.search(
        r"\b(TUBE|CHANNEL|PIPE|ANGLE|BEAM|HSS|BARS?)\b", text
    ):
        return True
    return False


_UNNAMED_STEP_NODE_RE = re.compile(r"^-?\d{3,}$")


def is_unnamed_step_node(name: str | None) -> bool:
    """Empty Name or ``-28656`` STEP node — not a leaf Cad/Linear noun."""
    text = str(name or "").strip()
    if not text:
        return True
    if text.casefold() == "root":
        return False
    return bool(_UNNAMED_STEP_NODE_RE.fullmatch(text))


def _row_field_ci(row: dict[str, Any], *names: str) -> str:
    """Read a FileList id field; accept Pascal/camel case. Skip empty GUID."""
    lower = {str(k).casefold(): v for k, v in row.items()}
    for name in names:
        raw = row.get(name)
        if raw in (None, ""):
            raw = lower.get(name.casefold())
        val = str(raw or "").strip()
        if not val or val.casefold() == EMPTY_GUID.casefold():
            continue
        return val
    return ""


def filelist_row_id_fields(row: dict[str, Any] | None) -> dict[str, str]:
    """SourceDataID / ID / FileID on a FileList row (any case)."""
    if not isinstance(row, dict):
        return {"SourceDataID": "", "ID": "", "FileID": ""}
    return {
        "SourceDataID": _row_field_ci(row, "SourceDataID"),
        "ID": _row_field_ci(row, "ID", "ItemID"),
        "FileID": _row_field_ci(row, "FileID"),
    }


def filelist_id_fields_present(rows: list[dict[str, Any]] | None) -> str:
    """Capture note: how many rows have each id field. Not token values."""
    src = ident = file_id = 0
    for row in rows or []:
        if not isinstance(row, dict) or is_cadimport_root_row(row):
            continue
        fields = filelist_row_id_fields(row)
        if fields["SourceDataID"]:
            src += 1
        if fields["ID"]:
            ident += 1
        if fields["FileID"]:
            file_id += 1
    return f"SourceDataID:{src},ID:{ident},FileID:{file_id}"


def filelist_row_explode_id(
    row: dict[str, Any] | None,
    *,
    used_ids: set[str] | None = None,
) -> str:
    """DoCreateDXFParts IDList value for this row.

    Prefer unused SourceDataID (28110-2 unique kids). When SourceDataID is
    the pass-1 upload id (live 107877-1 shared parent), use unused ID/FileID.
    """
    used = {str(x) for x in (used_ids or set()) if str(x).strip()}
    fields = filelist_row_id_fields(row)
    for key in ("SourceDataID", "ID", "FileID"):
        val = fields.get(key) or ""
        if val and val not in used:
            return val
    return ""


def overlay_filelist_ids(
    rows: list[dict[str, Any]] | None,
    grid_rows: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Copy ID/FileID/SourceDataID from bound #gridDXFParts onto name-only rows."""
    from collections import defaultdict

    pool: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for grid in grid_rows or []:
        if not isinstance(grid, dict):
            continue
        if not any(filelist_row_id_fields(grid).values()):
            continue
        pool[filelist_row_display_name(grid)].append(grid)
    taken: set[int] = set()
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        merged = dict(row)
        fields = filelist_row_id_fields(merged)
        if not fields["ID"] or not fields["FileID"]:
            name = filelist_row_display_name(merged)
            for donor in pool.get(name) or []:
                did = id(donor)
                if did in taken:
                    continue
                taken.add(did)
                donor_fields = filelist_row_id_fields(donor)
                for key, val in donor_fields.items():
                    if val and not filelist_row_id_fields(merged).get(key):
                        merged[key] = val
                break
        out.append(merged)
    return out


def is_nested_assembly_row(
    row: dict[str, Any] | None,
    *,
    part_key: str = "",
    cad_filename: str = "",
) -> bool:
    """FileList row to re-explode: *ASSY* / *ASM* / *WELDMENT* / unnamed -NNNN.

    Live 1020249-1: kids named the job PN are unnamed leaf solids, not nests.
    Live BB2000-ASM: job-PN ``BB2000-ASM`` leaves are not nests even though
    the name ends in ``-ASM``. Re-explode ``BB1000-ASM`` / ``BB1010-ASM``.
    Do not match ``normalize(name)==part_key``.
    """
    if not isinstance(row, dict):
        return False
    if is_cadimport_root_row(row):
        return False
    if is_raw_step_upload_row(row, part_key=part_key, cad_filename=cad_filename):
        return False
    name = filelist_row_display_name(row)
    from .item_desc import normalize_part_token

    if part_key and normalize_part_token(name) == normalize_part_token(part_key):
        return False
    return is_nested_assembly_name(name) or is_unnamed_step_node(name)


def filelist_leaf_noun_names(
    rows: list[dict[str, Any]] | None,
    *,
    part_key: str = "",
    cad_filename: str = "",
) -> list[str]:
    """Kid display names that are Cad/Linear nouns (not Root / raw STEP / ASSY)."""
    names: list[str] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if is_cadimport_root_row(row):
            continue
        if is_raw_step_upload_row(
            row, part_key=part_key, cad_filename=cad_filename
        ):
            continue
        name = filelist_row_display_name(row)
        if filelist_row_is_leaf_noun(name):
            names.append(name)
    return names


def filelist_is_assembly_only(
    rows: list[dict[str, Any]] | None,
    *,
    part_key: str = "",
    cad_filename: str = "",
) -> bool:
    """True when kids are only *ASSY*/*WELDMENT*/*-NNNN* (need another explode).

    Live 107877-1: unnamed ``-28656`` + GATE/REST WELDMENT is assembly-only.
    Live 1020249-1: 14× job-PN leaves are not assembly-only — Finish them.
    """
    kids = finish_filelist_kids(
        rows, part_key=part_key, cad_filename=cad_filename
    )
    if not kids:
        return False
    if filelist_leaf_noun_names(
        kids, part_key=part_key, cad_filename=cad_filename
    ):
        return False
    return any(
        is_nested_assembly_row(
            row, part_key=part_key, cad_filename=cad_filename
        )
        for row in kids
    )


def filelist_has_nested_titles(
    rows: list[dict[str, Any]] | None,
    *,
    part_key: str = "",
    cad_filename: str = "",
) -> bool:
    """True when names say GATE WELDMENT / ASSY / unnamed -NNNN (parse check)."""
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if is_nested_assembly_row(
            row, part_key=part_key, cad_filename=cad_filename
        ):
            return True
    return False


def nested_assembly_id_list(
    rows: list[dict[str, Any]] | None,
    *,
    part_key: str = "",
    cad_filename: str = "",
    used_ids: set[str] | None = None,
) -> list[tuple[str, str]]:
    """Unused SourceDataID/ID/FileID + units for nested FileList rows."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    used = {str(x) for x in (used_ids or set()) if str(x).strip()}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if not is_nested_assembly_row(
            row, part_key=part_key, cad_filename=cad_filename
        ):
            continue
        sid = filelist_row_explode_id(row, used_ids=used)
        if not sid or sid in seen:
            continue
        seen.add(sid)
        units = (
            str(row.get("Units") or row.get("Length_Units") or "inch").strip()
            or "inch"
        )
        out.append((sid, units))
    return out


def build_dxf_finish_payload(
    quote_id: str,
    file_list: list[dict[str, Any]],
    *,
    item_id: str | None = None,
    customer_material: bool = False,
) -> dict[str, Any]:
    """POST /Quote/AddItem_DXFFiles body from the QuoteOrderEdit JS contract."""
    rows = [slim_filelist_row(r) for r in filter_finish_filelist(file_list)]
    return {
        "ID": quote_id,
        "ItemID": item_id or EMPTY_GUID,
        "customerMaterial": bool(customer_material),
        "FileList": rows,
    }


# GetPDFData() row keys from QuoteOrderEdit OnAddPDFClick, plus Status
# (grid filter Status>0) so New Line Item actually commits.
# Live /bundles/QuoteOrderEdit: GetPDFData copies these from the
# #gridPDF dataItem when Status>0. ProductID is on FileList (same as
# the bag field). HasSelectedProductID / ProductName / NumberOfContours
# / NumberOfPierces / CuttingLength / BadgeString are omitted.
PDF_GETDATA_FIELDS = (
    "Status",
    "ItemType",
    "ItemID",
    "FileID",
    "SourceDataID",
    "ImageID",
    "FileName",
    "RevisionNumber",
    "Description",
    "PageNumber",
    "PartName",
    "Machine",
    "Memo",
    "Material",
    "Thickness",
    "Thickness_Units",
    "Location",
    "ProcessLocation",
    "Qty",
    "FixedCost",
    "FixedPrice",
    "HasFixedPrice",
    "CustomerMaterial",
    "Grain",
    "Outsource",
    "OutsourceMargin",
    "MaterialCost",
    "MaterialCost_Units",
    "VendorID",
    "VendorName",
    "WeightBorder",
    "WeightBorder_Units",
    "NumberOfHeads",
    "Length",
    "Length_Units",
    "Width",
    "Width_Units",
    "OutsideArea",
    "OutsideArea_Units",
    "OutsidePerimeter",
    "OutsidePerimeter_Units",
    "OutsidePerimeter_UseLocal",
    "Weight",
    "Weight_Units",
    "Weight_UseLocal",
    "TrueWeight",
    "TrueWeight_Units",
    "InternalData",
    "ProductID",
    "ProductType",
    "ProductSubType",
    "Dim1",
    "Dim1_Units",
    "Dim2",
    "Dim2_Units",
    "Dim3",
    "Dim3_Units",
    "Dim4",
    "Dim4_Units",
    "WeightLength",
    "WeightLength_Units",
    "LinearMaterialCost",
    "LinearMaterialCost_Units",
    "LinearMachine",
    "LinearTrimLeft",
    "LinearLeftMiterAngle",
    "LinearTrimRight",
    "LinearRightMiterAngle",
    "PriceListID",
    "PriceListItemID",
    "MarginMarkup",
)

# QuoteOrderEdit PDFGetData() feature form — not GetPDFData FileList.
# AddNewPDFFeature success: i.InternalData = JSON.stringify(PDFGetData()).
PDFGETDATA_FEATURE_KEYS = (
    "ID",
    "Type",
    "Quantity",
    "Dim1",
    "Dim1_Units",
    "Dim2",
    "Dim2_Units",
)

QUOTE_ORDER_EDIT_GETPDFDATA: dict[str, Any] = {
    "is_xhr": False,
    "walks": "tbody dataItem",
    "keeps": "Status>0",
    "copies_productid_from_dataitem": True,
    "omits": (
        "Status",
        "HasSelectedProductID",
        "ProductName",
        "NumberOfContours",
        "NumberOfPierces",
        "CuttingLength",
        "CuttingLengthDisp",
        "ProductionReady",
        "Tag",
        "BadgeString",
    ),
    "contours_not_a_bag_key": True,
    "hasselectedproductid_not_a_bag_key": True,
    "productname_not_a_bag_key": True,
    "cuttinglengthdisp_display_only": True,
    "status_is_filter_only": True,
}

QUOTE_ORDER_EDIT_PDF_FINISH_HYPOTHESES: dict[str, str] = {
    "1_productid_getpdfdata_vs_bag": "falsified_getpdfdata_copies_productid",
    "2_hasselectedproductid_productname": "falsified_not_getpdfdata_fields",
    "3_contours_pierces_after_hole": "named_miss_internaldata_n1_not_gold_1_1",
    "4_machine_laser_vs_bay1": "falsified_leftover_already_laser_bay1",
    "5_finish_success_list": "badge_ocl_unitcost_and_datapdf_contours",
}

# QuoteOrderEdit UpdatePerimeterWeight / onInternalDataChange (2026-09-07
# /bundles/QuoteOrderEdit 353603 bytes). NumberOfContours is 0 hits.
# Live 1020250-1: ProductID + Dim1 5.375 + InternalData + OP/Weight still
# Contours=0 / empty BadgeString. Last GetPerimeterAndWeight must post
# Internal: PDFGetData() (Dim1 filled) and #length/#width form fields.
# onInternalDataChange does that via UpdatePerimeterWeight(true, false).
# Nest / Renest_BestSheet is later. Do not invent Contours FileList keys.
QUOTE_ORDER_EDIT_UPW_INTERNAL: dict[str, Any] = {
    "xhr": "POST /Quote/GetPerimeterAndWeight",
    "reads_form": ("#length", "#width", "#MaterialEdit", "#LoadThickness"),
    "posts_internal": "PDFGetData()",
    "oninternaldatachange_call": "UpdatePerimeterWeight(true, false)",
    "onlengthchangepdf_call": "UpdatePerimeterWeight(true, true)",
    "number_of_contours_bundle_hits": 0,
    "nest_is_later": True,
    "named_miss": "upw_internal_dim1_and_form_lw",
    "form_lw_synced_false_miss": "form_lw_synced_false_after_internal_dim1_upw",
    "finish_filelist_n0_miss": "finish_filelist_n0_after_form_lw_synced_and_op",
    "finish_internaldata_null_miss": (
        "finish_bag_internaldata_null_after_getpdfdata_internal_dim1_n1"
    ),
    "finish_producttype_bar_miss": (
        "finish_producttype_bar_bar_flat_after_plate_productid_and_internaldata_dim1"
    ),
    "finish_prt_pdf_still_contours_zero_miss": (
        "finish_prt_pdf_still_contours_zero_after_internaldata_dim1_and_op"
    ),
    "finish_materialcost_empty_miss": (
        "falsified_empty_materialcost_not_contours_miss"
    ),
    "finish_materialcost_abort_blocked_miss": (
        "empty_materialcost_abort_blocked_finish_catalog_has_no_rate"
    ),
    "finish_list0_data_null_errorcount_miss": (
        "finish_list0_data_none_errorcount_1_vs_gold_datapartpdf_contours"
    ),
    "invent_contours_on_filelist": False,
}

# QuoteOrderEdit leftover-named GetPDFData candidate (33204-1 / 1009213-1):
# ProductType/prt_pdf. Gold imported Cad uses ProductSubType prt_dxf.
# Image Files grid template defaults to bar / bar_flat (live bab8f668).
# Do not leave that linear combo on a Sheets & Plates ProductID.
CAD_IMAGE_FILES_PLATE_PRODUCT_TYPE = "prt_pdf"
CAD_IMAGE_FILES_PLATE_PRODUCT_SUBTYPE = "prt_pdf"
# Gold 14501-1 Cad List[0]: Machine="Laser" Location="Bay1".
# Leftover 97ae3e4f posted Machine="Laser - Bay1" Location=null → Data=None.
CAD_IMAGE_FILES_MACHINE = "Laser"
CAD_IMAGE_FILES_LOCATION = "Bay1"

# OnAddLinearClick body keys. Do not add others.
LINEAR_ADD_FIELDS = (
    "ID",
    "ItemID",
    "productID",
    "productType",
    "productSubType",
    "productConfigID",
    "material",
    "location",
    "dim1",
    "dim1_Unit",
    "dim2",
    "dim2_Unit",
    "dim3",
    "dim3_Unit",
    "dim4",
    "dim4_Unit",
    "weightLength",
    "weightLength_Units",
    "materialCost",
    "materialCost_Units",
    "memo",
    "name",
    "revisionNumber",
    "machine",
    "length",
    "length_unit",
    "qty",
    "fixedPrice",
    "productionReady",
    "customerMaterial",
    "outsource",
    "outsourceCustomerMaterial",
    "outsourceUnitCost",
    "outsourceMargin",
    "vendorID",
    "FileID",
    "ImageID",
    "MiterLeft",
    "MiterLeftAngle1",
    "MiterLeftAngle2",
    "MiterLeftOffset",
    "MiterRight",
    "MiterRightAngle1",
    "MiterRightAngle2",
    "MiterRightOffset",
    "Internal",
    "processLocation",
)


def _pdf_row_status(row: dict[str, Any]) -> float:
    raw = row.get("Status", row.get("status"))
    if raw is None:
        return 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def filter_pdf_filelist(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """GetPDFData(): gridPDF rows with Status>0."""
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if _pdf_row_status(row) <= 0:
            continue
        out.append(dict(row))
    return out


def pdf_finish_from_page_kendo(result: dict[str, Any] | None) -> bool:
    """True only when OnAddPDFClick posted GetPDFData / #gridPDF FileList."""
    if not isinstance(result, dict):
        return False
    if str(result.get("via") or "") != "page_fn":
        return False
    return bool(result.get("filelist_from_kendo"))


def reconstructed_pdf_filelist_is_fail(result: dict[str, Any] | None) -> bool:
    """Reconstructed Image Files FileList is fail-closed even if GET>0.

    Live 1001898-5: HTTP-looking OnAddPDFClick of a Python-built FileList
    filled Cad unitcost without PR / OperationCostList.
    """
    return not pdf_finish_from_page_kendo(result)


PDF_UPLOAD_VIA_PAGE_ADD_FILES = "page_add_files"


def leftover_api_mint_cookie_finish_is_fail(dump: dict[str, Any] | None) -> bool:
    """Live 29340-1: API mint then cookie GetItem_AddView 302 / GET 0."""
    if not isinstance(dump, dict):
        return False
    live = dump.get("live_29340_1") if isinstance(dump.get("live_29340_1"), dict) else {}
    if not live:
        return False
    try:
        if live.get("itemlist_n") is None or int(live.get("itemlist_n")) != 0:
            return False
    except (TypeError, ValueError):
        return False
    if live.get("image_files_ran") is not False:
        return False
    if live.get("api_mint") is not True:
        return False
    if live.get("getitem_addview_302") is not True:
        return False
    if live.get("chrome_signed_in") is not True:
        return False
    if dump.get("cookie_302_is_logout") is not False:
        return False
    return True


def addview_302_after_refresh_is_fail(probe: dict[str, Any] | None) -> bool:
    """Cookie HTTP GetItem_AddView /Quote still 302 after Chrome refresh.

    Fail-closed for cookie-file GET/POST only (live 29340-1). Does not
    block in-page mint when Chrome EDIT is signed in.
    """
    if not isinstance(probe, dict):
        return False
    if probe.get("ok") is True:
        return False
    if probe.get("refreshed") is not True:
        return False
    if probe.get("still_302") is True:
        return True
    return probe.get("ok") is False


def live_quotes_fetch_ok(result: dict[str, Any] | None) -> bool:
    """True only for an in-page GET /Quote that stayed 200 (not Login).

    Leftover EDIT can still paint the amtech footer after AspNet dies
    (live P904272-1). Footer amtech is not a live session.
    """
    if not isinstance(result, dict):
        return False
    try:
        status = int(result.get("status") or 0)
    except (TypeError, ValueError):
        return False
    if status != 200:
        return False
    if result.get("login") is True:
        return False
    url = str(result.get("url") or result.get("location") or "")
    if "Login" in url or "/Account/Login" in url or "AccessDenied" in url:
        return False
    return True


def inpage_mint_allowed(
    *,
    chrome_edit_signed_in: bool,
    chrome_login: bool = False,
    cookie_addview_302: bool = False,
    quotes_fetch_200: bool | None = None,
    chrome_quotes_list_signed_in: bool = False,
) -> bool:
    """In-page mint is not gated on the cookie file (live 34603-2).

    Live Quotes list footer amtech is a mint session even when the
    cookie file or leftover EDIT fetch 302s. Cookie GetItem_AddView 302
    does not block when that list footer is signed in, or when
    chrome_edit_signed_in **and** live Quotes fetch is 200. Leftover
    EDIT amtech footer with a dead AspNet cookie is not a session
    (live P904272-1). Chrome Login page still aborts. Cookie-only path
    (302 + not signed in) is the 29340-1 leftover — do not v1/quote
    then cookie Finish.
    """
    if chrome_quotes_list_signed_in:
        return True
    if chrome_edit_signed_in and quotes_fetch_200 is False:
        return False
    if chrome_edit_signed_in:
        return True
    if chrome_login:
        return False
    if cookie_addview_302:
        return False
    return True


def leftover_gridpdf_fills_only_via_onsuccess(dump: dict[str, Any] | None) -> bool:
    """Leftover dialog: #files kendoUpload + onSuccess_PDFUpload is the only fill."""
    if not isinstance(dump, dict):
        return False
    ku = dump.get("kendoUpload") if isinstance(dump.get("kendoUpload"), dict) else {}
    if str(ku.get("selector") or "") != "#files":
        return False
    if str(ku.get("success") or "") != "onSuccess_PDFUpload":
        return False
    fill = dump.get("onSuccess_PDFUpload")
    if not isinstance(fill, dict) or not fill.get("only_fill"):
        return False
    transport = dump.get("gridPDF_transport")
    read = transport.get("read") if isinstance(transport, dict) else {}
    if not isinstance(read, dict) or str(read.get("url") if read.get("url") is not None else "missing") != "":
        return False
    getpdf = dump.get("GetPDFData") if isinstance(dump.get("GetPDFData"), dict) else {}
    if getpdf.get("is_xhr"):
        return False
    if "tbody" not in str(getpdf.get("walks") or "").casefold():
        return False
    if "Status>0" not in str(getpdf.get("keeps") or ""):
        return False
    return True


def pdf_grid_upload_bound(result: dict[str, Any] | None) -> bool:
    """True when in-page #files kendoUpload filled #gridPDF via onSuccess."""
    if not isinstance(result, dict):
        return False
    if str(result.get("upload_via") or "") != PDF_UPLOAD_VIA_PAGE_ADD_FILES:
        return False
    if not result.get("bound"):
        return False
    if not result.get("files_kendo"):
        return False
    try:
        n = int(result.get("status_gt0_n") or result.get("getpdfdata_n") or result.get("grid_pdf_row_count") or 0)
    except (TypeError, ValueError):
        return False
    return n > 0


def cookie_http_pdf_upload_is_fail(upload_via: str | None) -> bool:
    """Cookie HTTP skips #files kendo / AddNewPDFFeature (live 103535-1)."""
    via = str(upload_via or "").strip()
    return via != PDF_UPLOAD_VIA_PAGE_ADD_FILES


def cookie_http_additem_pdffiles_is_not_success(
    result: dict[str, Any] | None,
) -> bool:
    """Cookie-only AddItem_PDFFiles is not success (live 29340-1 / 103535-1)."""
    return not pdf_finish_from_page_kendo(result)


def empty_gridpdf_after_stamp_is_fail(
    result: dict[str, Any] | None,
    *,
    grid_pdf_row_count: int | None = None,
) -> bool:
    """empty_dataSource / filelist_from_kendo=false after stamp is FAIL."""
    why = ""
    from_kendo = False
    n = grid_pdf_row_count
    if isinstance(result, dict):
        why = str(result.get("finish_why") or "")
        from_kendo = bool(result.get("filelist_from_kendo"))
        if n is None:
            try:
                n = int(result.get("grid_pdf_row_count") or 0)
            except (TypeError, ValueError):
                n = 0
    if why == "empty_dataSource":
        return True
    if not from_kendo:
        return True
    try:
        return int(n or 0) <= 0
    except (TypeError, ValueError):
        return True


def image_files_cookie_http_empty_grid_is_fail(
    *,
    cookie_http_uploads: int,
    stamp_n: int,
    finish_why: str | None,
    filelist_from_kendo: bool,
    cad_n: int,
) -> bool:
    """Live 103535-1: 5 cookie HTTP uploads + 4 stamps + empty grid + GET 0."""
    del stamp_n
    if int(cookie_http_uploads or 0) >= 1:
        return True
    if str(finish_why or "") == "empty_dataSource":
        return True
    if not filelist_from_kendo:
        return True
    return int(cad_n or 0) <= 0


DXF_UPLOAD_VIA_PAGE_ADD_FILES = "page_add_files"


def explode_to_docreate_fills_internaldata(dump: dict[str, Any] | None) -> bool:
    """True only if a cited hunt names a fill XHR. Live 21785-2 dump is False."""
    if not isinstance(dump, dict):
        return False
    if dump.get("classify_finish_internaldata_fill"):
        return True
    create = dump.get("createAllParts")
    if isinstance(create, dict) and create.get("writes_internaldata"):
        return True
    if isinstance(create, dict) and create.get("xhr"):
        return True
    for key in ("SetPartMode", "SetDXFFilePartMode", "Unfold", "DoCreateDXFParts"):
        step = dump.get(key)
        if isinstance(step, dict) and step.get("writes_internaldata"):
            return True
    return False


def leftover_griddxf_fills_only_via_onsuccess(dump: dict[str, Any] | None) -> bool:
    """Leftover CAD Files: #files in #dxfupload_Zone + onSuccess_Upload is the only #gridDXF fill."""
    if not isinstance(dump, dict):
        return False
    ku = dump.get("kendoUpload") if isinstance(dump.get("kendoUpload"), dict) else {}
    if str(ku.get("selector") or "") != "#files":
        return False
    if str(ku.get("zone") or "") != "#dxfupload_Zone":
        return False
    if str(ku.get("success") or "") != "onSuccess_Upload":
        return False
    if str(ku.get("complete") or "") != "onComplete_Upload":
        return False
    if str(ku.get("upload") or "") != "onUpload_DXFUpload":
        return False
    async_opt = ku.get("async") if isinstance(ku.get("async"), dict) else {}
    if str(async_opt.get("saveUrl") or "") != "/CadImport/UploadItem_DXFFiles":
        return False
    fill = dump.get("onSuccess_Upload")
    if not isinstance(fill, dict) or not fill.get("only_fill"):
        return False
    adds = str(fill.get("adds") or "")
    if "#gridDXF" not in adds:
        return False
    if str(fill.get("not_grid") or "") != "#gridDXFParts":
        return False
    if fill.get("writes_gridDXFParts_internaldata") is not False:
        return False
    if fill.get("writes_gridDXFParts_cuttinglength") is not False:
        return False
    getdxf = dump.get("GetDXFData") if isinstance(dump.get("GetDXFData"), dict) else {}
    if getdxf.get("exists") is not False:
        return False
    nxt = dump.get("Next") if isinstance(dump.get("Next"), dict) else {}
    if str(nxt.get("caller") or "") != "createAllParts":
        return False
    if str(nxt.get("function") or "") != "DoCreateDXFParts":
        return False
    if str(nxt.get("path") or "") != "/part/create":
        return False
    if nxt.get("cookie_http_part_create_is_gold") is not False:
        return False
    onadd = dump.get("OnAddDXFClick") if isinstance(dump.get("OnAddDXFClick"), dict) else {}
    if "gridDXFParts" not in str(onadd.get("walks") or ""):
        return False
    if onadd.get("fills_internaldata") is not False:
        return False
    return leftover_getperimeter_is_gridpdf_only(dump)


def leftover_getperimeter_is_gridpdf_only(dump: dict[str, Any] | None) -> bool:
    """GetPerimeterAndWeight remains #gridPDF only — not CAD Files InternalData."""
    if not isinstance(dump, dict):
        return False
    gp = dump.get("GetPerimeterAndWeight")
    if not isinstance(gp, dict):
        return False
    if str(gp.get("targets") or "") != "gridPDF":
        return False
    return gp.get("fills_dxf_internaldata") is False


def dxf_grid_upload_bound(result: dict[str, Any] | None) -> bool:
    """True when in-page #files kendoUpload filled #gridDXF via onSuccess_Upload."""
    if not isinstance(result, dict):
        return False
    if str(result.get("upload_via") or "") != DXF_UPLOAD_VIA_PAGE_ADD_FILES:
        return False
    if not result.get("bound"):
        return False
    if not result.get("files_kendo"):
        return False
    try:
        n = int(result.get("gridDXF_n") or result.get("grid_dxf_row_count") or 0)
    except (TypeError, ValueError):
        return False
    return n > 0


def cookie_http_dxf_upload_is_fail(upload_via: str | None) -> bool:
    """Cookie HTTP UploadItem_DXFFiles does not bind #gridDXF (live EHB3112-1)."""
    via = str(upload_via or "").strip()
    return via != DXF_UPLOAD_VIA_PAGE_ADD_FILES


def leftover_cookie_http_dxf_empty_grid_is_fail(
    *,
    cookie_http_uploads: int,
    gridDXF_n: int,
    finish_posted: bool,
    cad_n: int,
) -> bool:
    """Live EHB3112-1: cookie HTTP upload + empty #gridDXF + GET 0."""
    if int(cookie_http_uploads or 0) >= 1:
        return True
    if bool(finish_posted):
        return int(cad_n or 0) <= 0
    return int(gridDXF_n or 0) <= 0 or int(cad_n or 0) <= 0


def leftover_dxf_pack_is_on_additem_list(dump: dict[str, Any] | None) -> bool:
    """21678-1 UI analog only. GetPerimeterAndWeight is #gridPDF — not CAD pack."""
    if not isinstance(dump, dict):
        return False
    if dump.get("pack_xhr_named") is not False:
        return False
    if dump.get("addrow_stamps_pr") is not False:
        return False
    if not dump.get("pack_already_on_additem_list"):
        return False
    xhr = dump.get("UpdatePerimeterWeight")
    if not isinstance(xhr, dict):
        return False
    if "/Quote/GetPerimeterAndWeight" not in str(xhr.get("xhr") or ""):
        return False
    if str(xhr.get("when") or "") != "change_before_AddItem":
        return False
    on = {str(k) for k in (xhr.get("on") or ())}
    if "Stock_X" not in on or "Stock_Y" not in on:
        return False
    nxt = dump.get("UpdateDataNext") if isinstance(dump.get("UpdateDataNext"), dict) else {}
    if nxt.get("gold") is not False:
        return False
    return True


def empty_dxf_stock_perimeter_is_fail(result: dict[str, Any] | None) -> bool:
    """Empty CuttingLength / perimeter / InternalData after Stock type is FAIL.

    Only when the stamp actually typed rows (``stamped>0`` or the
    GetPerimeterAndWeight XHR). Chrome-gate empty (stamped=0) falls through
    to the explode-empty check so unit tests without a box tab still Finish.
    """
    if not isinstance(result, dict):
        return False
    keys = ("outside_perimeter_n", "cutting_length_n", "internaldata_n")
    if not any(k in result for k in keys):
        return False
    try:
        stamped = int(result.get("stamped") or 0)
    except (TypeError, ValueError):
        stamped = 0
    if stamped <= 0 and not result.get("getperimeter_xhr"):
        return False
    counts: list[int] = []
    for key in keys:
        if key not in result:
            continue
        try:
            counts.append(int(result.get(key) or 0))
        except (TypeError, ValueError):
            counts.append(0)
    return bool(counts) and all(n <= 0 for n in counts)


def dxf_stock_perimeter_filled(result: dict[str, Any] | None) -> bool:
    """True when Stock type + GetPerimeterAndWeight filled kendo before Finish."""
    if not isinstance(result, dict):
        return False
    for key in ("outside_perimeter_n", "cutting_length_n", "internaldata_n"):
        try:
            if int(result.get(key) or 0) > 0:
                return True
        except (TypeError, ValueError):
            continue
    return False


def v1_quote_itemlist_post_wipes_gold(body: dict[str, Any] | None) -> bool:
    """POST v1/quote with ItemList wipes a website PR/laser stamp."""
    return isinstance(body, dict) and "ItemList" in body


def v1_quote_body_without_itemlist(detail: dict[str, Any] | None) -> dict[str, Any]:
    """Header/imperial POST must not resend ItemList after a gold stamp."""
    out = dict(detail or {})
    out.pop("ItemList", None)
    return out


def leftover_cad_pack_is_on_additem_list(dump: dict[str, Any] | None) -> bool:
    """Pack is on AddItem_PDFFiles List. AddRow only copies. No later XHR."""
    if not isinstance(dump, dict):
        return False
    if dump.get("pack_xhr_named") is not False:
        return False
    if dump.get("addrow_stamps_pr") is not False:
        return False
    if not dump.get("pack_already_on_additem_list"):
        return False
    xhr = dump.get("UpdatePerimeterWeight")
    if not isinstance(xhr, dict):
        return False
    if "/Quote/GetPerimeterAndWeight" not in str(xhr.get("xhr") or ""):
        return False
    if str(xhr.get("when") or "") != "change_before_AddItem":
        return False
    getpdf = dump.get("GetPDFData") if isinstance(dump.get("GetPDFData"), dict) else {}
    posts = {str(k) for k in (getpdf.get("posts") or ())}
    if "OutsidePerimeter" not in posts:
        return False
    omits = {str(k) for k in (getpdf.get("omits") or ())}
    if "Status" not in omits or "CuttingLength" not in omits:
        return False
    return True


def leftover_perimeter_xhr_is_not_gold_pack(dump: dict[str, Any] | None) -> bool:
    """Live 1002323-1: UpdatePerimeterWeight(true,true) is not the gold pack."""
    if not isinstance(dump, dict):
        return False
    xhr = dump.get("UpdatePerimeterWeight")
    if not isinstance(xhr, dict):
        return False
    if xhr.get("is_gold_pack") is not False:
        return False
    if xhr.get("bare_does_not_copy") is not True:
        return False
    call = str(xhr.get("call") or "").replace(" ", "")
    if "true,true" not in call:
        return False
    if "/Quote/GetPerimeterAndWeight" not in str(xhr.get("xhr") or ""):
        return False
    getpdf = dump.get("GetPDFData") if isinstance(dump.get("GetPDFData"), dict) else {}
    omits = {str(k) for k in (getpdf.get("omits") or ())}
    if "CuttingLength" not in omits:
        return False
    if getpdf.get("cuttinglengthdisp_display_only") is not True:
        return False
    live = dump.get("live_1002323_1") if isinstance(dump.get("live_1002323_1"), dict) else {}
    if not live:
        return False
    try:
        perim = float(live.get("outside_perimeter") or 0)
        cut = float(live.get("cutting_length") or 0)
    except (TypeError, ValueError):
        return False
    if perim <= 0 or cut > 0:
        return False
    if str(live.get("tag") or "") != "":
        return False
    if list(live.get("operation_cost_list") or []):
        return False
    nxt = dump.get("UpdateDataNext") if isinstance(dump.get("UpdateDataNext"), dict) else {}
    if nxt.get("gold") is not False:
        return False
    return True


def empty_internaldata_after_perimeter_is_fail(result: dict[str, Any] | None) -> bool:
    """Empty InternalData after a landed perimeter is not an Image Files fail.

    Kyle Loom: Add Feature Hole only when the drawing has holes. A no-hole
    rectangle still gets PR + laser pack. Live 1002323-1 leftover had
    InternalData '' with OutsidePerimeter 44.64 — that skip was wrong for
    PDF. STEP explode skip-when-InternalData-empty stays on CadImport.
    ``result`` is unused; kept so callers do not invent a new gate.
    """
    del result
    return False


GETPDFDATA_BAG_COMPARE_KEYS = (
    "Machine",
    "ProductID",
    "Qty",
    "Weight",
    "Weight_UseLocal",
    "OutsidePerimeter",
    "OutsidePerimeter_UseLocal",
    "NumberOfHeads",
    "WeightBorder",
    "Material",
    "Thickness",
    "Length",
    "Width",
    "InternalData",
    "ProductType",
    "ProductSubType",
    "OutsideArea",
    "TrueWeight",
    "MaterialCost",
    "MaterialCost_Units",
    "Description",
)


def leftover_weight_is_getpdfdata_bag_not_cuttinglength(
    dump: dict[str, Any] | None,
) -> bool:
    """Pack is not post CuttingLength. Weight is already in the GetPDFData bag.

    Live 1002323-1 FileList keys/values were not logged. GetPDFData omits
    CuttingLength. ``#CuttingLength`` / dataItem.CuttingLength is not
    posted. HasSelectedProductID is not a bag key. Do not invent
    CuttingLength on FileList. Do not graft.
    """
    if not isinstance(dump, dict):
        return False
    getpdf = dump.get("GetPDFData") if isinstance(dump.get("GetPDFData"), dict) else {}
    omits = {str(k) for k in (getpdf.get("omits") or ())}
    posts = {str(k) for k in (getpdf.get("posts") or ())}
    if "CuttingLength" not in omits:
        return False
    if getpdf.get("cuttinglengthdisp_display_only") is not True:
        return False
    if dump.get("filelist_keys_logged") is not False:
        return False
    wt = dump.get("Weight") if isinstance(dump.get("Weight"), dict) else {}
    if str(wt.get("bag_field") or "") != "Weight":
        return False
    if wt.get("invent_getpdfdata_key") is not False:
        return False
    if "Weight" not in PDF_GETDATA_FIELDS or "Weight_UseLocal" not in PDF_GETDATA_FIELDS:
        return False
    if "CuttingLength" in PDF_GETDATA_FIELDS:
        return False
    if "HasSelectedProductID" in PDF_GETDATA_FIELDS:
        return False
    if "HasSelectedProductID" in posts:
        return False
    xhr = dump.get("UpdatePerimeterWeight")
    if not isinstance(xhr, dict):
        return False
    result = xhr.get("result") if isinstance(xhr.get("result"), dict) else {}
    try:
        if float(result.get("Weight") or 0) <= 0:
            return False
    except (TypeError, ValueError):
        return False
    return True


def filelist_bag_snapshot(row: dict[str, Any] | None) -> dict[str, Any]:
    """Posted GetPDFData bag candidates — names/values, no tokens."""
    if not isinstance(row, dict):
        return {}
    out: dict[str, Any] = {}
    for key in GETPDFDATA_BAG_COMPARE_KEYS:
        if key in row:
            out[key] = row[key]
    return out


def leftover_empty_bind_productid_skip_is_wrong(dump: dict[str, Any] | None) -> bool:
    """21681-1: bind ProductID null + 316 Polished default + Finish skipped.

    Upload List ProductID is always null on Image Files PDFs. keepPid
    never has anything to restore. Fail-closing Finish on empty bind
    ProductID blocked L×W and taught nothing. Empty ProductID is the
    Image Files default, not a skip.
    """
    if not isinstance(dump, dict):
        return False
    if dump.get("finish_skipped") is not True:
        return False
    if str(dump.get("skip_reason") or "") != "empty_bind_productid":
        return False
    live = dump.get("live_21681_1") if isinstance(dump.get("live_21681_1"), dict) else {}
    if not live:
        return False
    try:
        pid_n = live.get("bind_productid_n")
        if pid_n is None or int(pid_n) != 0:
            return False
        if abs(float(live.get("upload_thickness") or 0) - 0.0178) > 1e-6:
            return False
    except (TypeError, ValueError):
        return False
    if str(live.get("upload_material") or "") != "316 Polished":
        return False
    if live.get("stamped") is not False:
        return False
    if str(live.get("drawing_material") or "") == "":
        return False
    return True


def leftover_plate_modal_is_not_the_pack(dump: dict[str, Any] | None) -> bool:
    """1009213-1: modal SKU + FileList ProductID null + list0_pack empty.

    ``#gridSelectProductPlate`` apply/select vs search-only. Modal is
    not gold. GET ProductID is not the pack. Do not skip Finish.
    """
    if not isinstance(dump, dict):
        return False
    if dump.get("modal_driven") is not True:
        return False
    bag = dump.get("filelist_bag") if isinstance(dump.get("filelist_bag"), dict) else {}
    if bag.get("ProductID") not in (None, "", "null"):
        return False
    pack = dump.get("list0_pack") if isinstance(dump.get("list0_pack"), dict) else {}
    if not pack:
        return False
    if str(pack.get("badge_string") or "") != "":
        return False
    try:
        if int(pack.get("ocl_n") or 0) != 0:
            return False
        if float(pack.get("unit_cost") or 0) <= 0:
            return False
    except (TypeError, ValueError):
        return False
    getpdf = dump.get("GetPDFData") if isinstance(dump.get("GetPDFData"), dict) else {}
    if "CuttingLength" not in {str(k) for k in (getpdf.get("omits") or ())}:
        return False
    live = dump.get("live_1009213_1") if isinstance(dump.get("live_1009213_1"), dict) else {}
    if not live:
        return False
    if str(live.get("sku") or "") == "":
        return False
    if live.get("modal_is_gold") is not False:
        return False
    if live.get("pack_is_productid") is not False:
        return False
    if live.get("list0_pack_is_gold") is not False:
        return False
    return True


def leftover_getpdfdata_values_named_not_invented(
    dump: dict[str, Any] | None,
) -> bool:
    """1009213-1: name leftover GetPDFData values; do not invent keys/CuttingLength."""
    if not isinstance(dump, dict):
        return False
    want = {
        "ProductionReady checkbox",
        "ItemType",
        "ProductType/prt_pdf",
        "FileID/ImageID present",
        "InternalData empty vs rectangle",
        "Machine string exact",
    }
    named = dump.get("getpdfdata_values_named")
    if not isinstance(named, (list, tuple)):
        return False
    if set(named) != want:
        return False
    if dump.get("invent_cuttinglength") is not False:
        return False
    getpdf = dump.get("GetPDFData") if isinstance(dump.get("GetPDFData"), dict) else {}
    if "CuttingLength" not in {str(k) for k in (getpdf.get("omits") or ())}:
        return False
    live = dump.get("live_1009213_1") if isinstance(dump.get("live_1009213_1"), dict) else {}
    return bool(live)


def plate_modal_without_filelist_productid_is_fail(
    stamp_out: dict[str, Any] | None,
    result: dict[str, Any] | None,
) -> bool:
    """Modal driven + FileList ProductID null + list0_pack empty (1009213-1)."""
    if not isinstance(stamp_out, dict) or not isinstance(result, dict):
        return False
    via = str(stamp_out.get("picker_via") or "").lower()
    if "gridselectproductplate" not in via:
        return False
    bag = result.get("filelist_bag") if isinstance(result.get("filelist_bag"), dict) else {}
    if bag.get("ProductID") not in (None, "", "null"):
        return False
    return list0_pack_without_tag_ocl_is_fail(result)


def leftover_thick_plate_cad_laser_is_wrong(dump: dict[str, Any] | None) -> bool:
    """1009213-1: 1.25 in plate was Cad-lasered; must be Component."""
    if not isinstance(dump, dict):
        return False
    live = dump.get("live_1009213_1") if isinstance(dump.get("live_1009213_1"), dict) else {}
    if not live:
        return False
    try:
        if abs(float(live.get("thickness") or 0) - 1.25) > 1e-6:
            return False
    except (TypeError, ValueError):
        return False
    if str(live.get("should_be") or "") != "Component":
        return False
    if str(live.get("was") or "") != "Cad":
        return False
    return True


def leftover_addnewpdffeature_skipped_is_named_miss(
    dump: dict[str, Any] | None,
) -> bool:
    """1009213-1: page AddNewPDFFeature(feature, cad) did not run."""
    if not isinstance(dump, dict):
        return False
    live = dump.get("live_1009213_1") if isinstance(dump.get("live_1009213_1"), dict) else {}
    if not live:
        return False
    if live.get("addnewpdffeature") is not False:
        return False
    if live.get("invent_internaldata") is not False:
        return False
    if live.get("cookie_addfeature") is not False:
        return False
    feat = dump.get("AddNewPDFFeature") if isinstance(dump.get("AddNewPDFFeature"), dict) else {}
    if feat.get("no_arg_not_gold") is not True:
        return False
    return True


def leftover_list0_pack_is_not_gold(dump: dict[str, Any] | None) -> bool:
    """33204-1: AddItem_PDFFiles response List[0] has no pack.

    Full L×W / Weight / OP / Machine / Material bag still FAIL when
    list0_pack BadgeString empty / OCL 0 / UnitCost 5.05. Gold Tag
    is empty — not a fail. Pack is BadgeString + CalculatorNames.
    GET ProductID is not the pack. Do not add CuttingLength.
    """
    if not isinstance(dump, dict):
        return False
    pack = dump.get("list0_pack") if isinstance(dump.get("list0_pack"), dict) else {}
    if not pack:
        return False
    if str(pack.get("badge_string") or "") != "":
        return False
    if pack.get("production_ready") is not False:
        return False
    try:
        if int(pack.get("list_n") or 0) < 1:
            return False
        if int(pack.get("ocl_n") or 0) != 0:
            return False
        if abs(float(pack.get("unit_cost") or 0) - 5.05) > 1e-6:
            return False
    except (TypeError, ValueError):
        return False
    bag = dump.get("filelist_bag") if isinstance(dump.get("filelist_bag"), dict) else {}
    if not bag:
        return False
    if bag.get("ProductID") not in (None, "", "null"):
        return False
    try:
        if float(bag.get("Weight") or 0) <= 0:
            return False
        if float(bag.get("OutsidePerimeter") or 0) <= 0:
            return False
        if float(bag.get("Length") or 0) <= 0:
            return False
        if float(bag.get("Width") or 0) <= 0:
            return False
    except (TypeError, ValueError):
        return False
    if str(bag.get("Machine") or "") == "":
        return False
    if str(bag.get("Material") or "") == "":
        return False
    if str(bag.get("Thickness") or "") == "":
        return False
    getpdf = dump.get("GetPDFData") if isinstance(dump.get("GetPDFData"), dict) else {}
    if "CuttingLength" not in {str(k) for k in (getpdf.get("omits") or ())}:
        return False
    live = dump.get("live_33204_1") if isinstance(dump.get("live_33204_1"), dict) else {}
    if not live:
        return False
    if str(live.get("tag") or "") != "":
        return False
    if list(live.get("operation_cost_list") or []):
        return False
    if live.get("list0_pack_is_gold") is not False:
        return False
    if live.get("pack_is_productid") is not False:
        return False
    return True


def leftover_getpdfdata_candidates_named_not_invented(
    dump: dict[str, Any] | None,
) -> bool:
    """33204-1: name leftover bag candidates; do not invent CuttingLength."""
    if not isinstance(dump, dict):
        return False
    want = {
        "ProductionReady checkbox",
        "ItemType",
        "ProductType/prt_pdf",
        "FileID/ImageID from upload",
        "InternalData rectangle vs empty",
        "Machine string vs Laser - Bay 1",
    }
    cands = dump.get("getpdfdata_candidates_to_verify")
    if not isinstance(cands, (list, tuple)):
        return False
    if set(cands) != want:
        return False
    if dump.get("invent_cuttinglength") is not False:
        return False
    getpdf = dump.get("GetPDFData") if isinstance(dump.get("GetPDFData"), dict) else {}
    if "CuttingLength" not in {str(k) for k in (getpdf.get("omits") or ())}:
        return False
    return True


GOLD_LASER_CALCULATOR_NAMES = (
    "Laser",
    "Drafting",
    "Laser-Setup",
    "Sheet Loading",
    "Deburr",
)


def list0_pack_without_tag_ocl_is_fail(result: dict[str, Any] | None) -> bool:
    """BadgeString empty / OCL 0 is FAIL. Gold Tag is empty — not a fail.

    Live GET 1001898-1 first Cad: Tag "" / ProductionReady false /
    BadgeString PR + laser CalculatorNames + UnitCost > UnitWeightCost.
    Only when the Finish capture names ``response_badge_string`` and
    ``response_ocl_n``. Tag-only captures do not fail.
    """
    if not isinstance(result, dict):
        return False
    if "response_badge_string" not in result or "response_ocl_n" not in result:
        return False
    if str(result.get("response_badge_string") or "") != "":
        return False
    try:
        if int(result.get("response_ocl_n") or 0) != 0:
            return False
    except (TypeError, ValueError):
        return False
    return True


def list0_pack_badge_ocl_is_gold(result: dict[str, Any] | None) -> bool:
    """PASS: BadgeString PR + Laser/Drafting/Laser-Setup/Sheet Loading/Deburr
    + UnitCost > UnitWeightCost. Not Tag. Not ProductionReady.
    """
    if not isinstance(result, dict):
        return False
    if str(result.get("response_badge_string") or "") != "PR":
        return False
    names = result.get("response_ocl_names")
    if not isinstance(names, (list, tuple)):
        return False
    have = {str(n).strip().lower() for n in names if str(n).strip()}
    want = {n.lower() for n in GOLD_LASER_CALCULATOR_NAMES}
    if not want <= have:
        return False
    try:
        uc = float(result.get("response_unit_cost") or 0)
        uwc = float(result.get("response_unit_weight_cost") or 0)
    except (TypeError, ValueError):
        return False
    return uc > uwc


def list0_pack_badge_ocl_contours_is_gold(result: dict[str, Any] | None) -> bool:
    """Gold 14501-1: list0_pack + DataPartPDF NumberOfContours/Pierces >= 1.

    Leftover Cad misses with a full L×W bag still had 0/0. Pack is not
    those FileList keys — GetPDFData omits NumberOfContours/Pierces.
    """
    if not list0_pack_badge_ocl_is_gold(result):
        return False
    try:
        if int(result.get("response_number_of_contours") or 0) < 1:
            return False
        if int(result.get("response_number_of_pierces") or 0) < 1:
            return False
    except (TypeError, ValueError):
        return False
    return True


GOLD_SAW_CALCULATOR_NAMES = (
    "Saw",
    "Saw-Setup",
)

GOLD_WELD_CALCULATOR_NAMES = (
    "Weld-Time",
    "Weld-Fitting",
    "Weld-Setup",
)


def _ocl_names_have_saw_pack(names: Any) -> bool:
    """True when CalculatorNames include Saw and Saw-Setup / Saw Setup."""
    if not isinstance(names, (list, tuple)):
        return False
    have = {str(n).strip().lower() for n in names if str(n).strip()}
    has_saw = any(n == "saw" or (n.startswith("saw") and "setup" not in n) for n in have)
    has_setup = any("saw" in n and "setup" in n for n in have)
    return has_saw and has_setup


def linear_finish_from_page_fn(result: dict[str, Any] | None) -> bool:
    """True only when OnAddLinearClick ran after the page Long click."""
    if not isinstance(result, dict):
        return False
    if str(result.get("via") or "") != "page_fn":
        return False
    finish = str(result.get("finish_fn") or "").casefold()
    if "onaddlinear" not in finish and "newlineitem" not in finish:
        return False
    if result.get("long_from_page") is False:
        return False
    return bool(result.get("long_from_page") or result.get("long_clicked"))


def cookie_http_additem_linear_is_not_success(
    result: dict[str, Any] | None,
) -> bool:
    """Cookie-only AddItem_Linear is not success (302 leftover class)."""
    return not linear_finish_from_page_fn(result)


def copy_move_from_page_fn(result: dict[str, Any] | None) -> bool:
    """True only when Copy/Move ran on signed-in EDIT (not cookie HTTP)."""
    if not isinstance(result, dict):
        return False
    if str(result.get("via") or "") != "page_fn":
        return False
    if result.get("copy_move_from_page") is False:
        return False
    return bool(result.get("copy_move_from_page") or result.get("ok"))


def cookie_http_copy_move_is_not_success(
    result: dict[str, Any] | None,
) -> bool:
    """Cookie-only CopyMoveItemToAssembly is not success (302 leftover class)."""
    return not copy_move_from_page_fn(result)


def weld_add_from_page_fn(result: dict[str, Any] | None) -> bool:
    """True only when AddOperation Weld ran on signed-in EDIT."""
    if not isinstance(result, dict):
        return False
    if str(result.get("via") or "") != "page_fn":
        return False
    if result.get("weld_from_page") is False:
        return False
    return bool(result.get("weld_from_page") or result.get("ok"))


def cookie_http_add_operation_is_not_success(
    result: dict[str, Any] | None,
) -> bool:
    """Cookie-only AddOperation is not success (302 leftover class)."""
    return not weld_add_from_page_fn(result)


def long_without_page_click_is_fail(stamp_out: dict[str, Any] | None) -> bool:
    """Long without the orange Long page click is fail-closed.

    Analog of hole-without-PDFInternal: do not Finish / OnAddLinearClick
    when the Long dialog was never opened on signed-in Chrome.
    """
    if not isinstance(stamp_out, dict):
        return True
    if stamp_out.get("long_clicked") is True:
        return False
    via = str(
        stamp_out.get("opened_via") or stamp_out.get("long_via") or ""
    ).casefold()
    compact = via.replace(" ", "")
    if (
        "long" in via
        or "but_bar" in via
        or "addnewitemhtml(bar)" in compact
        or "addnewitemhtml" in via
    ):
        return False
    return True


def long_opened_via_addnewitemhtml_linear_is_fail(
    stamp_out: dict[str, Any] | None,
) -> bool:
    """AddNewItemHTML('linear') / #but_linear is not the gold Long mint.

    Live 6d4373bc / d2ec4357: bar / #but_bar + LinearProduct +
    LinearConfigList 20ft + OnAddLinearClick. Older mocks without
    opened_via pass through.
    """
    if not isinstance(stamp_out, dict):
        return False
    if "opened_via" not in stamp_out and "long_via" not in stamp_out:
        return False
    via = str(stamp_out.get("opened_via") or stamp_out.get("long_via") or "")
    compact = via.replace(" ", "").lower()
    if 'addnewitemhtml("linear"' in compact or "addnewitemhtml('linear'" in compact:
        return True
    return via in {"#but_linear", "linear"}


def leftover_cookie_linear_empty_saw_is_fail(
    dump: dict[str, Any] | None,
) -> bool:
    """Leftover cookie AddItem_Linear 302 / empty Saw OCL is FAIL.

    Gold is page OnAddLinearClick List[0] Saw + Saw-Setup + UnitCost
    filled + ProductID/SKU. Cookie HTTP 302 is not logout.
    """
    if not isinstance(dump, dict):
        return False
    live = dump.get("live_leftover") if isinstance(dump.get("live_leftover"), dict) else {}
    if not live:
        live = dump
    via = str(live.get("finish_via") or live.get("via") or "").casefold()
    if via in {"page_fn", "page"}:
        return False
    try:
        status = int(live.get("status") or live.get("additem_linear_status") or 0)
    except (TypeError, ValueError):
        status = 0
    cookie_302 = (
        live.get("additem_linear_302") is True
        or status in {301, 302, 303, 307, 308}
        or via in {"cookie_http", "http", "cookie"}
    )
    pack = dump.get("list0_pack") if isinstance(dump.get("list0_pack"), dict) else {}
    if not pack:
        pack = live.get("list0_pack") if isinstance(live.get("list0_pack"), dict) else {}
    try:
        ocl_n = int(pack.get("ocl_n") or 0)
    except (TypeError, ValueError):
        ocl_n = 0
    empty_saw = ocl_n == 0 or not _ocl_names_have_saw_pack(pack.get("ocl_names"))
    if live.get("cookie_302_is_logout") is True:
        return False
    return bool(cookie_302 and empty_saw)


def list0_pack_empty_saw_ocl_is_fail(result: dict[str, Any] | None) -> bool:
    """Empty Saw OCL on AddItem_Linear List[0] is FAIL (leftover cookie 302)."""
    if not isinstance(result, dict):
        return False
    if "response_ocl_names" not in result and "response_ocl_n" not in result:
        return False
    names = result.get("response_ocl_names")
    if _ocl_names_have_saw_pack(names):
        return False
    try:
        if int(result.get("response_ocl_n") or 0) != 0 and _ocl_names_have_saw_pack(
            names
        ):
            return False
    except (TypeError, ValueError):
        return False
    return True


def list0_pack_saw_ocl_is_gold(result: dict[str, Any] | None) -> bool:
    """PASS: Saw + Saw-Setup in Primary Costs + UnitCost filled + ProductID/SKU.

    Gold linear pack is on AddItem_Linear List[0] (Long + New Line Item),
    not Operation→Saw. Badge/Tag may be empty — not a fail. Do not
    treat orange Saw tags as gold.
    """
    if not isinstance(result, dict):
        return False
    if not _ocl_names_have_saw_pack(result.get("response_ocl_names")):
        return False
    try:
        if float(result.get("response_unit_cost") or 0) <= 0:
            return False
    except (TypeError, ValueError):
        return False
    pid = str(
        result.get("response_product_id")
        or result.get("response_sku")
        or ""
    ).strip()
    if not pid:
        bag = result.get("request_bag") if isinstance(result.get("request_bag"), dict) else {}
        pid = str(bag.get("productID") or bag.get("sku") or bag.get("name") or "").strip()
    return bool(pid)


def leftover_contours_pierces_zero_is_not_gold(dump: dict[str, Any] | None) -> bool:
    """Named persist: leftover 0/0 vs gold 14501-1 1/1 + list0_pack.

    Missing step is wait-for GET /Quote/PDFInternal after
    AddNewPDFFeature("Hole","cad"), then PDFGetData InternalData.
    Do not invent NumberOfContours on FileList.
    """
    if not isinstance(dump, dict):
        return False
    gold = dump.get("gold_14501_1") if isinstance(dump.get("gold_14501_1"), dict) else {}
    miss = dump.get("leftover_miss") if isinstance(dump.get("leftover_miss"), dict) else {}
    if not gold or not miss:
        return False
    try:
        if int(gold.get("number_of_contours") or 0) != 1:
            return False
        if int(gold.get("number_of_pierces") or 0) != 1:
            return False
        if miss.get("number_of_contours") is None or int(miss.get("number_of_contours")) != 0:
            return False
        if miss.get("number_of_pierces") is None or int(miss.get("number_of_pierces")) != 0:
            return False
    except (TypeError, ValueError):
        return False
    if str(gold.get("badge_string") or "") != "PR":
        return False
    ocl = gold.get("ocl_names")
    if not isinstance(ocl, (list, tuple)):
        return False
    have = {str(n).strip().lower() for n in ocl if str(n).strip()}
    want = {n.lower() for n in GOLD_LASER_CALCULATOR_NAMES}
    if not want <= have:
        return False
    try:
        if float(gold.get("unit_cost") or 0) <= float(gold.get("unit_weight_cost") or 0):
            return False
    except (TypeError, ValueError):
        return False
    if str(miss.get("badge_string") or "") != "":
        return False
    try:
        if miss.get("ocl_n") is None or int(miss.get("ocl_n")) != 0:
            return False
    except (TypeError, ValueError):
        return False
    if miss.get("internaldata") not in ("", None):
        return False
    if miss.get("pdfinternal_xhr") is not False:
        return False
    if miss.get("invent_contours_on_filelist") is not False:
        return False
    feat = dump.get("AddNewPDFFeature") if isinstance(dump.get("AddNewPDFFeature"), dict) else {}
    if feat.get("wait_for_pdfinternal") is not True:
        return False
    if feat.get("race_400ms_not_gold") is not True:
        return False
    if feat.get("invent_internaldata") is not False:
        return False
    if feat.get("cookie_addfeature") is not False:
        return False
    getpdf = dump.get("GetPDFData") if isinstance(dump.get("GetPDFData"), dict) else {}
    omits = {str(k) for k in (getpdf.get("omits") or ())}
    if "NumberOfContours" not in omits or "NumberOfPierces" not in omits:
        return False
    if getpdf.get("contours_not_a_bag_key") is not True:
        return False
    if dump.get("invent_contours_on_filelist") is not False:
        return False
    return True


def hole_feature_without_pdfinternal_is_fail(
    stamp_out: dict[str, Any] | None,
    stamp_rows: list[dict[str, Any]] | None = None,
) -> bool:
    """Drawing has a hole but page GET /Quote/PDFInternal did not land.

    AddNewPDFFeature("Hole","cad") without waiting for PDFInternal
    leaves InternalData empty and NumberOfContours/Pierces 0/0.
    Do not Finish. Do not invent InternalData.
    """
    rows = stamp_rows if isinstance(stamp_rows, list) else []
    has_hole = False
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            dia = float(row.get("HoleDiameter") or 0)
        except (TypeError, ValueError):
            dia = 0.0
        if dia > 0:
            has_hole = True
            break
    if not has_hole:
        return False
    if not isinstance(stamp_out, dict):
        return True
    if not stamp_out.get("pdfinternal_xhr"):
        return True
    try:
        if int(stamp_out.get("internaldata_n") or 0) <= 0:
            return True
    except (TypeError, ValueError):
        return True
    return False


def leftover_productid_is_not_the_pack(dump: dict[str, Any] | None) -> bool:
    """1007092-1 leftover GET: FileList ProductID null, GET ProductID set, no pack.

    Pack miss is not ProductID. GET ProductID + empty Tag / OCL is FAIL.
    Upload bind ProductID 0 is not a stamp skip (live 21681-1). After a
    plate SKU picker, FileList ProductID still null is 34603-2
    (``filelist_productid_null_after_sku_bind_is_fail``).
    """
    if not isinstance(dump, dict):
        return False
    bag = dump.get("filelist_bag") if isinstance(dump.get("filelist_bag"), dict) else {}
    if bag.get("ProductID") not in (None, "", "null"):
        return False
    live = dump.get("live_1007092_1") if isinstance(dump.get("live_1007092_1"), dict) else {}
    if not live:
        return False
    if live.get("get_productid") in (None, "", "null"):
        return False
    if str(live.get("tag") or "") != "":
        return False
    if list(live.get("operation_cost_list") or []):
        return False
    if live.get("production_ready") is not False:
        return False
    if live.get("pack_is_productid") is not False:
        return False
    return True


def leftover_weight_without_productid_is_fail(dump: dict[str, Any] | None) -> bool:
    """33819-1 leftover GET after full stamp: Weight+OP, ProductID None, no pack.

    Empty ProductID is not a Finish skip (live 21681-1). Pack is still
    missing when FileList ProductID is null after L×W / Weight stamp.
    """
    if not isinstance(dump, dict):
        return False
    bag = dump.get("filelist_bag") if isinstance(dump.get("filelist_bag"), dict) else {}
    if bag.get("Weight_UseLocal") is not True:
        return False
    try:
        if float(bag.get("Weight") or 0) <= 0:
            return False
        if float(bag.get("OutsidePerimeter") or 0) <= 0:
            return False
    except (TypeError, ValueError):
        return False
    pid = bag.get("ProductID")
    if pid not in (None, "", "null"):
        return False
    getpdf = dump.get("GetPDFData") if isinstance(dump.get("GetPDFData"), dict) else {}
    if "CuttingLength" not in {str(k) for k in (getpdf.get("omits") or ())}:
        return False
    live = dump.get("live_33819_1") if isinstance(dump.get("live_33819_1"), dict) else {}
    if not live:
        return False
    if str(live.get("tag") or "") != "":
        return False
    if list(live.get("operation_cost_list") or []):
        return False
    return True


def empty_productid_after_bind_is_fail(result: dict[str, Any] | None) -> bool:
    """Upload List ProductID is always null on Image Files PDFs (21681-1).

    keepPid never has anything to restore. Fail-closing *stamp* on empty
    bind ProductID blocked L×W and taught nothing (live 21681-1 GET 0).
    Empty upload ProductID is the Image Files default, not a skip.
    After the plate picker, FileList ProductID still null is 34603-2
    (``filelist_productid_null_after_sku_bind_is_fail``). ``result`` unused.
    """
    del result
    return False


def plate_sku_required(
    stamp_rows: list[dict[str, Any]] | None,
    stamp_out: dict[str, Any] | None = None,
) -> bool:
    """True when the stamp named a plate SKU or the picker searched one."""
    for row in stamp_rows or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("ProductSku") or row.get("SKU") or "").strip():
            return True
    if isinstance(stamp_out, dict) and str(stamp_out.get("picker_sku") or "").strip():
        return True
    return False


def filelist_productid_null_after_sku_bind_is_fail(
    stamp_out: dict[str, Any] | None,
    stamp_rows: list[dict[str, Any]] | None = None,
) -> bool:
    """34603-2: plate SKU required + kendo/FileList ProductID still null.

    Do not Finish. Do not invent a GUID. Upload bind ProductID 0 is
    still not this gate (21681-1 — stamp L×W first).
    """
    if not plate_sku_required(stamp_rows, stamp_out):
        return False
    if not isinstance(stamp_out, dict):
        return True
    try:
        n = int(stamp_out.get("productid_n") or 0)
    except (TypeError, ValueError):
        n = 0
    return n <= 0


def leftover_plate_sku_missing_is_fail(dump: dict[str, Any] | None) -> bool:
    """21682-1 leftover: used quote-time PlateConfig Total=3, then skipped.

    Leftover stay. Full Sheets & Plates (v1/product/plate 1341) also
    has no Domex / PL050 — named reason stays plate_sku_missing.
    Do not invent a GUID. Do not PATCH. Do not remint.
    """
    if not isinstance(dump, dict):
        return False
    bag = dump.get("filelist_bag") if isinstance(dump.get("filelist_bag"), dict) else {}
    if bag.get("ProductID") not in (None, "", "null"):
        return False
    live = dump.get("live_21682_1") if isinstance(dump.get("live_21682_1"), dict) else {}
    if not live:
        return False
    if str(live.get("skip_reason") or "") != "plate_sku_missing":
        return False
    try:
        if int(live.get("plate_config_total") or 0) != 3:
            return False
    except (TypeError, ValueError):
        return False
    if live.get("invented_guid") is True:
        return False
    if live.get("onaddpdfclick") is True:
        return False
    return True


def leftover_productid_hole_empty_badge_is_fail(
    dump: dict[str, Any] | None,
) -> bool:
    """29341-1: ProductID+InternalData+hole still list0_pack BadgeString empty.

    GetPDFData copies ProductID onto FileList. InternalData n=1 is not
    gold NumberOfContours/Pierces 1/1. Do not invent InternalData.
    Gold GET OutsidePerimeter 0 is not this miss.
    """
    if not isinstance(dump, dict):
        return False
    bag = dump.get("filelist_bag") if isinstance(dump.get("filelist_bag"), dict) else {}
    if bag.get("ProductID") in (None, "", "null"):
        return False
    pack = dump.get("list0_pack") if isinstance(dump.get("list0_pack"), dict) else {}
    if str(pack.get("badge_string") or "") != "":
        return False
    try:
        if int(pack.get("ocl_n") or 0) != 0:
            return False
        uc = float(pack.get("unit_cost") or 0)
        uwc = float(pack.get("unit_weight_cost") or 0)
    except (TypeError, ValueError):
        return False
    if uc <= 0 or abs(uc - uwc) > 1e-6:
        return False
    live = dump.get("live_29341_1") if isinstance(dump.get("live_29341_1"), dict) else {}
    if not live:
        return False
    if live.get("hole") is not True:
        return False
    try:
        if int(live.get("internaldata_n") or 0) < 1:
            return False
    except (TypeError, ValueError):
        return False
    if live.get("internaldata_n1_is_gold_contours") is not False:
        return False
    if live.get("list0_pack_is_gold") is not False:
        return False
    if live.get("pack_is_productid") is not False:
        return False
    hyps = dump.get("hypotheses") if isinstance(dump.get("hypotheses"), dict) else {}
    if hyps.get("3_contours_pierces_after_hole") != (
        QUOTE_ORDER_EDIT_PDF_FINISH_HYPOTHESES["3_contours_pierces_after_hole"]
    ):
        return False
    getpdf = dump.get("GetPDFData") if isinstance(dump.get("GetPDFData"), dict) else {}
    if getpdf.get("copies_productid_from_dataitem") is not True:
        return False
    if getpdf.get("hasselectedproductid_not_a_bag_key") is not True:
        return False
    if dump.get("invent_internaldata") is not False:
        return False
    if dump.get("invent_contours_on_filelist") is not False:
        return False
    return True


def leftover_29341_1_hypotheses_named(dump: dict[str, Any] | None) -> bool:
    """QuoteOrderEdit capture named the five Finish hypotheses in order."""
    if not isinstance(dump, dict):
        return False
    hyps = dump.get("hypotheses") if isinstance(dump.get("hypotheses"), dict) else {}
    return hyps == dict(QUOTE_ORDER_EDIT_PDF_FINISH_HYPOTHESES)


def list0_pack_badge_empty_after_productid_hole_is_fail(
    result: dict[str, Any] | None,
    stamp_out: dict[str, Any] | None = None,
    stamp_rows: list[dict[str, Any]] | None = None,
) -> bool:
    """After Finish: ProductID+hole landed, List[0] BadgeString still empty.

    Live 29341-1. Fail-close. Do not treat as persisted. Pack is not
    ProductID. InternalData n=1 is not gold 1/1 contours.
    """
    if not isinstance(result, dict):
        return False
    if "response_badge_string" not in result:
        return False
    if str(result.get("response_badge_string") or "") != "":
        return False
    bag = result.get("filelist_bag") if isinstance(result.get("filelist_bag"), dict) else {}
    pid = bag.get("ProductID")
    stamp_pid = 0
    if isinstance(stamp_out, dict):
        try:
            stamp_pid = int(stamp_out.get("productid_n") or 0)
        except (TypeError, ValueError):
            stamp_pid = 0
    if pid in (None, "", "null") and stamp_pid <= 0:
        return False
    hole = False
    if isinstance(stamp_out, dict):
        try:
            if int(stamp_out.get("internaldata_n") or 0) >= 1:
                hole = True
        except (TypeError, ValueError):
            hole = False
    for row in stamp_rows or []:
        if not isinstance(row, dict):
            continue
        try:
            if float(row.get("HoleDiameter") or 0) > 0:
                hole = True
                break
        except (TypeError, ValueError):
            continue
    return hole


def leftover_contours_zero_after_productid_hole_is_fail(
    dump: dict[str, Any] | None,
) -> bool:
    """1020250-1: ProductID+Dim1+InternalData still Contours=0 / empty pack.

    GetPDFData omits NumberOfContours. Last GetPerimeterAndWeight must
    post Internal: PDFGetData() with Dim1 and #length/#width. Do not
    invent Contours FileList keys. Nest is later.
    """
    if not isinstance(dump, dict):
        return False
    bag = dump.get("filelist_bag") if isinstance(dump.get("filelist_bag"), dict) else {}
    if bag.get("ProductID") in (None, "", "null"):
        return False
    pack = dump.get("list0_pack") if isinstance(dump.get("list0_pack"), dict) else {}
    if str(pack.get("badge_string") or "") != "":
        return False
    try:
        if int(pack.get("number_of_contours") or 0) != 0:
            return False
        if int(pack.get("ocl_n") or 0) != 0:
            return False
    except (TypeError, ValueError):
        return False
    live = dump.get("live_1020250_1") if isinstance(dump.get("live_1020250_1"), dict) else {}
    if not live:
        return False
    if live.get("hole") is not True:
        return False
    try:
        if float(live.get("hole_dim1") or 0) <= 0:
            return False
        if int(live.get("internaldata_n") or 0) < 1:
            return False
        if int(live.get("number_of_contours") or 0) != 0:
            return False
    except (TypeError, ValueError):
        return False
    if live.get("invented_contours") is not False:
        return False
    if live.get("nest_best_sheet") is not False:
        return False
    if dump.get("invent_contours_on_filelist") is not False:
        return False
    if dump.get("operation_profile_graft") is not False:
        return False
    upw = dump.get("UpdatePerimeterWeight") if isinstance(dump.get("UpdatePerimeterWeight"), dict) else {}
    if upw.get("named_miss") != QUOTE_ORDER_EDIT_UPW_INTERNAL["named_miss"]:
        return False
    if upw.get("posts_internal") != "PDFGetData()":
        return False
    return True


def leftover_1020250_1_hypotheses_named(dump: dict[str, Any] | None) -> bool:
    """1020250-1 capture names UPW Internal Dim1 + Nest-later + form L×W + MaterialCost + Data=None."""
    if not isinstance(dump, dict):
        return False
    hyps = dump.get("hypotheses") if isinstance(dump.get("hypotheses"), dict) else {}
    if hyps.get("6_upw_internal_dim1_form_lw") != QUOTE_ORDER_EDIT_UPW_INTERNAL["named_miss"]:
        return False
    if hyps.get("7_nest_best_sheet") != "falsified_nest_is_later":
        return False
    if hyps.get("8_form_lw_synced_false") != QUOTE_ORDER_EDIT_UPW_INTERNAL.get(
        "form_lw_synced_false_miss"
    ):
        return False
    if hyps.get("9_finish_filelist_n0") != QUOTE_ORDER_EDIT_UPW_INTERNAL.get(
        "finish_filelist_n0_miss"
    ):
        return False
    if hyps.get("10_finish_internaldata_null") != QUOTE_ORDER_EDIT_UPW_INTERNAL.get(
        "finish_internaldata_null_miss"
    ):
        return False
    if hyps.get("11_finish_producttype_bar") != QUOTE_ORDER_EDIT_UPW_INTERNAL.get(
        "finish_producttype_bar_miss"
    ):
        return False
    if hyps.get("12_finish_prt_pdf_still_contours_zero") != QUOTE_ORDER_EDIT_UPW_INTERNAL.get(
        "finish_prt_pdf_still_contours_zero_miss"
    ):
        return False
    if hyps.get("13_finish_materialcost_empty") != QUOTE_ORDER_EDIT_UPW_INTERNAL.get(
        "finish_materialcost_empty_miss"
    ):
        return False
    if hyps.get("14_finish_materialcost_abort_blocked") != QUOTE_ORDER_EDIT_UPW_INTERNAL.get(
        "finish_materialcost_abort_blocked_miss"
    ):
        return False
    if hyps.get("15_finish_list0_data_null_errorcount") != QUOTE_ORDER_EDIT_UPW_INTERNAL.get(
        "finish_list0_data_null_errorcount_miss"
    ):
        return False
    return True


def leftover_form_lw_unsynced_after_internal_dim1_is_fail(
    dump: dict[str, Any] | None,
) -> bool:
    """5a231aa / 3e222215: Internal Dim1 UPW with form_lw_synced=false / OP=0."""
    if not isinstance(dump, dict):
        return False
    live = dump.get("live_5a231aa") if isinstance(dump.get("live_5a231aa"), dict) else {}
    if not live:
        return False
    if live.get("getperim_internal_dim1_n") != 1:
        return False
    if live.get("form_lw_synced") is not False:
        return False
    try:
        if int(live.get("outside_perimeter_n") or 0) != 0:
            return False
    except (TypeError, ValueError):
        return False
    if dump.get("invent_contours_on_filelist") is not False:
        return False
    if dump.get("operation_profile_graft") is not False:
        return False
    return True


def form_lw_unsynced_or_empty_perimeter_is_fail(
    stamp_out: dict[str, Any] | None,
) -> bool:
    """Do not Finish when form #length/#width missed or OutsidePerimeter is 0.

    Live 5a231aa 3e222215: getperim_internal_dim1_n=1 + form_lw_synced=false
    + outside_perimeter_n=0. Older stamps without form_lw_synced still
    use empty_perimeter_weight_is_fail. Do not invent Contours keys.
    """
    if not isinstance(stamp_out, dict):
        return False
    if "form_lw_synced" not in stamp_out:
        return False
    if stamp_out.get("form_lw_synced") is not True:
        return True
    try:
        if int(stamp_out.get("outside_perimeter_n") or 0) <= 0:
            return True
    except (TypeError, ValueError):
        return True
    return False


def getpdfdata_empty_or_incomplete_before_finish_is_fail(
    stamp_out: dict[str, Any] | None,
    stamp_rows: list[dict[str, Any]] | None = None,
) -> bool:
    """Do not Finish when GetPDFData n=0 after a good stamp.

    Live 1ca884cc: form_lw_synced=true + OP 69.5 + ProductID + Dim1
    but OnAddPDFClick posted FileList n=0. Older stamps without
    getpdfdata_n still Finish. Hole rows also require Internal Dim1
    + ProductID + OP on the GetPDFData bag. Do not invent Contours.
    """
    if not isinstance(stamp_out, dict):
        return False
    if "getpdfdata_n" not in stamp_out:
        return False
    try:
        n = int(stamp_out.get("getpdfdata_n") or 0)
    except (TypeError, ValueError):
        return True
    if n < 1:
        return True
    try:
        if int(stamp_out.get("getpdfdata_productid_n") or 0) < 1:
            return True
        if int(stamp_out.get("getpdfdata_outside_perimeter_n") or 0) <= 0:
            return True
    except (TypeError, ValueError):
        return True
    hole = False
    if isinstance(stamp_out, dict):
        try:
            if int(stamp_out.get("internaldata_n") or 0) >= 1:
                hole = True
        except (TypeError, ValueError):
            hole = False
        try:
            if float(stamp_out.get("hole_dim1") or 0) > 0:
                hole = True
        except (TypeError, ValueError):
            pass
    for row in stamp_rows or []:
        if not isinstance(row, dict):
            continue
        try:
            if float(row.get("HoleDiameter") or 0) > 0:
                hole = True
                break
        except (TypeError, ValueError):
            continue
    if hole:
        try:
            if int(stamp_out.get("getpdfdata_internal_dim1_n") or 0) < 1:
                return True
        except (TypeError, ValueError):
            return True
    return False


def leftover_finish_filelist_n0_after_form_lw_is_fail(
    dump: dict[str, Any] | None,
) -> bool:
    """1ca884cc: form_lw_synced=true + OP>0 but Finish FileList n=0."""
    if not isinstance(dump, dict):
        return False
    live = dump.get("live_1ca884cc") if isinstance(dump.get("live_1ca884cc"), dict) else {}
    if not live:
        return False
    if live.get("form_lw_synced") is not True:
        return False
    try:
        if float(live.get("outside_perimeter") or 0) <= 0:
            return False
        if "finish_filelist_n" not in live:
            return False
        if int(live.get("finish_filelist_n")) != 0:
            return False
    except (TypeError, ValueError):
        return False
    if dump.get("invent_contours_on_filelist") is not False:
        return False
    if dump.get("operation_profile_graft") is not False:
        return False
    return True


def finish_empty_filelist_after_good_stamp_is_fail(
    result: dict[str, Any] | None,
    stamp_out: dict[str, Any] | None = None,
) -> bool:
    """OnAddPDFClick FileList n=0 after form_lw_synced + OP>0.

    Live 1ca884cc. HTTP 200 + ItemList=1 empty pack is not success.
    """
    if not isinstance(result, dict):
        return False
    if "finish_filelist_n" not in result and "getpdfdata_n" not in result:
        return False
    try:
        posted = int(result.get("finish_filelist_n") or 0)
    except (TypeError, ValueError):
        posted = 0
    try:
        getn = int(result.get("getpdfdata_n") or 0)
    except (TypeError, ValueError):
        getn = 0
    if posted >= 1 and getn >= 1:
        return False
    if str(result.get("finish_why") or "") == "empty_getpdfdata":
        return True
    if not isinstance(stamp_out, dict):
        return posted < 1 or getn < 1
    if stamp_out.get("form_lw_synced") is True:
        try:
            if int(stamp_out.get("outside_perimeter_n") or 0) > 0:
                return posted < 1 or getn < 1
        except (TypeError, ValueError):
            return True
    return posted < 1 or getn < 1


def leftover_finish_internaldata_null_after_dim1_count_is_fail(
    dump: dict[str, Any] | None,
) -> bool:
    """6150c5c7: getpdfdata_internal_dim1_n=1 but Finish bag InternalData null."""
    if not isinstance(dump, dict):
        return False
    live = dump.get("live_6150c5c7") if isinstance(dump.get("live_6150c5c7"), dict) else {}
    if not live:
        return False
    try:
        if int(live.get("getpdfdata_n") or 0) < 1:
            return False
        if int(live.get("getpdfdata_internal_dim1_n") or 0) < 1:
            return False
        if int(live.get("finish_filelist_n") or 0) < 1:
            return False
    except (TypeError, ValueError):
        return False
    idata = live.get("filelist_internaldata")
    if idata not in (None, "", "null", "[]"):
        return False
    if dump.get("invent_contours_on_filelist") is not False:
        return False
    if dump.get("operation_profile_graft") is not False:
        return False
    return True


def finish_bag_internaldata_empty_after_hole_is_fail(
    result: dict[str, Any] | None,
    stamp_out: dict[str, Any] | None = None,
    stamp_rows: list[dict[str, Any]] | None = None,
) -> bool:
    """Posted GetPDFData InternalData null/empty or missing Dim1 after a hole.

    Live 6150c5c7. Older mocks without filelist_internaldata still pass
    through. Do not invent Contours FileList keys.
    """
    if not isinstance(result, dict):
        return False
    has_cap = (
        "filelist_internaldata" in result
        or "filelist_internaldata_dim1_n" in result
    )
    bag = result.get("filelist_bag") if isinstance(result.get("filelist_bag"), dict) else {}
    if not has_cap and "InternalData" not in bag:
        return False
    hole = False
    if isinstance(stamp_out, dict):
        try:
            if int(stamp_out.get("internaldata_n") or 0) >= 1:
                hole = True
        except (TypeError, ValueError):
            hole = False
        try:
            if int(stamp_out.get("getpdfdata_internal_dim1_n") or 0) >= 1:
                hole = True
        except (TypeError, ValueError):
            pass
        try:
            if float(stamp_out.get("hole_dim1") or 0) > 0:
                hole = True
        except (TypeError, ValueError):
            pass
    for row in stamp_rows or []:
        if not isinstance(row, dict):
            continue
        try:
            if float(row.get("HoleDiameter") or 0) > 0:
                hole = True
                break
        except (TypeError, ValueError):
            continue
    if not hole:
        return False
    if str(result.get("finish_why") or "") == "empty_internaldata":
        return True
    idata = result.get("filelist_internaldata")
    if idata is None and "InternalData" in bag:
        idata = bag.get("InternalData")
    if idata in (None, "", "null", "[]", "{}"):
        return True
    try:
        if "filelist_internaldata_dim1_n" in result:
            if int(result.get("filelist_internaldata_dim1_n") or 0) < 1:
                return True
    except (TypeError, ValueError):
        return True
    return False


def filelist_producttype_is_linear_bar(value: Any) -> bool:
    """FileList ProductType/ProductSubType bar / bar_flat (grid default)."""
    text = str(value or "").strip().lower()
    return text == "bar" or text.startswith("bar_")


_LINEAR_FILELIST_SUBTYPES = frozenset(
    {
        "bar",
        "bar_flat",
        "bar_round",
        "bar_sq",
        "tube",
        "pipe",
        "channel",
        "angle",
        "struct_ang",
        "structural",
        "hss",
        "beam",
    }
)


def filelist_productsubtype_is_linear(value: Any) -> bool:
    """Linear catalog / grid-default ProductSubType — not Cad plate."""
    text = str(value or "").strip().lower()
    if not text:
        return False
    if filelist_producttype_is_linear_bar(text):
        return True
    return text in _LINEAR_FILELIST_SUBTYPES or text.startswith("struct_")


def cad_partmode_row(row: dict[str, Any] | None) -> bool:
    """True when FileList row is Cad PartMode / Cad FileType (plate)."""
    if not isinstance(row, dict):
        return False
    if is_cad_filelist_row(row):
        return True
    if filelist_row_partmode_set(row):
        try:
            return int(row.get("PartMode")) == 0
        except (TypeError, ValueError):
            return False
    return False


def sanitize_cad_partmode_filelist_row(
    row: dict[str, Any] | None,
) -> dict[str, Any]:
    """Cad PartMode: drop Linear ProductSubType (live 28768-1 bar_flat).

    Do not invent prt_dxf / Contours / InternalData. Preserve explode
    InternalData when already nonempty.
    """
    if not isinstance(row, dict):
        return {}
    out = dict(row)
    if not cad_partmode_row(out):
        return out
    if filelist_productsubtype_is_linear(out.get("ProductSubType")):
        out.pop("ProductSubType", None)
    return out


def copy_explode_internaldata_through(
    src_rows: list[dict[str, Any]] | None,
    dest: dict[str, Any] | None,
) -> dict[str, Any]:
    """Copy nonempty explode InternalData/Contours onto dest. Never invent."""
    return copy_cadimport_get_payload_through(src_rows, dest)


def filelist_producttype_is_plate_or_sheet(value: Any) -> bool:
    """Cad Image Files plate/sheet family — QuoteOrderEdit prt_pdf / plate / sheet."""
    text = str(value or "").strip().lower()
    if not text or filelist_producttype_is_linear_bar(text):
        return False
    if text.startswith("prt_"):
        return True
    return (
        text in {"plate", "sheet", "plates", "sheets"}
        or "plate" in text
        or "sheet" in text
    )


def leftover_finish_producttype_bar_after_plate_is_fail(
    dump: dict[str, Any] | None,
) -> bool:
    """bab8f668: plate ProductID + InternalData Dim1, ProductType=bar/bar_flat."""
    if not isinstance(dump, dict):
        return False
    live = dump.get("live_bab8f668") if isinstance(dump.get("live_bab8f668"), dict) else {}
    if not live:
        return False
    try:
        if int(live.get("getpdfdata_n") or 0) < 1:
            return False
        if int(live.get("getpdfdata_internal_dim1_n") or 0) < 1:
            return False
        if int(live.get("finish_filelist_n") or 0) < 1:
            return False
    except (TypeError, ValueError):
        return False
    if live.get("productid") in (None, "", "null"):
        return False
    pt = live.get("filelist_producttype")
    pst = live.get("filelist_productsubtype")
    bag = dump.get("filelist_bag") if isinstance(dump.get("filelist_bag"), dict) else {}
    if pt is None:
        pt = bag.get("ProductType")
    if pst is None:
        pst = bag.get("ProductSubType")
    if not (
        filelist_producttype_is_linear_bar(pt)
        or filelist_producttype_is_linear_bar(pst)
        or (
            not filelist_producttype_is_plate_or_sheet(pt)
            and not filelist_producttype_is_plate_or_sheet(pst)
        )
    ):
        return False
    if dump.get("invent_contours_on_filelist") is not False:
        return False
    if dump.get("operation_profile_graft") is not False:
        return False
    return True


def cad_plate_filelist_bar_producttype_is_fail(
    result: dict[str, Any] | None,
    stamp_out: dict[str, Any] | None = None,
    stamp_rows: list[dict[str, Any]] | None = None,
) -> bool:
    """Cad + plate ProductID posted as ProductType bar/bar_* is FAIL.

    Live bab8f668. Older mocks without ProductType still pass through.
    Do not invent Contours FileList keys.
    """
    if not isinstance(result, dict):
        return False
    bag = result.get("filelist_bag") if isinstance(result.get("filelist_bag"), dict) else {}
    has_cap = (
        "filelist_producttype" in result
        or "filelist_productsubtype" in result
        or "ProductType" in bag
        or "ProductSubType" in bag
    )
    if not has_cap and str(result.get("finish_why") or "") != "bar_producttype":
        return False
    pid = bag.get("ProductID")
    stamp_pid = 0
    if isinstance(stamp_out, dict):
        try:
            stamp_pid = int(stamp_out.get("productid_n") or 0)
        except (TypeError, ValueError):
            stamp_pid = 0
    row_pid = False
    item_cad = False
    for row in stamp_rows or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("ProductID") or "").strip():
            row_pid = True
        if str(row.get("ItemType") or "").strip().lower() == "cad":
            item_cad = True
    if pid in (None, "", "null") and stamp_pid < 1 and not row_pid:
        return False
    if str(result.get("finish_why") or "") == "bar_producttype":
        return True
    pt = result.get("filelist_producttype")
    pst = result.get("filelist_productsubtype")
    if pt is None:
        pt = bag.get("ProductType")
    if pst is None:
        pst = bag.get("ProductSubType")
    item = str(bag.get("ItemType") or result.get("filelist_itemtype") or "").lower()
    if item and item != "cad" and not item_cad:
        return False
    if filelist_producttype_is_linear_bar(pt) or filelist_producttype_is_linear_bar(pst):
        return True
    if not filelist_producttype_is_plate_or_sheet(pt) and not filelist_producttype_is_plate_or_sheet(
        pst
    ):
        return True
    return False


def filelist_material_cost_empty(value: Any) -> bool:
    """True when FileList MaterialCost is missing, blank, or 0.

    GetPDFData copies MaterialCost from the #gridPDF dataItem. Gold GET
    Cad (1001898-1) persists a catalog $/lb. Do not invent that rate.
    """
    if value is None or value == "":
        return True
    try:
        return float(value) <= 0
    except (TypeError, ValueError):
        return not str(value).strip()


# Tenant $/lb fields QuoteOrderEdit / v1/product/plate actually copy.
# Generic Cost / Price / UnitCost / UnitPrice are sheet or line totals —
# never treat those as MaterialCost.
CATALOG_MATERIAL_COST_KEYS = (
    "MaterialCost",
    "materialCost",
    "CostPerPound",
    "CostPerLb",
    "costPerPound",
    "costPerLb",
    "PricePerPound",
    "PricePerLb",
    "pricePerPound",
    "pricePerLb",
    "MaterialCostPerPound",
    "MaterialCostPerLb",
    "Cost_Per_Pound",
    "Cost_Per_Lb",
    "Price_Per_Pound",
    "Price_Per_Lb",
)
CATALOG_MATERIAL_COST_UNIT_KEYS = (
    "MaterialCost_Units",
    "materialCost_Units",
    "CostPerPound_Units",
    "CostPerLb_Units",
    "PricePerPound_Units",
    "PricePerLb_Units",
    "MaterialCostPerPound_Units",
    "Cost_Per_Pound_Units",
)


def catalog_material_cost_value(row: dict[str, Any] | None) -> Any:
    """Copy-only catalog $/lb. Do not invent a rate (gold GET 0.55).

    QuoteOrderEdit product-select copies MaterialCost onto the grid row.
    Prefer MaterialCost; accept tenant CostPerPound / PricePerPound
    aliases. Do not take generic Cost / Price / UnitCost (sheet or line
    totals, not necessarily $/lb).
    """
    if not isinstance(row, dict):
        return None
    for key in CATALOG_MATERIAL_COST_KEYS:
        val = row.get(key)
        if not filelist_material_cost_empty(val):
            return val
    return None


def catalog_material_cost_units(row: dict[str, Any] | None) -> str:
    """Copy catalog $/lb units only. Empty when the tenant row has none."""
    if not isinstance(row, dict):
        return ""
    for key in CATALOG_MATERIAL_COST_UNIT_KEYS:
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return ""


def leftover_finish_prt_pdf_still_contours_zero_is_fail(
    dump: dict[str, Any] | None,
) -> bool:
    """c751780e: prt_pdf + InternalData Dim1 + OP, Contours=0 / no PR."""
    if not isinstance(dump, dict):
        return False
    live = dump.get("live_c751780e") if isinstance(dump.get("live_c751780e"), dict) else {}
    if not live:
        return False
    try:
        if int(live.get("getpdfdata_n") or 0) < 1:
            return False
        if int(live.get("getpdfdata_internal_dim1_n") or 0) < 1:
            return False
        if int(live.get("finish_filelist_n") or 0) < 1:
            return False
        if int(live.get("number_of_contours") or 0) != 0:
            return False
    except (TypeError, ValueError):
        return False
    pt = str(live.get("filelist_producttype") or "").strip().lower()
    if pt != CAD_IMAGE_FILES_PLATE_PRODUCT_TYPE:
        return False
    if str(live.get("badge_string") or "") != "":
        return False
    if dump.get("invent_contours_on_filelist") is not False:
        return False
    if dump.get("operation_profile_graft") is not False:
        return False
    if dump.get("nest_best_sheet") is not False:
        return False
    return True


def finish_prt_pdf_still_contours_zero_is_fail(
    result: dict[str, Any] | None,
    stamp_out: dict[str, Any] | None = None,
) -> bool:
    """OnAddPDFClick after prt_pdf + hole Dim1 + OP still Contours=0 / no PR.

    Live c751780e. Older mocks without ProductType still pass through.
    Nest is later (OnAddPDFClick AddRow n.List). Do not invent Contours.
    """
    if not isinstance(result, dict):
        return False
    bag = result.get("filelist_bag") if isinstance(result.get("filelist_bag"), dict) else {}
    pt = result.get("filelist_producttype")
    if pt is None:
        pt = bag.get("ProductType")
    if "filelist_producttype" not in result and "ProductType" not in bag:
        return False
    if str(pt or "").strip().lower() != CAD_IMAGE_FILES_PLATE_PRODUCT_TYPE:
        return False
    try:
        if int(result.get("getpdfdata_internal_dim1_n") or 0) < 1:
            if not isinstance(stamp_out, dict):
                return False
            if int(stamp_out.get("getpdfdata_internal_dim1_n") or 0) < 1:
                return False
    except (TypeError, ValueError):
        return False
    try:
        contours = int(result.get("response_number_of_contours") or 0)
    except (TypeError, ValueError):
        contours = 0
    badge = str(result.get("response_badge_string") or "")
    if contours >= 1 and badge == "PR":
        return False
    return contours < 1 or badge == ""


def leftover_finish_materialcost_empty_after_plate_is_fail(
    dump: dict[str, Any] | None,
) -> bool:
    """2a83a96b: OutsideArea+TrueWeight+prt_pdf, MaterialCost empty, Contours=0.

    Empty MaterialCost is not the Contours miss. Kyle allows default $/lb.
    """
    if not isinstance(dump, dict):
        return False
    live = dump.get("live_2a83a96b") if isinstance(dump.get("live_2a83a96b"), dict) else {}
    if not live:
        return False
    try:
        if int(live.get("getpdfdata_n") or 0) < 1:
            return False
        if int(live.get("getpdfdata_internal_dim1_n") or 0) < 1:
            return False
        if int(live.get("finish_filelist_n") or 0) < 1:
            return False
        if int(live.get("number_of_contours") or 0) != 0:
            return False
        if float(live.get("outsidearea") or 0) <= 0:
            return False
        if float(live.get("trueweight") or 0) <= 0:
            return False
    except (TypeError, ValueError):
        return False
    if live.get("productid") in (None, "", "null"):
        return False
    pt = str(live.get("filelist_producttype") or "").strip().lower()
    if pt != CAD_IMAGE_FILES_PLATE_PRODUCT_TYPE:
        return False
    bag = dump.get("filelist_bag") if isinstance(dump.get("filelist_bag"), dict) else {}
    mc = live.get("materialcost")
    if mc is None:
        mc = bag.get("MaterialCost")
    if not filelist_material_cost_empty(mc):
        return False
    if dump.get("invent_contours_on_filelist") is not False:
        return False
    if dump.get("operation_profile_graft") is not False:
        return False
    if dump.get("nest_best_sheet") is not False:
        return False
    return True


def leftover_empty_materialcost_abort_blocked_finish_is_fail(
    dump: dict[str, Any] | None,
) -> bool:
    """9ef2fedd: empty_materialcost abort skipped OnAddPDFClick.

    Catalog PL7 Ga-A572 has no $/lb. Kyle allows default Material $/lb.
    Aborting Finish blocked Contours investigation. Soft WARNING only.
    """
    if not isinstance(dump, dict):
        return False
    live = dump.get("live_9ef2fedd") if isinstance(dump.get("live_9ef2fedd"), dict) else {}
    if not live:
        return False
    if str(live.get("finish_why") or "") != "empty_materialcost":
        return False
    if str(live.get("via") or "") != "skipped":
        return False
    try:
        if int(live.get("getpdfdata_n") or 0) < 1:
            return False
        if int(live.get("finish_filelist_n") or 0) < 1:
            return False
        if float(live.get("outsidearea") or 0) <= 0:
            return False
        if float(live.get("trueweight") or 0) <= 0:
            return False
    except (TypeError, ValueError):
        return False
    if live.get("productid") in (None, "", "null"):
        return False
    if dump.get("invent_contours_on_filelist") is not False:
        return False
    if dump.get("operation_profile_graft") is not False:
        return False
    if dump.get("nest_best_sheet") is not False:
        return False
    return True


def finish_empty_materialcost_must_not_skip(
    result: dict[str, Any] | None,
) -> bool:
    """True when Finish was skipped solely for empty MaterialCost.

    Live 9ef2fedd. Soft WARNING only — do not abort OnAddPDFClick.
    """
    if not isinstance(result, dict):
        return False
    return str(result.get("finish_why") or "") == "empty_materialcost"


def plate_filelist_material_cost_empty(
    result: dict[str, Any] | None,
    stamp_out: dict[str, Any] | None = None,
    stamp_rows: list[dict[str, Any]] | None = None,
) -> bool:
    """True when Cad + plate ProductID FileList MaterialCost is empty/0.

    Includes gold PASS packs (catalog has no copyable $/lb). Do not invent.
    Older mocks without MaterialCost still pass through.
    """
    if not isinstance(result, dict):
        return False
    bag = result.get("filelist_bag") if isinstance(result.get("filelist_bag"), dict) else {}
    has_cap = (
        "filelist_materialcost" in result
        or "MaterialCost" in bag
        or str(result.get("finish_why") or "") == "empty_materialcost"
    )
    if not has_cap:
        return False
    if str(result.get("finish_why") or "") == "empty_materialcost":
        return True
    pid = bag.get("ProductID")
    stamp_pid = 0
    if isinstance(stamp_out, dict):
        try:
            stamp_pid = int(stamp_out.get("productid_n") or 0)
        except (TypeError, ValueError):
            stamp_pid = 0
    row_pid = False
    item_cad = False
    for row in stamp_rows or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("ProductID") or "").strip():
            row_pid = True
        if str(row.get("ItemType") or "").strip().lower() == "cad":
            item_cad = True
    if pid in (None, "", "null") and stamp_pid < 1 and not row_pid:
        return False
    item = str(bag.get("ItemType") or result.get("filelist_itemtype") or "").lower()
    if item and item != "cad" and not item_cad:
        return False
    mc = result.get("filelist_materialcost")
    if mc is None:
        mc = bag.get("MaterialCost")
    return filelist_material_cost_empty(mc)


def finish_empty_materialcost_after_plate_is_fail(
    result: dict[str, Any] | None,
    stamp_out: dict[str, Any] | None = None,
    stamp_rows: list[dict[str, Any]] | None = None,
) -> bool:
    """Soft WARNING: Cad + plate ProductID with empty/0 MaterialCost.

    Live 2a83a96b posted MaterialCost "" and AddItem still returned
    List[0] UC==UWC / Contours=0. Live 9ef2fedd abort blocked Finish.
    Catalog PL7 Ga-A572 has no rate. Do not invent a $/lb. Do not
    skip OnAddPDFClick. Gold PR + laser pack + UnitCost is PASS —
    empty MaterialCost is then a catalog-no-rate note, not a warning.
    Older mocks without MaterialCost still pass through.
    """
    if not plate_filelist_material_cost_empty(result, stamp_out, stamp_rows):
        return False
    if list0_pack_badge_ocl_is_gold(result) or list0_pack_badge_ocl_contours_is_gold(
        result
    ):
        return False
    return True


def leftover_list0_data_null_errorcount_is_fail(
    dump: dict[str, Any] | None,
) -> bool:
    """97ae3e4f: Finish 200 List[0] Data=None ErrorCount=1 Contours=0.

    Gold 14501-1 Data=DataPartPDF Contours 1/1 ErrorCount=0 Machine=Laser
    Location=Bay1. Leftover FileList Machine=Laser - Bay1 Location=null.
    """
    if not isinstance(dump, dict):
        return False
    live = dump.get("live_97ae3e4f") if isinstance(dump.get("live_97ae3e4f"), dict) else {}
    if not live:
        return False
    if live.get("data_present") is True:
        return False
    kind = str(live.get("data_kind") or "")
    if kind.startswith("DataPartPDF"):
        return False
    if live.get("data") not in (None, "", "None", "null"):
        return False
    try:
        if int(live.get("error_count") or 0) < 1:
            return False
        if int(live.get("number_of_contours") or 0) != 0:
            return False
        if int(live.get("getpdfdata_n") or 0) < 1:
            return False
        if int(live.get("finish_filelist_n") or 0) < 1:
            return False
    except (TypeError, ValueError):
        return False
    if str(live.get("via") or "") == "skipped":
        return False
    if dump.get("invent_contours_on_filelist") is not False:
        return False
    if dump.get("operation_profile_graft") is not False:
        return False
    if dump.get("nest_best_sheet") is not False:
        return False
    return True


def finish_list0_data_null_or_errorcount_is_fail(
    result: dict[str, Any] | None,
) -> bool:
    """Finish List[0] Data null or ErrorCount>0 or Contours=0.

    Live 97ae3e4f. Gold 14501-1 Data=DataPartPDF Contours 1/1 ErrorCount=0.
    Older mocks without response_error_count / response_data_kind pass through.
    """
    if not isinstance(result, dict):
        return False
    if "response_error_count" not in result and "response_data_kind" not in result:
        return False
    try:
        if int(result.get("response_list_n") or 0) < 1:
            return False
    except (TypeError, ValueError):
        return False
    kind = str(result.get("response_data_kind") or "")
    present = result.get("response_data_present")
    data_null = present is False or kind in {"", "null", "None", "none", "missing_row"}
    if kind.startswith("DataPartPDF"):
        data_null = present is False
    try:
        err = int(result.get("response_error_count") or 0)
    except (TypeError, ValueError):
        err = 0
    try:
        contours = int(result.get("response_number_of_contours") or 0)
    except (TypeError, ValueError):
        contours = 0
    return data_null or err > 0 or contours < 1


def list0_pack_contours_zero_after_productid_hole_is_fail(
    result: dict[str, Any] | None,
    stamp_out: dict[str, Any] | None = None,
    stamp_rows: list[dict[str, Any]] | None = None,
) -> bool:
    """OnAddPDFClick 200 but Contours=0 or BadgeString empty after ProductID+hole.

    Live 1020250-1. Fail-close. Do not invent Contours FileList keys.
    """
    if not isinstance(result, dict):
        return False
    if (
        "response_badge_string" not in result
        and "response_number_of_contours" not in result
    ):
        return False
    try:
        contours = int(result.get("response_number_of_contours") or 0)
    except (TypeError, ValueError):
        contours = 0
    badge = str(result.get("response_badge_string") or "")
    if contours >= 1 and badge == "PR":
        return False
    if contours >= 1 and badge != "":
        return False
    bag = result.get("filelist_bag") if isinstance(result.get("filelist_bag"), dict) else {}
    pid = bag.get("ProductID")
    stamp_pid = 0
    if isinstance(stamp_out, dict):
        try:
            stamp_pid = int(stamp_out.get("productid_n") or 0)
        except (TypeError, ValueError):
            stamp_pid = 0
    if pid in (None, "", "null") and stamp_pid <= 0:
        return False
    hole = False
    if isinstance(stamp_out, dict):
        try:
            if int(stamp_out.get("internaldata_n") or 0) >= 1:
                hole = True
        except (TypeError, ValueError):
            hole = False
        try:
            if float(stamp_out.get("hole_dim1") or 0) > 0:
                hole = True
        except (TypeError, ValueError):
            pass
    for row in stamp_rows or []:
        if not isinstance(row, dict):
            continue
        try:
            if float(row.get("HoleDiameter") or 0) > 0:
                hole = True
                break
        except (TypeError, ValueError):
            continue
    if not hole:
        return False
    return contours < 1 or badge == ""


def leftover_filelist_productid_null_after_bind_is_fail(
    dump: dict[str, Any] | None,
) -> bool:
    """34603-2 leftover: picker ran, GetPDFData FileList ProductID null."""
    if not isinstance(dump, dict):
        return False
    bag = dump.get("filelist_bag") if isinstance(dump.get("filelist_bag"), dict) else {}
    if bag.get("ProductID") not in (None, "", "null"):
        return False
    live = dump.get("live_34603_2") if isinstance(dump.get("live_34603_2"), dict) else {}
    if not live:
        return False
    if live.get("productid") not in (None, "", "null"):
        return False
    if not str(live.get("picker_sku") or "").strip() and not str(
        live.get("product_sku") or ""
    ).strip():
        return False
    return True


def empty_weight_after_perimeter_is_fail(
    result: dict[str, Any] | None,
) -> bool:
    """Landed OutsidePerimeter without bag Weight is the 1002323-1 miss.

    GetPDFData posts Weight / Weight_UseLocal. It omits CuttingLength.
    Empty InternalData is not this gate. Only when the stamp names
    ``weight_n`` and ``outside_perimeter_n``. MagicMock / older stamps
    without those keys still Finish.
    """
    if not isinstance(result, dict):
        return False
    if "weight_n" not in result or "outside_perimeter_n" not in result:
        return False
    try:
        perim = int(result.get("outside_perimeter_n") or 0)
    except (TypeError, ValueError):
        perim = 0
    try:
        weight = int(result.get("weight_n") or 0)
    except (TypeError, ValueError):
        weight = 0
    return perim > 0 and weight <= 0


def empty_perimeter_weight_is_fail(result: dict[str, Any] | None) -> bool:
    """Empty OutsidePerimeter / CuttingLengthDisp after L×W is FAIL (29743-1).

    Only when the stamp result names the counts (live Chrome). MagicMock /
    older ``{stamped: n}`` mocks without those keys still Finish.
    """
    if not isinstance(result, dict):
        return False
    if "outside_perimeter_n" not in result and "cutting_length_n" not in result:
        return False
    try:
        perim = int(result.get("outside_perimeter_n") or 0)
    except (TypeError, ValueError):
        perim = 0
    try:
        cut = int(result.get("cutting_length_n") or 0)
    except (TypeError, ValueError):
        cut = 0
    return perim <= 0 and cut <= 0


def prepare_pdf_newline_fields(row: dict[str, Any]) -> dict[str, Any]:
    """Commit Image Files New Line Item fields (not CadImport list-only).

    Drawing flat is Length/Width (or CadImport Stock_X/Y). Never a PDF page outline.
    Proven Image Files FileList uses ItemType=cad, Machine=Laser - Bay1, Status>0.
    """
    out = dict(row)
    try:
        status = float(out.get("Status") or 0)
    except (TypeError, ValueError):
        status = 0.0
    if status <= 0:
        out["Status"] = 1
    machine = str(out.get("Machine") or "").strip()
    if not machine or machine.casefold() in {"laser", "laser - bay1", "laser-bay1"}:
        out["Machine"] = "Laser - Bay1"
    if str(out.get("ItemType") or "").casefold() != "linear":
        out["ItemType"] = "cad"
    out["ProductType"] = out.get("ProductType") or 100
    try:
        if int(out["ProductType"]) != 100 and not out.get("IsLinear"):
            out["ProductType"] = 100
    except (TypeError, ValueError):
        out["ProductType"] = 100
    out["Location"] = out.get("Location") or "Bay1"
    out["ProcessLocation"] = out.get("ProcessLocation") or out.get("Location") or "Bay1"
    if not out.get("PartName") and out.get("Name"):
        out["PartName"] = out["Name"]
    if not out.get("Description") and (out.get("Name") or out.get("PartName")):
        out["Description"] = out.get("Name") or out.get("PartName")
    length = out.get("Length") or out.get("Stock_Y") or out.get("Stock_Length")
    width = out.get("Width") or out.get("Stock_X")
    if length not in (None, ""):
        out["Length"] = length
        out["Length_Units"] = out.get("Length_Units") or "inch"
    if width not in (None, ""):
        out["Width"] = width
        out["Width_Units"] = out.get("Width_Units") or "inch"
    if _qty_of(out) <= 0:
        out["Qty"] = 1
    return out


def slim_pdf_grid_row(row: dict[str, Any]) -> dict[str, Any]:
    """Deprecated helper. AddItem_PDFFiles must keep the full upload List row."""
    return prepare_pdf_newline_fields(row)


def _first_upload_row(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        for row in payload:
            if isinstance(row, dict):
                return row
        return {}
    if not isinstance(payload, dict):
        return {}
    for key in ("List", "Data", "Results", "Result", "File", "NewItem"):
        inner = payload.get(key)
        if isinstance(inner, list):
            for row in inner:
                if isinstance(row, dict):
                    return row
        if isinstance(inner, dict):
            nested = inner.get("NewItem") or inner.get("File") or inner.get("Result")
            if isinstance(nested, dict):
                return nested
            if inner.get("FileID") or inner.get("ID") or inner.get("ImageID"):
                return inner
    if payload.get("FileID") or payload.get("ImageID") or payload.get("ID"):
        return payload
    return {}


def filelist_row_from_attachment_upload(
    payload: Any,
    *,
    part_name: str,
    description: str = "",
    qty: int = 1,
    material: str = "A36",
    thickness: Any = None,
    length: Any = None,
    width: Any = None,
    file_name: str = "",
) -> dict[str, Any]:
    """FileList row after POST /Attachment/UploadItem_PDFFiles (not CadImport).

    Merge the upload List row so calculator identity fields stay on FileList.
    Keep whatever the upload actually returned. Do not invent SourceDataID
    (live Upload List often has none). Live 7a555ac2 posted an 85-key
    jquery.param FileList[0][Field] + Laser - Bay1 and still left Badge
    empty — do not switch that encoding to JSON.
    """
    src = dict(_first_upload_row(payload))
    file_id = src.get("FileID") or src.get("ID") or src.get("ImageID") or ""
    image_id = src.get("ImageID") or file_id
    length = length if length not in (None, "") else (
        src.get("Length") or src.get("Stock_Y")
    )
    width = width if width not in (None, "") else (
        src.get("Width") or src.get("Stock_X")
    )
    thickness = thickness if thickness not in (None, "") else src.get("Thickness")
    row = dict(src)
    row.update(
        {
            "Status": 1,
            "ItemType": "cad",
            "ItemID": src.get("ItemID") or EMPTY_GUID,
            "FileID": file_id,
            "ImageID": image_id,
            "FileName": file_name or src.get("FileName") or "",
            "PartName": part_name,
            "Description": description or part_name,
            "Qty": max(1, int(qty or 1)),
            "Machine": "Laser - Bay1",
            "Material": material or "A36",
            "Thickness": thickness,
            "Thickness_Units": src.get("Thickness_Units") or "inch",
            "Length": length,
            "Length_Units": src.get("Length_Units") or "inch",
            "Width": width,
            "Width_Units": src.get("Width_Units") or "inch",
            "ProductType": src.get("ProductType") or 100,
        }
    )
    if src.get("SourceDataID") not in (None, ""):
        row["SourceDataID"] = src["SourceDataID"]
    if src.get("FileID") not in (None, ""):
        row["FileID"] = src["FileID"]
    return prepare_pdf_newline_fields(row)


def _filelist_dim(val: Any) -> float:
    """Numeric FileList Thickness / Length / Width (fractions ok)."""
    if val in (None, ""):
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        text = str(val).strip().replace('"', "").replace("″", "").replace("'", "")
        if "/" in text:
            try:
                num, den = text.split("/", 1)
                den_f = float(den)
                if den_f:
                    return float(num) / den_f
            except (TypeError, ValueError, ZeroDivisionError):
                return 0.0
        return 0.0


def attachment_pdf_filelist_ready(row: dict[str, Any] | None) -> bool:
    """True only when Image Files New Line Item fields are present."""
    if not isinstance(row, dict):
        return False
    if str(row.get("ItemType") or "").strip().casefold() != "cad":
        return False
    try:
        thickness = _filelist_dim(row.get("Thickness"))
        length = _filelist_dim(row.get("Length"))
        width = _filelist_dim(row.get("Width"))
        status = float(row.get("Status") or 0)
    except (TypeError, ValueError):
        return False
    return thickness > 0 and length > 0 and width > 0 and status > 0


def is_cadimport_only_filelist_row(row: dict[str, Any] | None) -> bool:
    """CadImport identity without Attachment New Line Item fields."""
    if not isinstance(row, dict):
        return False
    has_cadimport = bool(row.get("SourceDataID")) or "CadType" in row
    return has_cadimport and not attachment_pdf_filelist_ready(
        prepare_pdf_newline_fields(row)
    )


def quote_item_rows(payload: Any) -> list[dict[str, Any]]:
    """Rows from v1/quote ItemList or QuoteItem_Read Data."""
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("ItemList", "Data", "Results"):
        rows = payload.get(key)
        if isinstance(rows, list):
            return [r for r in rows if isinstance(r, dict)]
    return []


def count_cad_product_type(payload: Any) -> int:
    n = 0
    for it in quote_item_rows(payload):
        try:
            if int(it.get("ProductType")) == 100:
                n += 1
        except (TypeError, ValueError):
            continue
    return n


def count_linear_product_type(payload: Any) -> int:
    n = 0
    for it in quote_item_rows(payload):
        try:
            if int(it.get("ProductType")) in VALID_LINEAR_PRODUCT_TYPES:
                n += 1
        except (TypeError, ValueError):
            continue
    return n


def linear_lookup_rows(payload: Any) -> list[dict[str, Any]]:
    """Rows from /Product/Read_DataLinearlookup or a catalog product.Configs.

    Do not stop at Data. Live 7a555ac2 Data was the product-shaped row
    (Value == productID); the 20ft/21ft config GUIDs sat on List.
    """
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if not isinstance(payload, dict):
        return []
    out: list[dict[str, Any]] = []
    seen: set[int] = set()

    def _add(rows: Any) -> None:
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            return
        for row in rows:
            if not isinstance(row, dict):
                continue
            marker = id(row)
            if marker in seen:
                continue
            seen.add(marker)
            out.append(row)
            for nested_key in (
                "Configs",
                "ProductConfigList",
                "ProductConfigs",
                "List",
            ):
                inner = row.get(nested_key)
                if inner is not None and inner is not row:
                    _add(inner)

    for key in (
        "Data",
        "Results",
        "List",
        "Configs",
        "ProductConfigList",
        "ProductConfigs",
        "ItemList",
    ):
        _add(payload.get(key))
    if not out and any(payload.get(k) not in (None, "") for k in ("Value", "ID", "Text", "Name")):
        out.append(payload)
    return out


def _linear_config_guid(
    row: dict[str, Any] | None,
    *,
    not_id: str | None = None,
) -> str | None:
    """Stock-length config GUID. Never the product GUID (that 500s)."""
    if not isinstance(row, dict):
        return None
    skip = {
        EMPTY_GUID,
        str(not_id or "").strip(),
        str(row.get("ProductID") or "").strip(),
        str(row.get("productID") or "").strip(),
    }
    skip.discard("")
    for key in (
        "Value",
        "ProductConfigID",
        "ConfigID",
        "ConfigValue",
        "Key",
    ):
        val = row.get(key)
        if is_tenant_guid(val) and str(val) not in skip:
            return str(val)
    val = row.get("ID")
    if is_tenant_guid(val) and str(val) not in skip:
        return str(val)
    for key, val in row.items():
        if key in {"ProductID", "productID", "ID"}:
            continue
        if is_tenant_guid(val) and str(val) not in skip:
            return str(val)
    return None


def _linear_stock_feet(row: dict[str, Any] | None) -> float | None:
    if not isinstance(row, dict):
        return None
    label = " ".join(
        str(row.get(k) or "")
        for k in ("Name", "Text", "Display", "Description", "Length", "StockLength")
    )
    match = _FT_RE.search(label)
    if not match:
        return None
    try:
        return float(match.group(1))
    except (TypeError, ValueError):
        return None


def _lookup_row_belongs_to_product(
    row: dict[str, Any] | None,
    product: dict[str, Any] | None,
) -> bool:
    """True when a Read_DataLinearlookup row is this SKU — not the first 20ft row."""
    if not isinstance(row, dict) or not isinstance(product, dict):
        return False
    pid = str(product.get("ID") or product.get("ProductID") or "").strip()
    row_pid = str(row.get("ProductID") or row.get("productID") or "").strip()
    if pid and row_pid and row_pid == pid:
        return True
    sku = str(
        product.get("ProductName") or product.get("SKU") or product.get("ProductCode") or ""
    ).strip().upper()
    if not sku:
        return False
    blob = " ".join(
        str(row.get(k) or "")
        for k in ("ProductName", "SKU", "Name", "Text", "Display", "Description")
    ).upper()
    compact = sku.replace(" ", "")
    return bool(sku and (sku in blob or compact in blob.replace(" ", "")))


def pick_linear_config_row(
    rows: list[dict[str, Any]] | None,
    *,
    product_id: str | None = None,
    product: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Prefer the 20ft/21ft stock config row. Never a row whose GUID is productID."""
    wanted = str(product_id or (product or {}).get("ID") or "").strip()
    pool = [r for r in (rows or []) if isinstance(r, dict)]
    stock = [
        r
        for r in pool
        if _linear_stock_feet(r) in (20.0, 21.0)
        and _linear_config_guid(r, not_id=wanted)
    ]
    if stock:
        pool = stock
    elif product is not None or wanted:
        owned = [
            r
            for r in pool
            if _linear_config_guid(r, not_id=wanted)
            and (
                _lookup_row_belongs_to_product(r, product)
                or (
                    wanted
                    and str(r.get("ProductID") or r.get("productID") or "") == wanted
                )
            )
        ]
        distinct = [r for r in pool if _linear_config_guid(r, not_id=wanted)]
        pool = owned or distinct
    ranked: list[tuple[float, dict[str, Any]]] = []
    for row in pool:
        cid = _linear_config_guid(row, not_id=wanted)
        if not cid or (wanted and cid == wanted):
            continue
        feet = _linear_stock_feet(row)
        score = 10.0
        if feet in (20.0, 21.0):
            score = 100.0
        elif feet:
            score = 20.0
        ranked.append((score, row))
    if not ranked:
        return None
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1]


def pick_linear_config_id(
    rows: list[dict[str, Any]] | None,
    *,
    product_id: str | None = None,
    product: dict[str, Any] | None = None,
) -> str | None:
    """20ft/21ft config GUID. Never the product GUID (live 7a555ac2 500)."""
    wanted = str(product_id or (product or {}).get("ID") or "").strip()
    row = pick_linear_config_row(rows, product_id=product_id, product=product)
    if not row:
        return None
    cid = _linear_config_guid(row, not_id=wanted)
    if not cid or (wanted and cid == wanted):
        return None
    return cid


def item_linear_config_id(item: dict[str, Any] | None) -> str | None:
    """Current LinearConfigList / productConfigID on a GET item."""
    if not isinstance(item, dict):
        return None
    for key in (
        "productConfigID",
        "ProductConfigID",
        "LinearProductConfigID",
        "LinearConfigList",
    ):
        val = item.get(key)
        if is_tenant_guid(val):
            return str(val)
    return None


def linear_config_stock_feet(
    rows: list[dict[str, Any]] | None,
    config_id: str | None,
    *,
    product_id: str | None = None,
) -> float | None:
    """Stock feet for a config GUID from Read_DataLinearlookup rows."""
    wanted = str(config_id or "").strip()
    if not wanted:
        return None
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        guid = _linear_config_guid(row, not_id=product_id)
        if guid and guid.casefold() == wanted.casefold():
            return _linear_stock_feet(row)
    return None


def _linear_bind_val(*rows: dict[str, Any] | None, keys: tuple[str, ...]) -> Any:
    """First non-empty value from the given rows in order."""
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in keys:
            val = row.get(key)
            if val not in (None, ""):
                return val
    return None


def _sku_num_token(raw: str) -> float | None:
    text = str(raw or "").strip().replace("-", " ")
    if not text:
        return None
    try:
        if " " in text and "/" in text:
            whole, frac = text.split(None, 1)
            num, den = frac.split("/", 1)
            return float(whole) + float(num) / float(den)
        if "/" in text:
            num, den = text.split("/", 1)
            den_f = float(den)
            if den_f == 0:
                return None
            return float(num) / den_f
        return float(text)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


LINEAR_SKU_MISSING = "sku_missing"
_LINEAR_SKU_PREFIXES = ("HSS", "DOM", "RCT", "RTD", "RT", "ST", "L", "C", "P")
_TUBE_SKU_PREFIXES = ("HSS", "DOM", "RCT", "RTD", "RT", "ST")
_TUBE_GRADE_RE = re.compile(
    r"\bA\s*500\s*B?\b|\bA\s*513\b|\bA\s*519\b|\bA\s*106\b|\bA\s*53\b",
    re.IGNORECASE,
)
_FITTING_RE = re.compile(
    r"\b(ELBOW|COUPLING|NIPPLE|PLUG|PIPE\s+CAP|FITTING|REDUCER|UNION|"
    r"FILLER\s*-?\s*NECK)\b",
    re.IGNORECASE,
)


def linear_description_is_fitting(description: str | None) -> bool:
    """Purchased fittings are Component — Long must not graft a pipe/tube SKU."""
    return bool(_FITTING_RE.search(str(description or "")))


def sku_material_grade(sku: str | None) -> str:
    """Trailing -A500 / -A500B / -A36 token from a tenant SKU name."""
    raw = str(sku or "").upper().replace(" ", "")
    match = re.search(r"-([A-Z][A-Z0-9]*)$", raw)
    return match.group(1) if match else ""


def linear_grades_equivalent(left: str | None, right: str | None) -> bool:
    """A500B ≡ A500; exact otherwise. Empty sides are not a match."""

    def _norm(grade: str | None) -> str:
        compact = re.sub(r"[^A-Z0-9]", "", str(grade or "").upper())
        if compact.startswith("A500"):
            return "A500"
        return compact

    a = _norm(left)
    b = _norm(right)
    if not a or not b:
        return False
    return a == b or a in b or b in a


def parse_linear_sku_dims(sku: str | None) -> dict[str, float]:
    """Dim1-4 from this SKU only (C3X4.1 / L1/2X1/2X1/8 / RTD4X0.375 / ST8)."""
    raw = str(sku or "").upper().replace(" ", "")
    raw = re.sub(r"-[A-Z][A-Z0-9]*$", "", raw)
    rest = raw
    for prefix in _LINEAR_SKU_PREFIXES:
        if raw.startswith(prefix):
            rest = raw[len(prefix) :]
            break
    nums: list[float] = []
    for tok in re.split(r"[X×]", rest):
        num = _sku_num_token(tok)
        if num is None:
            continue
        nums.append(num)
        if len(nums) >= 4:
            break
    out: dict[str, float] = {}
    for idx, num in enumerate(nums, start=1):
        out[f"dim{idx}"] = num
    return out


def infer_linear_subtype(sku: str | None, description: str | None = None) -> str:
    """Website productSubType for this SKU — never copy another SKU's struct_ang."""
    text = f" {sku or ''} {description or ''} ".upper()
    compact = str(sku or "").upper().replace(" ", "")
    if "CHANNEL" in text or re.match(r"^C\d", compact):
        return "channel"
    if "ANGLE" in text or (compact.startswith("L") and "X" in compact):
        return "struct_ang"
    if compact.startswith(_TUBE_SKU_PREFIXES) or " TUBE" in text:
        return "tube"
    if re.match(r"^P[\d/]", compact) or " PIPE" in text:
        return "pipe"
    if "HOSE GUARD" in text or " BAR" in text:
        return "bar"
    return "bar"


def linear_bind_fields(
    product: dict[str, Any] | None,
    configs: list[dict[str, Any]] | None = None,
    *,
    lookup_scoped: bool = False,
) -> dict[str, Any] | None:
    """productID + this SKU's subtype/dims/weightLength + its productConfigID.

    Never overlay another SKU's lookup row (live 51e017e reused L1/2 angle
    struct_ang / dim1=0.5 / wl=0.37275 on C3X4.1 and RT*). Lookup supplies
    the 20ft/21ft GUID; dims come from the catalog product or this SKU parse.
    """
    if not isinstance(product, dict):
        return None
    pid = product.get("ID") or product.get("ProductID")
    if not is_tenant_guid(pid):
        return None
    nested = list(configs or [])
    if not nested:
        nested = linear_lookup_rows(product)
    del lookup_scoped  # lookup List/Data is always scanned; never owned-only
    # Config GUIDs live on anonymous {Value, Text: "20 ft"} rows. A
    # product-shaped Data row (SKU in ProductName, Value==productID) is
    # "owned" and used to hide those Values — that 500'd live 7a555ac2.
    cfg_row = pick_linear_config_row(nested, product_id=str(pid), product=product) or {}
    cfg = _linear_config_guid(cfg_row, not_id=str(pid))
    if not cfg or cfg == str(pid):
        return None
    sku = str(
        product.get("ProductName")
        or product.get("SKU")
        or product.get("ProductCode")
        or ""
    )
    sku_dims = parse_linear_sku_dims(sku)
    owned_row = cfg_row if _lookup_row_belongs_to_product(cfg_row, product) else {}
    subtype = str(
        _linear_bind_val(
            product,
            owned_row,
            keys=("productSubType", "ProductSubType", "SubType", "ProductSubTypeName"),
        )
        or infer_linear_subtype(sku, str(product.get("Name") or ""))
    ).strip()

    def _dim(n: int) -> Any:
        got = _linear_bind_val(
            product,
            owned_row,
            keys=(f"dim{n}", f"Dim{n}", f"DIM{n}", f"Size{n}"),
        )
        if got not in (None, ""):
            return got
        if sku_dims.get(f"dim{n}") is not None:
            return sku_dims[f"dim{n}"]
        return 0

    return {
        "productID": str(pid),
        "productConfigID": cfg,
        "productSubType": subtype,
        "dim1": _dim(1),
        "dim1_Unit": _linear_bind_val(
            product, owned_row, keys=("dim1_Unit", "Dim1_Unit", "dim1_Units", "Dim1_Units")
        )
        or "inch",
        "dim2": _dim(2),
        "dim2_Unit": _linear_bind_val(
            product, owned_row, keys=("dim2_Unit", "Dim2_Unit", "dim2_Units", "Dim2_Units")
        )
        or "inch",
        "dim3": _dim(3),
        "dim3_Unit": _linear_bind_val(
            product, owned_row, keys=("dim3_Unit", "Dim3_Unit", "dim3_Units", "Dim3_Units")
        )
        or "inch",
        "dim4": _dim(4),
        "dim4_Unit": _linear_bind_val(
            product, owned_row, keys=("dim4_Unit", "Dim4_Unit", "dim4_Units", "Dim4_Units")
        )
        or "inch",
        "weightLength": _linear_bind_val(
            product,
            owned_row,
            keys=(
                "weightLength",
                "WeightLength",
                "WeightPerFoot",
                "WtPerFt",
                "Weight_Length",
            ),
        )
        or 0,
        "weightLength_Units": _linear_bind_val(
            product,
            owned_row,
            keys=("weightLength_Units", "WeightLength_Unit", "WeightLength_Units"),
        )
        or "pound/foot",
        "sku": sku or None,
    }


def redact_linear_add_keys(payload: dict[str, Any] | None) -> str:
    """Redacted OnAddLinearClick bag for 500 dumps (no full GUIDs)."""
    bits: list[str] = []
    for key in LINEAR_ADD_FIELDS:
        val = (payload or {}).get(key, "")
        if val in ("", None):
            bits.append(f"{key}=<empty>")
            continue
        if is_tenant_guid(val):
            bits.append(f"{key}=guid…{str(val)[-4:]}")
            continue
        bits.append(f"{key}={val}")
    return " ".join(bits)


def jquery_ajax_form(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    """jQuery $.param (traditional=false) — ajax default urlencoding."""
    pairs: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, inner in value.items():
            name = f"{prefix}[{key}]" if prefix else str(key)
            pairs.extend(jquery_ajax_form(inner, name))
        return pairs
    if isinstance(value, (list, tuple)):
        for idx, inner in enumerate(value):
            pairs.extend(jquery_ajax_form(inner, f"{prefix}[{idx}]"))
        return pairs
    if value is None:
        return [(prefix, "")]
    if isinstance(value, bool):
        return [(prefix, "true" if value else "false")]
    return [(prefix, str(value))]


def build_pdf_finish_payload(
    quote_id: str,
    file_list: list[dict[str, Any]],
    *,
    item_id: str | None = None,
    customer_material: bool = False,
) -> dict[str, Any]:
    """POST /Quote/AddItem_PDFFiles — { ID, ItemID, FileList } one part."""
    del customer_material  # row field only; not a top-level OnAddPDFClick key
    prepared = [
        prepare_pdf_newline_fields(r)
        for r in (file_list or [])
        if isinstance(r, dict)
    ]
    # Keep every upload List key. Slimming drops calculator identity that is
    # not named SourceDataID (live 51e017e Upload List never had SourceDataID).
    rows = [
        r
        for r in filter_pdf_filelist(prepared)
        if attachment_pdf_filelist_ready(r)
    ]
    return {
        "ID": quote_id,
        "ItemID": item_id or EMPTY_GUID,
        "FileList": rows,
    }


def build_linear_add_payload(
    quote_id: str,
    *,
    product_id: str,
    qty: int = 1,
    length: float | None = None,
    material: str | None = None,
    machine: str = "Saw",
    name: str = "",
    item_id: str | None = None,
    customer_material: bool = False,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """POST /Quote/AddItem_Linear (OnAddLinearClick) — exact form keys."""
    payload: dict[str, Any] = {key: "" for key in LINEAR_ADD_FIELDS}
    payload["ID"] = quote_id
    payload["ItemID"] = item_id or EMPTY_GUID
    payload["productID"] = product_id
    payload["productType"] = linear_add_product_type(
        name, sku=str((extra or {}).get("sku") or "")
    )
    payload["qty"] = max(1, int(qty))
    payload["machine"] = machine
    payload["customerMaterial"] = bool(customer_material)
    if length is not None:
        payload["length"] = length
        payload["length_unit"] = "inch"
    if material:
        payload["material"] = material
    if name:
        payload["name"] = name
    if extra:
        for key, val in extra.items():
            if key in payload:
                payload[key] = val
    payload["productType"] = coerce_linear_add_product_type(
        payload.get("productType"),
        name=name,
        sku=str((extra or {}).get("sku") or ""),
    )
    cid = str(payload.get("productConfigID") or "")
    pid = str(payload.get("productID") or product_id or "")
    if not is_tenant_guid(payload.get("productConfigID")):
        raise ValueError(
            "AddItem_Linear requires a tenant productConfigID from "
            "/Product/Read_DataLinearlookup (empty GUID 500s)"
        )
    if cid == pid:
        raise ValueError("linear bind productConfigID must not equal productID")
    if str(payload.get("productSubType") or "").strip() == "":
        raise ValueError(
            "AddItem_Linear requires productSubType from the catalog lookup"
        )
    if not any(payload.get(k) not in ("", None) for k in ("dim1", "dim2", "dim3", "dim4")):
        raise ValueError(
            "AddItem_Linear requires dim1-4 from the catalog lookup"
        )
    if payload.get("weightLength") in ("", None):
        raise ValueError(
            "AddItem_Linear requires weightLength from the catalog lookup"
        )
    # Live 29743-1: empty string fixedPrice / productionReady / outsource
    # HTTP 500s. Website AddItem_Linear needs non-null decimal / bool / bool.
    if payload.get("fixedPrice") in ("", None):
        payload["fixedPrice"] = 0
    if payload.get("productionReady") in ("", None):
        payload["productionReady"] = False
    if payload.get("outsource") in ("", None):
        payload["outsource"] = False
    # New rows: empty ItemID. Do not send Internal holes / NREs on Long.
    payload["ItemID"] = item_id or EMPTY_GUID
    payload["Internal"] = ""
    return payload


def build_weld_add_operation_payload(
    quote_id: str,
    item_id: str,
    *,
    weld_inches: float,
    weld_hours: float,
    fitup_hours: float,
    setup_hours: float,
    grind_cost: float = 0.0,
) -> dict[str, Any]:
    """POST /Quote/AddOperation — Q10056 CalcParamType on the assembly only."""
    payload: dict[str, Any] = {key: "" for key in WELD_ADD_FIELDS}
    payload["ID"] = quote_id
    payload["ItemID"] = item_id
    payload["operation_code"] = WELD_OPERATION_CODE
    payload["Equipment"] = WELD_EQUIPMENT
    payload["ApplyTo"] = WELD_APPLY_TO
    payload["CalcParamType"] = WELD_CALC_PARAM_TYPE
    payload["weld"] = float(weld_inches or 0)
    payload["perunittime"] = float(weld_hours or 0)
    payload["perunittime2"] = float(fitup_hours or 0)
    payload["fixedtime"] = float(setup_hours or 0)
    payload["perunitcost"] = float(grind_cost or 0)
    return payload


def build_copy_move_assembly_payload(
    quote_id: str,
    item_id: str,
    assembly_id: str,
    *,
    mode: str = "Move",
) -> dict[str, Any]:
    """POST /Quote/CopyMoveItemToAssembly — kids under the top-level assembly."""
    return {
        "ID": quote_id,
        "ItemID": item_id,
        "AssemblyID": assembly_id,
        "Mode": mode or "Move",
    }


def build_add_feature_payload(
    quote_id: str,
    item_id: str,
    *,
    diameter: float,
    qty: int = 1,
    feature_type: str = "Internal",
) -> dict[str, Any]:
    """POST /Quote/AddFeature — Internal hole when the drawing has one."""
    return {
        "ID": quote_id,
        "ItemID": item_id,
        "FeatureType": feature_type or "Internal",
        "Diameter": float(diameter),
        "Qty": max(1, int(qty or 1)),
    }


def internal_data_from_holes(holes: list[dict[str, Any]] | None) -> str:
    """Serialize hole features for Image Files FileList InternalData."""
    import json

    rows: list[dict[str, Any]] = []
    for hole in holes or []:
        if not isinstance(hole, dict):
            continue
        try:
            dia = float(hole.get("diameter") or hole.get("Diameter") or 0)
        except (TypeError, ValueError):
            continue
        if dia <= 0:
            continue
        try:
            qty = max(1, int(hole.get("qty") or hole.get("Qty") or 1))
        except (TypeError, ValueError):
            qty = 1
        rows.append({"Type": "Circle", "Diameter": dia, "Qty": qty})
    return json.dumps(rows) if rows else ""


def is_website_cookie_302(status_code: int, location: str | None = None) -> bool:
    """Cookie GET 302 is not logout (live 29340-1 Chrome signed in)."""
    del location
    return int(status_code or 0) in {301, 302, 303, 307, 308}


def is_website_login_redirect(status_code: int, location: str | None) -> bool:
    loc = str(location or "")
    return is_website_cookie_302(status_code, loc) and "Login" in loc


def is_cloudflare_challenge(status_code: int, text: str | None) -> bool:
    blob = str(text or "")
    return status_code == 403 and (
        "Just a moment" in blob or "cf-challenge" in blob.lower()
    )


def part_mode_int(category: str) -> int:
    return PART_MODE_BY_CATEGORY.get(str(category or "Cad"), PART_MODE_CAD)


def part_mode_is_null(value: Any) -> bool:
    """True when explode left PartMode unset. 0 is Cad, not null."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip().casefold() in {
        "",
        "null",
        "undefined",
        "none",
    }:
        return True
    return False


def classified_kids_missing_part_mode(
    rows: list[dict[str, Any]] | None,
) -> list[str]:
    """Kid names still missing PartMode after classify (not Assembly)."""
    names: list[str] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        cat = str(row.get("Category") or row.get("ItemType") or "")
        if cat == "Assembly":
            continue
        if "PartMode" not in row or part_mode_is_null(row.get("PartMode")):
            names.append(row_name(row) or "?")
    return names


def kyle_classify_before_finish_blocked(
    rows: list[dict[str, Any]] | None,
) -> str | None:
    """Fail-close if classify did not stamp PartMode (Kyle Loom c9d7c05a)."""
    missing = classified_kids_missing_part_mode(rows)
    if not missing:
        return None
    return (
        "PartMode still null after classify — not Finishing "
        "(Kyle Loom c9d7c05a classify-before-Finish; live 21785-2)"
    )


def finish_attempt_empty_partmode_or_internaldata(
    rows: list[dict[str, Any]] | None,
    result: dict[str, Any] | None = None,
) -> str | None:
    """After AddItem_DXFFiles: PartMode null is fail. FileList InternalData
    empty is not — packs land after Finish (Kyle Loom c9d7 / P904271-1).
    """
    check: list[dict[str, Any]] = []
    if isinstance(result, dict):
        for key in ("FileList", "List"):
            raw = result.get(key)
            if isinstance(raw, list):
                check.extend(r for r in raw if isinstance(r, dict))
                break
    if not check:
        check = [r for r in (rows or []) if isinstance(r, dict)]
    for row in check:
        cat = str(row.get("Category") or row.get("ItemType") or row.get("FileType") or "")
        if cat == "Assembly":
            continue
        if "PartMode" not in row or part_mode_is_null(row.get("PartMode")):
            return (
                "PartMode still null after Finish attempt — not success "
                "(Kyle Loom c9d7c05a classify-before-Finish)"
            )
    return None


def item_cad_contour_count(item: dict[str, Any] | None) -> int:
    """GET Cad Contours from DataPartPDF / Data / row. Absent is 0 — do not invent."""
    if not isinstance(item, dict):
        return 0
    sources: list[dict[str, Any]] = []
    data = item.get("Data")
    if isinstance(data, dict):
        sources.append(data)
        nested = data.get("DataPartPDF")
        if isinstance(nested, dict):
            sources.append(nested)
    dpp = item.get("DataPartPDF")
    if isinstance(dpp, dict):
        sources.append(dpp)
    sources.append(item)
    for src in sources:
        for key in ("NumberOfContours", "Contours"):
            if key not in src:
                continue
            try:
                return max(0, int(src.get(key) or 0))
            except (TypeError, ValueError):
                return 0
    return 0


def step_finish_pack_missing(
    posted: Any,
    *,
    expect_cad: bool,
    expect_linear: bool,
) -> str | None:
    """After STEP Finish: Cad Contours≥1 + PR + laser; Linear Saw if Linear.

    Live P904271-1: classify worked, Finish was refused too early. Packs
    appear after AddItem_DXFFiles. 0 Cad / empty Contours is fail-close.
    Do not invent InternalData.
    """
    from .line_item_ops import item_has_laser_pack, item_has_pr_tag, item_has_saw_pack

    items = [it for it in quote_item_rows(posted) if isinstance(it, dict)]
    if expect_cad:
        cad_items = []
        for it in items:
            cat = str(it.get("Category") or it.get("ItemType") or "")
            try:
                pt = int(it.get("ProductType"))
            except (TypeError, ValueError):
                pt = None
            if cat == "Cad" or pt == 100:
                cad_items.append(it)
        if not cad_items:
            return (
                "GET 0 Cad after Finish — not success "
                "(live P904271-1; ZZ-DEL; do not invent InternalData)"
            )
        if not any(item_cad_contour_count(it) >= 1 for it in cad_items):
            return (
                "Cad Contours empty after Finish — not success "
                "(live P904271-1; ZZ-DEL; do not invent InternalData)"
            )
        if not any(
            item_has_pr_tag(it) and item_has_laser_pack(it) for it in cad_items
        ):
            return (
                "Cad PR+laser pack missing after Finish — not success "
                "(live P904271-1)"
            )
    if expect_linear:
        lin_items = []
        for it in items:
            cat = str(it.get("Category") or it.get("ItemType") or "")
            try:
                pt = int(it.get("ProductType"))
            except (TypeError, ValueError):
                pt = None
            if cat == "Linear" or pt in VALID_LINEAR_PRODUCT_TYPES:
                lin_items.append(it)
        if not lin_items or not any(item_has_saw_pack(it) for it in lin_items):
            return (
                "Linear Saw pack missing after Finish — not success "
                "(live P904271-1)"
            )
    return None


def coerce_product_type(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def is_valid_linear_product_type(value: Any) -> bool:
    return coerce_product_type(value) in VALID_LINEAR_PRODUCT_TYPES


def linear_website_product_type(
    description: str | None,
    sku: str | None = None,
) -> int:
    """GET ItemList ProductType: 10 bar, 30 tube, 40 angle/channel."""
    text = f" {str(description or '').upper()} {str(sku or '').upper()} "
    if any(h in text for h in (" ANGLE", " CHANNEL")):
        return LINEAR_PRODUCT_TYPE_ANGLE
    # Hose guards bind Round Bar (bar), not tube.
    if "HOSE GUARD" in text or "HOSEGUARD" in text:
        return LINEAR_PRODUCT_TYPE_BAR
    if any(h in text for h in (" TUBE", " HSS", " PIPE", " DOM")):
        return LINEAR_PRODUCT_TYPE_TUBE
    sku_u = str(sku or "").upper().strip()
    compact_sku = sku_u.replace(" ", "")
    if sku_u.startswith("L") and "X" in sku_u:
        return LINEAR_PRODUCT_TYPE_ANGLE
    if sku_u.startswith(_TUBE_SKU_PREFIXES):
        return LINEAR_PRODUCT_TYPE_TUBE
    # Tenant pipe SKUs (P5-40-A36 / P1 1/4-40-A36) are Long tube, not bar.
    if re.match(r"^P[\d/]+-\d+", compact_sku):
        return LINEAR_PRODUCT_TYPE_TUBE
    return LINEAR_PRODUCT_TYPE_BAR


LINEAR_ADD_TYPE_STRUCTURAL = "structural"
LINEAR_ADD_TYPE_PIPE = "pipe"
LINEAR_ADD_TYPE_TUBE = "tube"
LINEAR_ADD_TYPE_BAR = "bar"
_LINEAR_ADD_TYPES = frozenset(
    {
        LINEAR_ADD_TYPE_STRUCTURAL,
        LINEAR_ADD_TYPE_PIPE,
        LINEAR_ADD_TYPE_TUBE,
        LINEAR_ADD_TYPE_BAR,
    }
)
_INT_TO_LINEAR_ADD_TYPE = {
    10: LINEAR_ADD_TYPE_BAR,
    20: LINEAR_ADD_TYPE_PIPE,
    30: LINEAR_ADD_TYPE_TUBE,
    40: LINEAR_ADD_TYPE_STRUCTURAL,
}


def linear_add_product_type(
    description: str | None,
    sku: str | None = None,
) -> str:
    """OnAddLinearClick productType: structural / pipe / tube / bar (not 10/30/40)."""
    text = f" {str(description or '').upper()} {str(sku or '').upper()} "
    compact = text.replace(" ", "")
    if "CHANNEL" in text or re.search(r"C\d+X", compact):
        return LINEAR_ADD_TYPE_STRUCTURAL
    if "ANGLE" in text or re.search(r"L\d", compact) and "X" in compact:
        return LINEAR_ADD_TYPE_STRUCTURAL
    if "PIPE" in text or re.search(r"(^|[^A-Z])P[\d/]", compact):
        return LINEAR_ADD_TYPE_PIPE
    if (
        "TUBE" in text
        or "RT" in compact
        or "RCT" in compact
        or "RTD" in compact
        or "HSS" in compact
        or "DOM" in compact
        or re.search(r"(^|[^A-Z])ST[\d.]", compact)
    ):
        return LINEAR_ADD_TYPE_TUBE
    if "HOSE GUARD" in text or "HOSEGUARD" in text or " BAR" in text:
        return LINEAR_ADD_TYPE_BAR
    return LINEAR_ADD_TYPE_BAR


def coerce_linear_add_product_type(
    value: Any,
    *,
    name: str = "",
    sku: str = "",
) -> str:
    """Force the proven-script strings. Int 10/30/40 500s on AddItem_Linear."""
    if isinstance(value, str) and value.strip().casefold() in _LINEAR_ADD_TYPES:
        return value.strip().casefold()
    try:
        mapped = _INT_TO_LINEAR_ADD_TYPE.get(int(value))
        if mapped:
            return mapped
    except (TypeError, ValueError):
        pass
    return linear_add_product_type(name, sku=sku)


def overlay_classified_row(
    row: dict[str, Any],
    *,
    category: str,
    material: str | None = None,
    thickness: str | float | None = None,
    product_id: str | None = None,
    sku: str | None = None,
    qty: int | float | None = None,
    machine: str | None = None,
) -> dict[str, Any]:
    """Apply Cad / Linear / Component + SKU/grade onto a CadImport grid row."""
    out = dict(row)
    cat = category if category in {"Cad", "Linear", "Component", "Assembly"} else "Cad"
    if cat != "Assembly":
        out["PartMode"] = part_mode_int(cat)
    out["ItemType"] = cat
    out["Category"] = cat
    if cat in SETPARTMODE_FILETYPES:
        out["FileType"] = cat
    if qty is not None:
        out["Qty"] = qty
        out["Quantity"] = qty
    elif _qty_of(out) <= 0:
        out["Qty"] = 1
        out["Quantity"] = 1
    if material:
        out["Material"] = material
        out["MaterialGrade"] = material
    if thickness is not None and str(thickness) != "":
        out["Thickness"] = thickness
        out["Thickness_Units"] = out.get("Thickness_Units") or "inch"
    if product_id:
        out["ProductID"] = product_id
    if sku:
        out["SKU"] = sku
    if cat == "Linear":
        out["IsLinear"] = True
        out["IsPlate"] = False
        out["IsPart"] = True
        out["ProductType"] = linear_website_product_type(
            row_name(out), sku=sku
        )
        out["Machine"] = machine or out.get("Machine") or "Saw"
    elif cat == "Component":
        out["IsLinear"] = False
        out["IsPlate"] = False
        out["IsPart"] = True
        out["Machine"] = machine
    elif cat == "Assembly":
        out["IsLinear"] = False
        out["IsPlate"] = False
        out["IsPart"] = False
        out["ProductType"] = 300
        out["Machine"] = None
        out["IsAssembly"] = True
    else:
        # Cad — overwrite Sectura Adjust Properties Component default.
        # API/kendo ProductType=100 (not a UI dropdown click).
        if machine:
            out["Machine"] = machine
        out = bind_plate_step_product_type_cad(out)
        if filelist_productsubtype_is_linear(out.get("ProductSubType")):
            out.pop("ProductSubType", None)
    out["ErrorStatus"] = _error_status(out)
    if out.get("Status") in (None, "", 0, "0"):
        out["Status"] = 1
    return out


def row_name(row: dict[str, Any]) -> str:
    for key in ("Name", "PartName", "Description", "FileName"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return ""


_DIM_TOKEN_RE = re.compile(
    r"(\d+\s+\d+\s*/\s*\d+|\d+\s*/\s*\d+|\d+(?:\.\d+)?)"
    r"\s*(?:x|X|×)\s*"
    r"(\d+\s+\d+\s*/\s*\d+|\d+\s*/\s*\d+|\d+(?:\.\d+)?)"
    r"(?:\s*(?:x|X|×)\s*"
    r"(\d+\s+\d+\s*/\s*\d+|\d+\s*/\s*\d+|\d+(?:\.\d+)?))?"
)
_MIXED_FRAC_RE = re.compile(r"\b(\d+)\s+(\d+)\s*/\s*(\d+)\b")
_BARE_FRAC_RE = re.compile(r"\b(\d+)\s*/\s*(\d+)\b")
_CLEAR_LINEAR_HIT = 8.0


def _as_float(val: Any) -> float | None:
    try:
        if val is None or val == "":
            return None
        return float(val)
    except (TypeError, ValueError):
        return None


def product_linear_dims(product: dict[str, Any] | None) -> list[float]:
    """Dim1-4 from the catalog row, else parse the SKU name. Do not invent."""
    if not isinstance(product, dict):
        return []
    dims = [
        x
        for x in (
            _as_float(product.get("Dim1")),
            _as_float(product.get("Dim2")),
            _as_float(product.get("Dim3")),
            _as_float(product.get("Dim4")),
        )
        if x and x > 0
    ]
    if dims:
        return dims
    sku = str(
        product.get("ProductName")
        or product.get("SKU")
        or product.get("ProductCode")
        or ""
    )
    parsed = parse_linear_sku_dims(sku)
    return [parsed[k] for k in ("dim1", "dim2", "dim3", "dim4") if parsed.get(k)]


def drawing_is_hss_dim_callout(
    description: str | None,
    material: str | None = None,
    row: dict[str, Any] | None = None,
) -> bool:
    """3-dim A500/A513/A519 callout is HSS/rect tube (1007038-1 2.5×5×0.25)."""
    text = f"{description or ''} {material or ''}"
    dims = extract_linear_dims(description or "", row)
    return len(dims) >= 3 and bool(_TUBE_GRADE_RE.search(text))


def drawing_is_rect_hss_tube(
    description: str | None,
    material: str | None = None,
    row: dict[str, Any] | None = None,
) -> bool:
    """TUBE/HSS noun or a 3-dim tube-grade callout."""
    blob = f" {str(description or '').upper()} {str(material or '').upper()} "
    if any(h in blob for h in (" TUBE", " HSS", " RECT TUBE", " RECTANGULAR")):
        return True
    return drawing_is_hss_dim_callout(description, material, row)


def _dim_match_score(want: list[float], got: list[float]) -> float:
    """Score drawing dims against catalog/SKU dims. Rect first-two may swap."""
    want = [d for d in want if d and d > 0]
    got = [d for d in got if d and d > 0]
    if not want or not got:
        return 0.0
    if len(want) >= 3 and len(got) >= 2:
        xy_w = sorted(want[:2])
        wall_w = want[-1]
        if len(got) >= 3:
            xy_g = sorted(got[:2])
            wall_g = got[2]
        else:
            xy_g = sorted(got[:2]) if len(got) >= 2 else [got[0]]
            wall_g = None
        score = 0.0
        if len(xy_g) >= 2:
            score += max(0.0, 15.0 - abs(xy_w[0] - xy_g[0]) * 20.0)
            score += max(0.0, 12.0 - abs(xy_w[1] - xy_g[1]) * 20.0)
        if wall_g is not None:
            score += max(0.0, 10.0 - abs(wall_w - wall_g) * 40.0)
        return score
    best = min(abs(want[0] - p) for p in got)
    score = max(0.0, 15.0 - best * 20.0)
    if len(want) > 1 and len(got) > 1:
        best2 = min(abs(want[1] - p) for p in got)
        score += max(0.0, 8.0 - best2 * 20.0)
    return score


def score_linear_product(
    product: dict[str, Any],
    *,
    description: str,
    material: str | None,
    dims: list[float] | None = None,
) -> float:
    """Higher is closer. Hose guards prefer Round Bar; tubes prefer Mechanical Tube."""
    text = f" {str(description or '').upper()} "
    pname = str(product.get("ProductName") or product.get("SKU") or "").upper()
    compact = pname.replace(" ", "")
    pdesc = str(product.get("ProductDescription") or "").upper()
    shape = str(product.get("ShapeName") or product.get("Category") or "").upper()
    sub = str(product.get("SubCategory") or "").upper()
    grade = str(
        product.get("MaterialGrade")
        or product.get("Property")
        or sku_material_grade(pname)
        or ""
    ).upper()
    blob = f"{pname} {pdesc} {shape} {sub}"
    score = 0.0
    want_dims = [d for d in (dims or []) if d and d > 0]
    drawing_tube = drawing_is_rect_hss_tube(description, material) or any(
        h in text for h in (" TUBE", " HSS", " PIPE", " DOM")
    )

    if "HOSE GUARD" in text or "HOSEGUARD" in text:
        if "ROUND BAR" in blob or "RB" in compact:
            score += 40
        elif "TUBE" in blob or "PIPE" in blob:
            score -= 10
    elif drawing_tube:
        if "TUBE" in blob or "PIPE" in blob or compact.startswith(_TUBE_SKU_PREFIXES):
            score += 30
        if "MECHANICAL TUBE" in blob:
            score += 8
        if compact.startswith(_TUBE_SKU_PREFIXES):
            score += 12
        if "ANGLE" in blob or (compact.startswith("L") and "X" in compact):
            score -= 20
        if "CHANNEL" in blob:
            score -= 20
        # Prior 1001898 binds of P1/8-5-A36 / P1/4-5-A36 on tubes are suspect.
        if " TUBE" in text and " PIPE" not in text:
            if re.match(r"^P[\d/]", compact):
                score -= 25
    elif "ANGLE" in text:
        if "ANGLE" in blob:
            score += 30
    elif "CHANNEL" in text:
        if "CHANNEL" in blob:
            score += 30
    elif "BAR" in text:
        if "BAR" in blob:
            score += 25

    want_grade = (material or "").strip().upper().split()[0] if material else ""
    if not want_grade:
        named = _TUBE_GRADE_RE.search(f"{description or ''} {material or ''}")
        if named:
            want_grade = re.sub(r"\s+", "", named.group(0)).upper()
    if want_grade and grade:
        if linear_grades_equivalent(want_grade, grade):
            score += 20
        else:
            score -= 8
    elif want_grade == "A36" and not grade:
        score += 4

    prod_dims = product_linear_dims(product)
    if want_dims and prod_dims:
        score += _dim_match_score(want_dims, prod_dims)

    if product.get("Active") is False:
        score -= 50
    return score


def extract_linear_dims(description: str, row: dict[str, Any] | None = None) -> list[float]:
    dims: list[float] = []
    row = row or {}
    for key in (
        "Dim1",
        "Dim2",
        "Dim3",
        "Thickness",
        "LinearWidth",
        "width_in",
        "height_in",
        "wall_in",
        "thickness_in",
    ):
        val = _as_float(row.get(key))
        if val and val > 0:
            dims.append(val)
    text = str(description or "").replace('"', "").replace("″", "")
    m = _DIM_TOKEN_RE.search(text)
    if m:
        for g in m.groups():
            if not g:
                continue
            num = _sku_num_token(g)
            if num is not None and num > 0:
                dims.append(num)
    mixed = _MIXED_FRAC_RE.search(text)
    if mixed:
        try:
            dims.append(
                int(mixed.group(1)) + int(mixed.group(2)) / int(mixed.group(3))
            )
        except (TypeError, ValueError, ZeroDivisionError):
            pass
    elif _BARE_FRAC_RE.search(text) and not m:
        frac = _BARE_FRAC_RE.search(text)
        try:
            dims.append(int(frac.group(1)) / int(frac.group(2)))
        except (TypeError, ValueError, ZeroDivisionError):
            pass
    seen: set[float] = set()
    out: list[float] = []
    for d in dims:
        key = round(d, 4)
        if key in seen:
            continue
        seen.add(key)
        out.append(d)
    return out


def pick_closest_linear_product(
    products: list[dict[str, Any]],
    *,
    description: str,
    material: str | None = None,
    row: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Return (product, mismatch_note). Weak hits are sku_missing — no graft."""
    if linear_description_is_fitting(description):
        return None, (
            f"{LINEAR_SKU_MISSING} {description!r} is a fitting — "
            "fail-closed, no silent SKU graft"
        )
    if not products:
        return None, "No linear ProductID catalog available"
    dims = extract_linear_dims(description, row)
    ranked = sorted(
        products,
        key=lambda p: score_linear_product(
            p, description=description, material=material, dims=dims
        ),
        reverse=True,
    )
    best = ranked[0]
    best_score = score_linear_product(
        best, description=description, material=material, dims=dims
    )
    sku = str(best.get("ProductName") or best.get("SKU") or best.get("ID") or "")
    if best_score < _CLEAR_LINEAR_HIT:
        return None, (
            f"{LINEAR_SKU_MISSING} no tenant SKU for {description!r} "
            f"(closest {sku} score={best_score:.1f}; no silent SKU graft)"
        )
    if len(dims) >= 3 and _dim_match_score(dims, product_linear_dims(best)) < 20:
        return None, (
            f"{LINEAR_SKU_MISSING} no tenant SKU for {description!r} "
            f"{dims} — closest {sku} dims do not match; no silent SKU graft"
        )
    want_grade = (material or "").strip().upper().split()[0] if material else ""
    if not want_grade:
        named = _TUBE_GRADE_RE.search(f"{description or ''} {material or ''}")
        if named:
            want_grade = re.sub(r"\s+", "", named.group(0)).upper()
    got_grade = str(
        best.get("MaterialGrade") or sku_material_grade(sku) or ""
    ).upper()
    note = None
    if (
        want_grade
        and got_grade
        and not linear_grades_equivalent(want_grade, got_grade)
    ):
        note = (
            f"Linear grade mismatch: drawing {want_grade} vs SKU "
            f"{sku} ({got_grade})"
        )
    return best, note
