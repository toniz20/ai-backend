import os
import json
import time
import requests
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_FREE_GEMINI_API_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")  # Optional, for auto-commit

# ============================================================
# STEP 1: FETCH TRENDING AI TOOLS FROM THE WEB
# ============================================================
def fetch_hackernews_tools():
    """Get top AI-related stories from Hacker News."""
    print("📡 Fetching trending AI tools from Hacker News...")
    try:
        # Get top 100 stories
        top_ids = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json").json()[:100]
        tools = []
        ai_keywords = ["AI", "GPT", "LLM", "ChatGPT", "Gemini", "Claude", "Mistral", "Copilot", "Sora", "Runway", "Midjourney"]

        for story_id in top_ids:
            story = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json").json()
            if not story or "title" not in story:
                continue
            title = story.get("title", "")
            url = story.get("url", "")
            # Check if it's AI-related
            if any(kw.lower() in title.lower() for kw in ai_keywords):
                tools.append({
                    "name": title.split(":")[0].split("-")[0].strip()[:50],
                    "url": url or f"https://news.ycombinator.com/item?id={story_id}",
                    "source": "HackerNews"
                })
            time.sleep(0.1)  # Be polite to the API
        return tools
    except Exception as e:
        print(f"⚠️ HackerNews fetch error: {e}")
        return []

def fetch_github_ai_tools():
    """Fetch trending AI repos from GitHub."""
    print("📡 Fetching trending AI repos from GitHub...")
    try:
        url = "https://api.github.com/search/repositories?q=ai+tool+language:python&sort=stars&order=desc&per_page=20"
        headers = {"Accept": "application/vnd.github.v3+json"}
        response = requests.get(url, headers=headers)
        data = response.json()
        tools = []
        for repo in data.get("items", []):
            tools.append({
                "name": repo["name"].replace("-", " ").title(),
                "url": repo["html_url"],
                "description": repo.get("description", ""),
                "source": "GitHub"
            })
        return tools
    except Exception as e:
        print(f"⚠️ GitHub fetch error: {e}")
        return []

# ============================================================
# STEP 2: USE GEMINI AI TO GENERATE STRUCTURED DATA
# ============================================================
def generate_ai_content(tools_list):
    """Use Gemini to generate descriptions, categories, and emojis."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_FREE_GEMINI_API_KEY":
        print("⚠️ No Gemini API key. Using fallback content.")
        return generate_fallback_content(tools_list)

    print("🤖 Generating AI descriptions and categories...")

    # Build prompt
    tool_names = [t["name"] for t in tools_list[:15]]  # Limit to 15 per run
    prompt = f"""
    Given these AI tool names: {', '.join(tool_names)}.
    For each tool, return a JSON array with:
    - name (string)
    - description (short, 1 sentence)
    - category (writing, image, video, seo, productivity, business)
    - icon_emoji (relevant emoji)
    - url (string)

    Example:
    [{{"name":"ChatGPT","description":"AI chatbot for writing and coding.","category":"writing","icon_emoji":"💬","url":"https://chat.openai.com"}}]

    Return ONLY the JSON array, no other text.
    """

    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/model = genai.GenerativeModel('gemini-2.0-flash'):generateContent?key={GEMINI_API_KEY}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.7}
            },
            timeout=30
        )
        
        # Check for API errors
        if response.status_code != 200:
            print(f"⚠️ Gemini API Error {response.status_code}: {response.text}")
            print("⚠️ Falling back to basic descriptions.")
            return generate_fallback_content(tools_list)

        data = response.json()
        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "[]")
        
        # Extract JSON from the response
        import re
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if json_match:
            parsed_tools = json.loads(json_match.group())
            if len(parsed_tools) == 0:
                print("⚠️ Gemini returned an empty list. Using fallback content.")
                return generate_fallback_content(tools_list)
            return parsed_tools
        else:
            print("⚠️ Gemini returned no JSON data. Using fallback content.")
            return generate_fallback_content(tools_list)
    except Exception as e:
        print(f"⚠️ Gemini API error: {e}")
        return generate_fallback_content(tools_list)

def generate_fallback_content(tools_list):
    """Fallback: generate basic content without AI."""
    categories = ["writing", "image", "video", "seo", "productivity", "business"]
    emojis = ["✍️", "🎨", "🎬", "📈", "⚡", "💼"]
    tools = []
    for i, t in enumerate(tools_list[:20]):
        tools.append({
            "name": t["name"],
            "description": f"AI tool for {categories[i % len(categories)]} — {t.get('description', 'Discover this AI tool.')}",
            "category": categories[i % len(categories)],
            "icon_emoji": emojis[i % len(emojis)],
            "url": t.get("url", "#"),
            "featured": i % 5 == 0  # Every 5th tool is featured
        })
    return tools

# ============================================================
# STEP 3: MERGE WITH EXISTING DATA & SAVE
# ============================================================
def load_existing_tools():
    """Load existing tools from tools.json."""
    try:
        with open("tools.json", "r") as f:
            data = json.load(f)
            return data.get("tools", [])  # <--- Fixed crash here
    except:
        return []

def save_tools(tools):
    """Save tools to tools.json with timestamp."""
    # Deduplicate by name (keep the most recent)
    seen = set()
    unique_tools = []
    for tool in tools:
        if tool["name"] not in seen:
            seen.add(tool["name"])
            unique_tools.append(tool)

    # Add timestamp
    data = {
        "last_updated": datetime.now().isoformat(),
        "total_tools": len(unique_tools),
        "tools": unique_tools
    }

    with open("tools.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"✅ Saved {len(unique_tools)} tools to tools.json")
    return data

# ============================================================
# STEP 4: AUTO-COMMIT TO GITHUB (Optional)
# ============================================================
def auto_commit():
    """Commit changes to GitHub using the API."""
    if not GITHUB_TOKEN:
        return
    print("📤 Auto-committing to GitHub...")
    # This would use the GitHub API to update the file
    # For simplicity, we skip this in the demo—you can set up GitHub Actions instead.

# ============================================================
# STEP 5: MAIN ROUTINE
# ============================================================
def main():
    print("🚀 Starting AI Tools Directory Automation")

    # Step 1: Fetch raw data from multiple sources
    all_tools = []
    all_tools.extend(fetch_hackernews_tools())
    all_tools.extend(fetch_github_ai_tools())

    if not all_tools:
        print("⚠️ No tools fetched. Keeping existing data.")
        return

    # Step 2: Generate AI-powered content
    enriched_tools = generate_ai_content(all_tools)

    # Step 3: Merge with existing data
    existing = load_existing_tools()
    # Combine, keeping existing featured status
    existing_names = {t["name"]: t for t in existing}
    for tool in enriched_tools:
        if tool["name"] in existing_names:
            tool["featured"] = existing_names[tool["name"]].get("featured", False)

    # Step 4: Save to tools.json
    save_tools(enriched_tools)

    print("✅ Automation complete!")

if __name__ == "__main__":
    main()