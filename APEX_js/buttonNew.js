const fileInput   = apex.item('P1_FILE').element[0];
const rawOutput   = apex.item('P1_RAW_TEXT');
const jsonOutput  = apex.item('P1_JSON_FIELDS');

if (!fileInput.files.length) {
    alert('Lütfen bir fotoğraf yükleyin.');
    return;
}

const reader = new FileReader();
reader.onload = async function (e) {
    const dataUrl = e.target.result;

    const result = await Tesseract.recognize(dataUrl, 'tur', {
      tessedit_pageseg_mode: 6
    }); // Buraya ifReceipt ile çağırıp farklı psm mantığını button.js den almak lazım
    // Fiş mi değil mi booleanını field olarak alalım
    // Alper hoca burayı sallayın dedi ama şimdilik
    const rawText = result.data.text;
    rawOutput.setValue(rawText);

    const fields = extractFields(rawText);
    fields.Alt_Kalemler = parseItems(rawText, true);

    jsonOutput.setValue(JSON.stringify(fields, null, 2));
};

reader.readAsDataURL(fileInput.files[0]);