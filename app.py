from flask import Flask, render_template, request
import anthropic
import requests
import re
import os
import markdown

app = Flask(__name__)
client = anthropic.Anthropic()

def get_twitch_token():
    client_id = os.environ.get("TWITCH_CLIENT_ID")
    client_secret = os.environ.get("TWITCH_CLIENT_SECRET")
    
    response = requests.post("https://id.twitch.tv/oauth2/token", params={
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    })
    return response.json()["access_token"]

def get_game_image(game_name):
    try:
        client_id = os.environ.get("TWITCH_CLIENT_ID")
        token = get_twitch_token()
        
        response = requests.post(
            "https://api.igdb.com/v4/games",
            headers={
                "Client-ID": client_id,
                "Authorization": f"Bearer {token}"
            },
            data=f'search "{game_name}"; fields name,cover.url; where version_parent = null & cover != null; limit 1;'
        )
        
        games = response.json()
        if games and "cover" in games[0]:
            found_name = games[0].get("name", "").lower()
            search_name = game_name.lower()
            if any(word in found_name for word in search_name.split()):
                cover_url = games[0]["cover"]["url"]
                cover_url = cover_url.replace("t_thumb", "t_cover_big")
                return "https:" + cover_url
        return None
    except:
        return None

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/search", methods=["POST"])
def search():
    game_name = request.form["game"]
    
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"""Write a detailed game review for {game_name}.
                
Start your response with SCORE: X.X (just the number out of 10, nothing else on that line)
Then write the full review with pros, cons, and summary.
Format it clearly with headers."""
            }
        ]
    )
    
    full_response = message.content[0].text
    
    score = None
    score_match = re.search(r'SCORE:\s*(\d+\.?\d*)', full_response)
    if score_match:
        score = float(score_match.group(1))
        review = full_response.replace(score_match.group(0), '').strip()
        review = markdown.markdown(review)
    else:
        review = full_response
        review = markdown.markdown(review)
    
    image_url = get_game_image(game_name)
    if not image_url:
        image_url = f"https://picsum.photos/seed/{game_name.replace(' ', '')}/800/300"
    
    return render_template("index.html", 
                         review=review, 
                         game_name=game_name,
                         score=score,
                         image_url=image_url)

if __name__ == "__main__":
    app.run(debug=True)