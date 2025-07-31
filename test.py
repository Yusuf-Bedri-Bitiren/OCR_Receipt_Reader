import os
from main import run

SAMPLES_DIR = 'Karel/receipts'                  # Fişlerin olduğu klasör neyse aynı dir de güncelle

expected_outputs = {                            # manuel girme yeri
    "S1.jpg": {
        "Tarih": "18.05.2023",
        "Toplam": "756.37",
        "Toplam KDV": "9.33",
    },
    "S2.jpg": {
        "Tarih": "01.10.2019",
        "Toplam": "45.67",
        "Toplam KDV": "3.38",
    },    
    "S3.jpg": {
        "Tarih": "12.12.2019",
        "Toplam": "26.15",
        "Toplam KDV": "1.96",
    },
    "S4.jpg": {
        "Tarih": "21.03.2024",
        "Toplam": "1195.39",
        "Toplam KDV": "17.64",
    },
    "S5.jpg": {
        "Tarih": "30.04.2013",
        "Toplam": "316.86",
        "Toplam KDV": "40.77",
    },
    "S6.jpg": {
        "Tarih": "25.09.2024",
        "Toplam": "391.26",
        "Toplam KDV": "33.69",
    },
    "S7.jpg": {
        "Tarih": "11.02.2023",
        "Toplam": "347.08",
        "Toplam KDV": "10.72",
    },
    "S8.jpg": {
        "Tarih": "10.10.2020",
        "Toplam": "238.63",
        "Toplam KDV": "26.25",
    },
    "S9.jpg": {
        "Tarih": "29.08.2010",
        "Toplam": "7.09",
        "Toplam KDV": "0.53",
    },
    "S10.jpg": {
        "Tarih": "29.08.2010",
        "Toplam": "8.0",
        "Toplam KDV": "0.59",
    },
    "S11.jpg": {
        "Tarih": "28.07.2021",
        "Toplam": "115.7",
        "Toplam KDV": "12.05",
    },
    "S12.jpg": {
        "Tarih": "15.06.2014",
        "Toplam": "62.23",
        "Toplam KDV": "4.16",
    },
    "S13.jpg": {
        "Tarih": "28.02.2023",
        "Toplam": "489.04",
        "Toplam KDV": "43.1",
    },
    "S14.jpg": {
        "Tarih": "06.01.2020",
        "Toplam": "307.85",
        "Toplam KDV": "22.79",
    },
    "S15.jpg": {
        "Tarih": "16.06.2025",
        "Toplam": "315.79",
        "Toplam KDV": "3.29",
    },
    "S16.jpg": {
        "Tarih": "06.05.2024",
        "Toplam": "249.99",
        "Toplam KDV": "22.73",
    },
    "S17.jpg": {
        "Tarih": "04.03.2021",
        "Toplam": "3.45",
        "Toplam KDV": "0.26",
    },
    "S18.jpg": {
        "Tarih": "13.08.2023",
        "Toplam": "74.95",
        "Toplam KDV": "3.18",
    },
    "S19.jpg": {
        "Tarih": "06.07.2023",
        "Toplam": "821.09",
        "Toplam KDV": "8.13",
    },
    "S20.jpg": {
        "Tarih": "26.09.2022",
        "Toplam": "144.15",
        "Toplam KDV": "1.19",
    },
    "S21.jpg": {
        "Tarih": "11.03.2025",
        "Toplam": "119.2",
        "Toplam KDV": "1.18",
    },
    "S22.jpg": {
        "Tarih": "11.01.2023",
        "Toplam": "92.9",
        "Toplam KDV": "0.96",
    },
    "S23.jpg": {
        "Tarih": "07.04.2024",
        "Toplam": "194.0",
        "Toplam KDV": "12.9",
    },
    "S24.jpg": {
        "Tarih": "30.01.2022",
        "Toplam": "82.55",
        "Toplam KDV": "6.11",
    },
    "S25.jpg": {
        "Tarih": "01.02.2024",
        "Toplam": "427.42",
        "Toplam KDV": "46.6",
    },
    "S26.jpg": {
        "Tarih": "05.03.2024",
        "Toplam": "130.15",
        "Toplam KDV": "2.66",
    },
    "S27.jpg": {
        "Tarih": "03.02.2024",
        "Toplam": "70.5",
        "Toplam KDV": "0.7",
    },
    "S28.jpg": {
        "Tarih": "02.01.2019",
        "Toplam": "102.0",
        "Toplam KDV": "10.35",
    },
    "S29.jpg": {
        "Tarih": "08.02.2023",
        "Toplam": "30.75",
        "Toplam KDV": "1.53",
    },
    "S30.jpg": {
        "Tarih": "13.01.2024",
        "Toplam": "500.0",
        "Toplam KDV": "0.0",
    },
    "S31.jpg": {
        "Tarih": "12.07.2012",
        "Toplam": "21.45",
        "Toplam KDV": "1.59",
    }
}

FIELDS = ["Tarih", "Toplam", "Toplam KDV"]      # Field'lar, daha fazla eklenebilir

def test_receipts():
    total_fields = len(FIELDS) * len(expected_outputs)
    correct_fields = 0
    failed_receipts = 0

    for i in range(1, len(expected_outputs) + 1):
        filename = f"S{i}.jpg"
        filepath = os.path.join(SAMPLES_DIR, filename)

        if not os.path.exists(filepath):
            print(f"❌ Missing file: {filepath}")
            continue

        print(f"\n🧾 Testing {filename}...")
        predicted = run(filepath)
        expected = expected_outputs.get(filename)

        if not expected:
            print(f"⚠️ No expected result for {filename}, skipping.")
            continue

        receipt_passed = True

        for field in FIELDS:
            pred = str(predicted.get(field, "")).strip()
            exp = str(expected.get(field, "")).strip()

            if pred == exp:
                correct_fields += 1
                print(f"   ✅ {field}: got '{pred}'")
            else:
                receipt_passed = False
                print(f"   ❌ {field}: expected '{exp}', got '{pred}'")

        if receipt_passed:
            print(f"✅ All fields passed for {filename}")
        else:
            failed_receipts += 1

    accuracy = (correct_fields / total_fields) * 100

    print("\n📊 Test Summary:")
    print(f"✅ Correct fields: {correct_fields}/{total_fields}")
    print(f"❌ Incorrect fields: {total_fields - correct_fields}")
    print(f"🧾 Receipts with any error: {failed_receipts}/{len(expected_outputs)}")
    print(f"🎯 Accuracy: {accuracy:.2f}%")

if __name__ == "__main__":
    test_receipts()
