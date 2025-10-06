import requests
r = requests.post("http://127.0.0.1:8000/convert",
                  json={"tsql": "SELECT TOP (5) ISNULL([Name],'N/A') FROM [dbo].[Users];"})
print(r.json())
