var files     = document.getElementById("P2_FILE_UPLOAD").files;
var statusDiv = document.getElementById("ocrStatus");

if (!files || files.length === 0) {
  statusDiv.textContent = "Lütfen bir görsel seçin.";
  return;
}

var form = new FormData();
form.append("image", files[0]);
statusDiv.textContent = "OCR tarafına gönderiliyor...";

fetch("http://127.0.0.1:5000/ocr", {
  method: "POST",
  body: form
})
.then(r => r.json())
.then(function(json) {
  console.log("OCR response:", json);
  if (json.error) throw json.error;

  apex.item("P2_RAW_TEXT")   .setValue(JSON.stringify(json, null, 2));
  apex.item("P2_JSON_FIELDS").setValue(JSON.stringify(json, null, 2));
  apex.item("P2_BELGE_NO")   .setValue(json["Fiş No"]   || json["Fatura No"] || "");
  apex.item("P2_BELGE_TARIHI").setValue(json["Tarih"]     || "");
  apex.item("P2_BELGE_TUTARI").setValue(json["Toplam"]     || "");
  apex.item("P2_BELGE_TURU") .setValue(json["Belge Türü"] || "");

  if (json["Belge Türü"] !== "Fiş") {
    $("#ALT_KALEMLER_GRID").hide();
    return statusDiv.textContent = "Fiş değil; alt kalem yok.";
  }
  $("#ALT_KALEMLER_GRID").show();

var ig$      = apex.region("ALT_KALEMLER_GRID").widget();
var gridView = ig$.interactiveGrid("getViews", "grid");
var model    = gridView.model;

if (!gridView || !model) {
  console.error("Grid view or model not found");
  statusDiv.textContent = "Hata: Grid bulunamadı.";
  return;
}

var recordsToDelete = []; // Collect all records and delete them
model.forEach(function(rec) {
  if (model.getRecordId(rec)) {
    recordsToDelete.push(rec);
  }
});

if (recordsToDelete.length > 0) {
  model.deleteRecords(recordsToDelete);
}

(json["Alt Kalemler"] || []).forEach(function(row) { // 3) Insert and populate rows
  var newId = model.insertNewRecord();
  var rec   = model.getRecord(newId);       

  model.setValue(rec, "GIDER_TURU", "");
  model.setValue(rec, "KDV_ORANI", row["KDV Oranı"] || "");
  model.setValue(rec, "MASRAF_ACIKLAMA", row["Masraf Açıklama"] || "");
  model.setValue(rec, "HARCAMA_TUTARI", row["Harcama Tutarı"] || "");

  model.fetchRecords([ rec ], { refresh: true });
});


  statusDiv.textContent = "OCR tamamlandı. Alt kalemler yüklendi.";
})
.catch(function(err) {
  console.error("OCR error:", err);
  statusDiv.textContent = "Hata: " + (err.message || err);
});
