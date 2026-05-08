import psycopg2

conn = psycopg2.connect(
    host="192.168.100.149",   # ← just the IP, no http:// or /
    port=5432,
    database="mydb",
    user="AIJLX",
    password="AIJLX9211"
)

print("✓ Postgres connected!")
cursor = conn.cursor()
cursor.execute("SELECT version();")
print(cursor.fetchone())
conn.close()