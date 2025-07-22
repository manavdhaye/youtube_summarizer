import streamlit as st
import os
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
import re
from openai import OpenAI
import requests
from deep_translator import GoogleTranslator
import subprocess
import yt_dlp
from pyvis.network import Network
import sqlite3
import json

st.sidebar.title("📜 History")

# Database setup
conn = sqlite3.connect("youtube_history.db")
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id TEXT UNIQUE,
        youtube_link TEXT,
        title TEXT,
        description TEXT,
        summary TEXT,
        timestamp_data TEXT
    )
""")
cursor.execute("SELECT video_id, title FROM history ORDER BY id DESC")
history_items = cursor.fetchall()
conn.close()

# Sidebar history buttons
for vid, title in history_items:
    if st.sidebar.button(title):
        st.query_params["video"] = vid  # ✅ REPLACED

# Read from query params
params = st.query_params  # ✅ REPLACED

if "video" in params:
    video_id = params["video"]
    if isinstance(video_id, list):  # In case it's a list
        video_id = video_id[0]
    conn = sqlite3.connect("youtube_history.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM history WHERE video_id = ?", (video_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        _, _, youtube_link, title, description, summary, timestamp_data = row
        st.image(f"http://img.youtube.com/vi/{video_id}/0.jpg")
        st.markdown(f"### {title}")
        st.write(summary)
        st.markdown("### ⏱️ Timestamps with Text")
        for ts, text in json.loads(timestamp_data):
            st.markdown(f"[{ts}](https://www.youtube.com/watch?v={video_id}&t={ts.replace(':', '')}s) — {text}")


def download_video(url):
  #url = "https://www.youtube.com/watch?v=9He4UBLyk8Y"
  cmd = ["yt-dlp", "--cookies", "cookies.txt", url]
  try:
      result = subprocess.run(cmd, capture_output=True, text=True, check=True)
      print(result.stdout)  # Print output
  except subprocess.CalledProcessError as e:
      print("Error:", e.stderr)  # Print error if it fails


def get_video_details(video_url):
    try:
        ydl_opts = {
            "quiet": True,  # Reduce output noise
            "noplaylist": True,  # Ensure only a single video is fetched
            "extractor_args": {
                "youtube": {"player_client": ["web"]}
            }  # Fixes YouTube extraction issue
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            title = info.get('title', 'No Title')
            description = info.get('description', 'No Description')
            length = info.get('duration', 0)  # Duration in seconds
            return title, description, length
    except Exception as e:
        return None, None, f"Error: {e}"


def extract_video_id(url):
    """Extracts the video ID from various YouTube URL formats."""
    match = re.search(r"(?:v=|be/|embed/|shorts/|watch\?v=|&v=|/v/)([a-zA-Z0-9_-]{11})", url)
    return match.group(1) if match else None


def get_transcript(video_url, lang='en'):
    video_id = extract_video_id(video_url)
    if not video_id:
        return "Invalid YouTube URL!"
    try:
        print("vedeo id =",video_id)
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        print("transcript_list",transcript_list)
        # Print available languages for debugging
        available_languages = [t.language_code for t in transcript_list]
        print("Available languages:", available_languages)

        # Try preferred language first
        if lang in available_languages:
            transcript = transcript_list.find_transcript([lang]).fetch()
            print("langhague =",lang)
        else:
            # Fallback: use first available language
            transcript = transcript_list.find_transcript(available_languages).fetch()
            print("langhague =",available_languages)

        # Format transcript as plain text
        formatter = TextFormatter()
        text = formatter.format_transcript(transcript)
        text = text.replace('\n', ' ')  # Remove line breaks
        return transcript, text
    except TranscriptsDisabled:
        return "Transcripts are disabled for this video."
    except NoTranscriptFound:
        return "No transcript found for the given language."
    except Exception as e:
        return f"Error: {e}"


def lang_translator(transcript,lang):
  translated_text = GoogleTranslator(source='auto', target=lang).translate(transcript)
  return translated_text


def get_completion(transcript_text,title,description,language):
  prompt =  f"""Given the following title, description, and transcript from a YouTube video, generate a well-structured and detailed summary in {language}. Identify the category of the video (e.g., coding tutorial, music video, educational content, documentary, or general discussion) and format the summary accordingly:

  - If the video is a **coding tutorial**: Extract the key concepts, explain the logic, and include relevant code snippets in a properly formatted manner.

  - If the video is a **music video**: Provide the full lyrics (if available) and explain the meaning or story behind the song.

  - If the video is an **educational video**: Summarize the main points, key takeaways, and explain technical terms or concepts in a simple manner.

  - If the video is a **documentary or discussion**: Summarize the major themes, arguments, and insights shared in the video.

Ensure that the summary is **clear, concise, and written in {language}**.

Transcript:
{title, description, transcript_text}"""


  client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",
  )

  completion = client.chat.completions.create(
    extra_headers={
      "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
      "X-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
    },
    extra_body={},
    model="deepseek/deepseek-r1:free",
    messages=[
      {
        "role": "user",
        "content":prompt
      }
    ]
  )
  return completion.choices[0].message.content


def generate_mind_map_data(transcript_text):
    prompt = f"""
       Extract key topics from the following transcript and structure them in a hierarchical format
       for a mind map. Return ONLY a JSON object with no explanations or additional text.

       Example output:
       ```json
       {{
           "Main Topic 1": ["Subtopic A", "Subtopic B"],
           "Main Topic 2": ["Subtopic C"]
       }}
       ```

       Transcript:
       {transcript_text}
       """

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key="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",
    )

    try:
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "<YOUR_SITE_URL>",  # Optional. Site URL for rankings on openrouter.ai.
                "X-Title": "<YOUR_SITE_NAME>",  # Optional. Site title for rankings on openrouter.ai.
            },
            extra_body={},
            model="deepseek/deepseek-r1:free",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        if not completion.choices:
            print("❌ Error: OpenAI response does not contain choices.")
            return {}

        response_text = completion.choices[0].message.content.strip()

        # Extract JSON part only
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        json_data = response_text[json_start:json_end]

        topics_dict = json.loads(json_data)
        return topics_dict  # Ensure it returns a dictionary

    except ValueError:  # ✅ Use ValueError instead of json.JSONDecodeError
        print("❌ Error parsing OpenAI response. Ensure the response is in valid JSON format.")
        print("Response received:", response_text)  # Debugging: Print raw response
        return {}  # Return empty dict if parsing fails

    except Exception as e:
        print("❌ Unexpected Error:", str(e))
        return {}  # Return empty dict in case of any other errors



def create_mind_map(topics, output_file="mind_map.html"):
    """
    Generates an interactive mind map from structured topics.

    Parameters:
    - topics (dict): Dictionary with subtopics and their key phrases.
    - output_file (str): Output HTML file.

    Returns:
    - str: Path to the generated HTML file.
    """
    try:
        net = Network(height="750px", width="100%", directed=True)

        # Main node (center)
        main_node = "YouTube Video Summary"
        net.add_node(main_node, label=main_node, color="red", shape="dot")

        # Add subtopics & key phrases
        for subtopic, key_phrases in topics.items():
            net.add_node(subtopic, label=subtopic, color="blue", shape="dot")
            net.add_edge(main_node, subtopic)  # Connect subtopic to main node

            for phrase in key_phrases:
                net.add_node(phrase, label=phrase, color="lightblue", shape="dot")
                net.add_edge(subtopic, phrase)  # Connect key phrases to subtopic

        # Save as HTML
        net.write_html(output_file)
        return output_file

    except Exception as e:
        st.error(f"Error generating mind map: {str(e)}")
        return None

def generate_questions(transcript_text):
    prompt = f"Generate 5 multiple-choice questions (MCQs) and 5 short-answer questions from this transcript:\n{transcript_text}"

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key="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",
    )

    completion = client.chat.completions.create(
        extra_headers={
            "HTTP-Referer": "<YOUR_SITE_URL>",  # Optional. Site URL for rankings on openrouter.ai.
            "X-Title": "<YOUR_SITE_NAME>",  # Optional. Site title for rankings on openrouter.ai.
        },
        extra_body={},
        model="deepseek/deepseek-r1:free",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    return completion.choices[0].message.content

def generate_timestamps(transcript_raw):
    try:
        timestamp_data = []
        for entry in transcript_raw:
            start_sec = int(entry.start)
            minutes = start_sec // 60
            seconds = start_sec % 60
            timestamp = f"{minutes}:{seconds:02d}"
            text = entry.text
            timestamp_data.append((timestamp, text))
        return timestamp_data
    except Exception as e:
        print(f"❌ Error generating timestamps: {e}")
        return []




dict={'English':'en','Hindi':'hi','Spanish':'es','French':'fr','German':'de','Portuguese':'pt','Russian':'ru','Bengali':'bn','Tamil':'ta','Telugu':'te','Marathi':'mr','Gujarati':'gu','Malayalam':'ml','Kannada':'kn','Punjabi':'pa','Urdu':'ur'}
#print(dict['English'])
language_options = ["English", "Hindi", "Spanish", "French", "German", "Portuguese", "Russian", "Bengali",
"Tamil", "Telugu", "Marathi", "Gujarati", "Malayalam", "Kannada", "Punjabi", "Urdu"]
st.title("YouTube Transcript to Detailed Notes Converter")
youtube_link = st.text_input("Enter YouTube Video Link:")

selected_language=''
video_id=''
transcript_text=''
if youtube_link:
    #video_id = youtube_link.split("=")[1]
    #print(video_id)
    download_video(youtube_link)
    video_id=extract_video_id(youtube_link)
    url = f"http://img.youtube.com/vi/{video_id}/0.jpg"
    response = requests.get(url)

    if response.status_code == 200:
        st.image(url, use_container_width=True)
        selected_language = st.selectbox("Select Language for Summary:", language_options)
        print(selected_language, type(selected_language))
        # Add a dropdown for selecting summary language
    else:
        st.error("Failed to load image. Check the video ID or network connection.")

    if st.button("Get Detailed Notes"):
        title, description, length = get_video_details(youtube_link)
        if length and "Error" in str(length):
            print(length)  # Print the error message
        else:
            print("Title:", title)
            print("Description:", description)
            print("Length (seconds):", length)
        transcript_raw, transcript_text = get_transcript(youtube_link)
        print("transcript_text =", transcript_text)
        if transcript_text:
            summary = get_completion(transcript_text,title,description,selected_language)
            st.markdown("## Detailed Notes:")
            st.write(summary)
            questions = generate_questions(transcript_text)
            st.markdown(questions)
            topics = generate_mind_map_data(transcript_text)
            print("topics ",topics)
            mind_map_path = create_mind_map(topics)
            print(f"✅ Mind map saved at: {mind_map_path}")
            # Generate mind map HTML
            if mind_map_path:
                with open(mind_map_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
                    # Render the mind map in Streamlit
                st.components.v1.html(html_content, height=750, scrolling=True)
                #st.write(topics)
            else:
                st.error("Failed to create mind map.")

            # Inside your `if st.button("Get Detailed Notes"):` block
            timestamps = generate_timestamps(transcript_raw)
            if timestamps:
                st.markdown("### ⏱️ Timestamps with Text")
                for timestamp, text in timestamps:
                    yt_link = f"https://www.youtube.com/watch?v={video_id}&t={timestamp.replace(':', '')}s"
                    st.markdown(f"**[{timestamp}]({yt_link})** — {text}")
            else:
                st.warning("No timestamps found or transcript unavailable.")

            # Save history into the database
            conn = sqlite3.connect("youtube_history.db")
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO history (video_id, youtube_link, title, description, summary, timestamp_data)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    video_id,
                    youtube_link,
                    title,
                    description,
                    summary,
                    json.dumps(timestamps)  # Save timestamp data as JSON string
                ))
                conn.commit()
                st.success("✅ Video history saved successfully!")
            except Exception as e:
                st.warning(f"⚠️ Failed to save video history: {e}")
            finally:
                conn.close()
