// QuoteOrderEdit ItemType + live Q10335 mouse Cad capture.
// POST /Part/UpdateItemType 200 on Component→Cad dropdown.
// Grid field is ItemType (GetPDFData / onInternalDataChange ItemType==="cad").
// SetPartMode analog is {ID, PartMode}. Capture did not restate request
// keys — wired keys are ID + ItemType only. Do not invent extra keys.
// Contours still 0 before Finish. invent=false.
function UpdateItemType(n,t){$.ajax({type:"POST",url:"/Part/UpdateItemType",data:{ID:n,ItemType:t}})}
