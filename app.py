import streamlit as st
import os
from youtube_transcript_api import YouTubeTranscriptApi
import re
from openai import OpenAI
import requests
from deep_translator import GoogleTranslator
import subprocess
import yt_dlp
from pyvis.network import Network
import json

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
        available_transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        avilable_langhuage = [t.language_code for t in available_transcripts]
        print("avilable langhe ====", avilable_langhuage)
        print(avilable_langhuage[0])
        # if lang not in [t.language_code for t in available_transcripts]:
        #     return f"No transcript found for language: {lang}"

        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[avilable_langhuage[0]])
        text = " ".join([entry['text'] for entry in transcript])
        return text
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
    model="deepseek/deepseek-chat-v3-0324:free",
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
            model="deepseek/deepseek-chat-v3-0324:free",
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


# def create_mind_map(topics, output_file="mind_map.html"):
#     """
#     Generates an interactive mind map from a YouTube transcript.
#
#     Parameters:
#     - transcript_text (str): Extracted text from YouTube video.
#     - output_file (str): Name of the output HTML file.
#
#     Returns:
#     - str: Path to the saved HTML file.
#     """
#     try:
#         net = Network(height="750px", width="100%", directed=True)
#
#         # Add the main node
#         parent = "YouTube Video Summary"
#         net.add_node(parent, label=parent, color="red")
#
#         # Add subtopics
#         for main_topic, subtopics in topics.items():
#             net.add_node(main_topic, label=main_topic, color="blue")
#             net.add_edge(parent, main_topic)  # Link to main topic
#
#             for sub in subtopics:
#                 net.add_node(sub, label=sub, color="lightblue")
#                 net.add_edge(main_topic, sub)  # Link subtopics
#
#         # Save the interactive graph
#         net.write_html(output_file)
#
#         return output_file
#     except Exception as e:
#         print("Error generating mind map:", str(e))
#         return None

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
        model="deepseek/deepseek-chat-v3-0324:free",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    return completion.choices[0].message.content

def extract_timestamps(transcript):
    timestamps = re.findall(r"\d{1,2}:\d{2}", transcript)
    return timestamps


dict={'English':'en','Hindi':'hi','Spanish':'es','French':'fr','German':'de','Portuguese':'pt','Russian':'ru','Bengali':'bn','Tamil':'ta','Telugu':'te','Marathi':'mr','Gujarati':'gu','Malayalam':'ml','Kannada':'kn','Punjabi':'pa','Urdu':'ur'}
#print(dict['English'])
language_options = ["English", "Hindi", "Spanish", "French", "German", "Portuguese", "Russian", "Bengali",
"Tamil", "Telugu", "Marathi", "Gujarati", "Malayalam", "Kannada", "Punjabi", "Urdu"]
st.title("YouTube Transcript to Detailed Notes Converter")
youtube_link = st.text_input("Enter YouTube Video Link:")

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
        # print("Description:", description)
        # print("Length (seconds):", length)
    transcript_text = get_transcript(youtube_link)
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
            st.write(topics)
        else:
            st.error("Failed to create mind map.")
        #generate_pdf(vedeo_text,title+""+".pdf")

        timestamps = extract_timestamps(transcript_text)
        video_id = extract_video_id(youtube_link)

        for time in timestamps:
            st.markdown(f"[{time}](https://www.youtube.com/watch?v={video_id}&t={time.replace(':', '')}s)")












