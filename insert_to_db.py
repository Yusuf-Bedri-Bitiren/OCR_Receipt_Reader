import os
import pyodbc
from main import run

conn = pyodbc.connect( #MSSQL Setup
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=localhost\\SQLEXPRESS06;"   #Server name---------------------- CHANGE
    "Database=KarelOCR;"                #Database  ---------------------- CHANGE
    "Trusted_Connection=yes;"
)
cursor = conn.cursor()

image_dir = "Karel/receipts"        #Image directory ---------------------- CHANGE
image_files = [f"S{i}.jpg" for i in range(1, 36)]  #Image names ---------------------- CHANGE

print("Code starts")

for filename in image_files:
    path = os.path.join(image_dir, filename)
    print(f"\nProcessing {filename}...")

    try:
        result = run(path, test=False)

        if not result or "Toplam" not in result:
            print(f"Skipping {filename} — 'Toplam' missing.")
            continue

        doc_type = "Bill" if "Fatura No" in result else "Receipt"

        insert_query = """
        INSERT INTO Documents (
            DocumentType, FisNo, FaturaNo, BelgeTarihi, Toplam, ToplamKDV,
            KDVOrani, TicaretSicilNo, MersisNo, ETTN, ImagePath
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        raw_date = result.get("Tarih")         # Date Fix DD.MM.YYYY → YYYY-MM-DD for SQL
        sql_date = None
        if raw_date:
            try:
                day, month, year = raw_date.split(".")
                sql_date = f"{year}-{month}-{day}"
            except Exception as e:
                print(f"Invalid date format in {filename}: {raw_date}")

        values = (
            doc_type,
            result.get("Fiş No"),
            result.get("Fatura No"),
            sql_date,
            result["Toplam"],                     # NOT NULL
            result.get("Toplam KDV"),
            result.get("KDV Oranı"),
            result.get("Ticaret Sicil No"),
            result.get("Mersis No"),
            result.get("ETTN"),
            path.replace("\\", "/")
        )

        cursor.execute(insert_query, values)
        conn.commit()
        print(f"Inserted {filename} into database.")

    except Exception as e:
        print(f"Error processing {filename}: {e}")

cursor.close()
conn.close()

print("\n Code ends")
