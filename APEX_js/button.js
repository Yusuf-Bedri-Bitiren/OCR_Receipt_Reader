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
    const psmModes = [
        Tesseract.PSM.SINGLE_BLOCK,  // 6
        Tesseract.PSM.SPARSE_TEXT,   // 11
        Tesseract.PSM.SINGLE_COLUMN, // 4
        Tesseract.PSM.AUTO           // 3
    ];

    const allFieldResults = [];
    const allRawTexts = [];

    for (const mode of psmModes) {
        const worker = await Tesseract.createWorker({
            // logger: m => console.log(`[PSM ${mode}]`, m)
        });

        await worker.loadLanguage('tur');
        await worker.initialize('tur');
        await worker.setParameters({ tessedit_pageseg_mode: mode });

        const { data: { text } } = await worker.recognize(dataUrl);

        console.log(`--- PSM ${mode} OUTPUT ---\n${text}\n`);

        const fields = extractFields(text);
        const components =  parseItems(text, true); //Burada bıraktım, alt kalemleri kendi arasında oy verdirtmek imkansız çünkü label adları saçma sapan
        allFieldResults.push(fields);

        allRawTexts.push(text);

        await worker.terminate();
    }

    const mergedFields = mergeFieldResults(allFieldResults);
    rawOutput.setValue(allRawTexts);
    
    jsonOutput.setValue(JSON.stringify(mergedFields, null, 2));
};

reader.readAsDataURL(fileInput.files[0]);
