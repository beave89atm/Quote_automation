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
UpdateDXF_LoadNew is editor-only (not gold): #DXFEdit open +
CADType==="DXF" + Previous/Next/combobox → UpdateDataNext.
Live leftover EDIT: WebGLCADDisp undefined, #DXFEdit hidden.
Do not fire UpdateDataNext. Classify→Finish without #DXFEdit
has no InternalData-fill XHR. Leave 5b622a0d / Skin Assembly,
0d4b8a46 / FA Assembly, b8a62e76 / SC0600, and 6a568912 / 10098-1.
Do not remint. Do not mint.

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
  POST /CadImport/UpdateData, UpdateDataNext, SetPartMode, SetUnits, ConvertTo
  POST /Quote/AddItem_DXFFiles   data { ID, ItemID, customerMaterial, FileList }
  POST /Quote/AddItem_PDFFiles   urlencoded { ID, ItemID, FileList }
      FileList = GetPDFData() (#gridPDF tbody dataItem Status>0,
      not an XHR). Reconstructed FileList is fail-closed
      even if GET>0 (live 1001898-5 491f6387).
  POST /Quote/AddItem_Linear     urlencoded OnAddLinearClick field bag
  GET  /Product/Read_DataLinearlookup?ProductID=  (20ft/21ft productConfigID)
  POST /Quote/NestQuote_Edit
  POST /Quote/NestQuoteMultiPart_Renest

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
    "upload_dxf": "/CadImport/UploadItem_DXFFiles",
    "cadimport_data": "/CadImport/Data",
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
    "nest_quote_renest": "/Quote/NestQuoteMultiPart_Renest",
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
    }


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
        persist_setpartmode_filetype(
            copy_cadimport_identity_through(
                src_rows[i] if i < len(src_rows) else {}, dest
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
    payload_block = cad_filelist_payload_blocks_finish(
        filled[0] if filled else None
    )
    why = ""
    if n > 0 and sid_n == 0:
        why = "filelist_missing_ids"
    elif ident_miss:
        why = "filelist_missing_keys=" + "+".join(ident_miss)
    elif payload_block:
        why = "filelist_cad_payload_empty"
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
        "filelist_missing_identity": ident_miss,
        "kendo_row_keys": kendo_identity_log_keys(filled[0]) if filled else [],
        "should_finish": bool(from_kendo and not ident_miss and not payload_block),
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
    """Cookie HTTP UploadItem_PDFFiles does not bind #gridPDF (live 103535-1)."""
    via = str(upload_via or "").strip()
    return via != PDF_UPLOAD_VIA_PAGE_ADD_FILES


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


def leftover_dxf_pack_is_on_additem_list(dump: dict[str, Any] | None) -> bool:
    """Pack is on AddItem_DXFFiles List after Stock type + GetPerimeterAndWeight."""
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

    Only when the stamp result names the counts. MagicMock / older mocks
    without those keys still use the explode-empty fail-closed check.
    """
    if not isinstance(result, dict):
        return False
    keys = ("outside_perimeter_n", "cutting_length_n", "internaldata_n")
    if not any(k in result for k in keys):
        return False
    counts: list[int] = []
    for key in keys:
        if key not in result:
            continue
        try:
            counts.append(int(result.get(key) or 0))
        except (TypeError, ValueError):
            counts.append(0)
    return all(n <= 0 for n in counts)


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


def parse_linear_sku_dims(sku: str | None) -> dict[str, float]:
    """Dim1-4 from this SKU only (C3X4.1 / L1/2X1/2X1/8 / RT1/8X0.022)."""
    raw = str(sku or "").upper().replace(" ", "")
    raw = re.sub(r"-[A-Z][A-Z0-9]*$", "", raw)
    rest = raw
    for prefix in ("HSS", "DOM", "RCT", "RT", "L", "C", "P"):
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
    if compact.startswith(("RT", "RCT", "HSS", "DOM")) or " TUBE" in text:
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


def is_website_login_redirect(status_code: int, location: str | None) -> bool:
    loc = str(location or "")
    return status_code in {301, 302, 303, 307, 308} and "Login" in loc


def is_cloudflare_challenge(status_code: int, text: str | None) -> bool:
    blob = str(text or "")
    return status_code == 403 and (
        "Just a moment" in blob or "cf-challenge" in blob.lower()
    )


def part_mode_int(category: str) -> int:
    return PART_MODE_BY_CATEGORY.get(str(category or "Cad"), PART_MODE_CAD)


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
    if sku_u.startswith(("RT", "RCT", "HSS", "DOM")):
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
        or "HSS" in compact
        or "DOM" in compact
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
        out["IsLinear"] = False
        out["IsPlate"] = True
        out["IsPart"] = True
        out["ProductType"] = 100
        out["Machine"] = machine or out.get("Machine") or "Laser - Bay1"
        if str(out["Machine"]).casefold() == "laser":
            out["Machine"] = "Laser - Bay1"
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
    r"(\d+(?:\.\d+)?)\s*(?:x|X|×)\s*(\d+(?:\.\d+)?)(?:\s*(?:x|X|×)\s*(\d+(?:\.\d+)?))?"
)


def _as_float(val: Any) -> float | None:
    try:
        if val is None or val == "":
            return None
        return float(val)
    except (TypeError, ValueError):
        return None


def score_linear_product(
    product: dict[str, Any],
    *,
    description: str,
    material: str | None,
    dims: list[float] | None = None,
) -> float:
    """Higher is closer. Hose guards prefer Round Bar; tubes prefer Mechanical Tube."""
    text = f" {str(description or '').upper()} "
    pname = str(product.get("ProductName") or "").upper()
    pdesc = str(product.get("ProductDescription") or "").upper()
    shape = str(product.get("ShapeName") or product.get("Category") or "").upper()
    sub = str(product.get("SubCategory") or "").upper()
    grade = str(product.get("MaterialGrade") or product.get("Property") or "").upper()
    blob = f"{pname} {pdesc} {shape} {sub}"
    score = 0.0

    if "HOSE GUARD" in text or "HOSEGUARD" in text:
        if "ROUND BAR" in blob or "RB" in pname:
            score += 40
        elif "TUBE" in blob or "PIPE" in blob:
            score -= 10
    elif any(h in text for h in (" TUBE", " HSS", " PIPE", " DOM")):
        if "TUBE" in blob or "PIPE" in blob:
            score += 30
        if "MECHANICAL TUBE" in blob:
            score += 8
        if pname.startswith("RT") or pname.startswith("RCT") or " RCT" in blob:
            score += 12
        # Prior 1001898 binds of P1/8-5-A36 / P1/4-5-A36 on tubes are suspect.
        if " TUBE" in text and " PIPE" not in text:
            compact_name = pname.replace(" ", "")
            if re.match(r"^P[\d/]", compact_name):
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
    if want_grade and grade:
        if want_grade == grade or want_grade in grade or grade in want_grade:
            score += 20
        else:
            score -= 8
    elif want_grade == "A36" and not grade:
        score += 4

    want_dims = [d for d in (dims or []) if d and d > 0]
    prod_dims = [
        x
        for x in (
            _as_float(product.get("Dim1")),
            _as_float(product.get("Dim2")),
            _as_float(product.get("Dim3")),
            _as_float(product.get("Dim4")),
        )
        if x and x > 0
    ]
    if want_dims and prod_dims:
        # Closest primary dim (OD / leg / bar diameter).
        best = min(abs(want_dims[0] - p) for p in prod_dims)
        score += max(0.0, 15.0 - best * 20.0)
        if len(want_dims) > 1 and len(prod_dims) > 1:
            best2 = min(abs(want_dims[1] - p) for p in prod_dims)
            score += max(0.0, 8.0 - best2 * 20.0)

    if product.get("Active") is False:
        score -= 50
    return score


def extract_linear_dims(description: str, row: dict[str, Any] | None = None) -> list[float]:
    dims: list[float] = []
    row = row or {}
    for key in ("Dim1", "Dim2", "Thickness", "LinearWidth"):
        val = _as_float(row.get(key))
        if val and val > 0:
            dims.append(val)
    text = str(description or "")
    m = _DIM_TOKEN_RE.search(text.replace('"', "").replace("″", ""))
    if m:
        for g in m.groups():
            if not g:
                continue
            try:
                dims.append(float(g))
            except ValueError:
                pass
    # Fraction OD like 3/8 on hose guards.
    frac = re.search(r"\b(\d+)\s*/\s*(\d+)\b", text)
    if frac:
        try:
            dims.append(int(frac.group(1)) / int(frac.group(2)))
        except (TypeError, ValueError, ZeroDivisionError):
            pass
    # unique preserve order
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
    """Return (product, mismatch_note)."""
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
    if best_score < 8:
        return best, (
            f"Closest linear SKU {best.get('ProductName') or best.get('ID')} "
            f"is a weak match for {description!r} — confirm ProductID in SecturaFAB"
        )
    want_grade = (material or "").strip().upper().split()[0] if material else ""
    got_grade = str(best.get("MaterialGrade") or "").upper()
    note = None
    if want_grade and got_grade and want_grade not in got_grade and got_grade not in want_grade:
        note = (
            f"Linear grade mismatch: drawing {want_grade} vs SKU "
            f"{best.get('ProductName')} ({got_grade})"
        )
    return best, note
