import requests

url = 'http://localhost:8000/matches/{match_id}/report_result/'

headers = {
    'Content-Type': 'application/json',
}

data = {
    "winning_side": "team_1",
    "bonuses": "Bonus for Team A",
    "penalties": "Penalty for Team B",
    "judge": {
        "name": "John Doe",
        "team": "Judging Team"
    },
    "substitutes": [
        {
            "team": "Team A",
            "tank": "T34",
            "rating": 3
        }
    ],
    "tanks_lost": {
        "M2A2": 3,
        "M2A4": 2
    }
}

response = requests.post(url, headers=headers, json=data)

if response.status_code == 201:
    print("Match result reported successfully.")
    print("Response data:", response.json())
else:
    print("Failed to report match result.")
    print("Status code:", response.status_code)
    print("Response data:", response.json())