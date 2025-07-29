================================================================================
📘 README - YouTube Transcript to Detailed Notes Converter
================================================================================

This project is a Streamlit-based web application that allows users to convert any YouTube video into structured, educational content including detailed AI-powered summaries, translated transcripts, interactive mind maps, timestamped notes, and quiz questions.

It is especially useful for students, educators, and researchers who want to take efficient notes from video lectures or tutorials.

--------------------------------------------------------------------------------
📌 MAIN FEATURES
--------------------------------------------------------------------------------

1. 🔍 **Extract YouTube Transcript**
   - Automatically fetches transcript using the video link
   - Supports auto-detection and multiple languages

2. 🌍 **Translate Transcript**
   - Translates the transcript into your selected language using Google Translate

3. 🤖 **AI-Powered Summary**
   - Uses OpenRouter's DeepSeek model to generate detailed, well-structured summaries
   - Tailors output format based on video type (e.g., coding tutorial, educational, documentary)

4. 🧠 **Mind Map Generation**
   - Automatically generates a hierarchical JSON of key concepts
   - Visualizes it using PyVis and displays in the app as an HTML mind map

5. ❓ **Question Generator**
   - Creates 5 Multiple-Choice Questions (MCQs) and 5 Short Answer Questions from the transcript

6. ⏱️ **Timestamps with Notes**
   - Extracts time-stamped text from the transcript and creates direct YouTube links

7. 📜 **History Storage**
   - Stores previous video data (title, link, summary, timestamps) in a local SQLite database

--------------------------------------------------------------------------------
🛠 TECHNOLOGIES USED
--------------------------------------------------------------------------------

- `Streamlit` – User interface framework
- `yt-dlp` – For video metadata (not downloading full video)
- `YouTube Transcript API` – For fetching transcripts
- `OpenRouter + DeepSeek` – For AI-based summarization & question generation
- `Google Translator API` – For language translation
- `PyVis` – For generating mind map graphs
- `SQLite3` – Local database for storing history
- `Requests` – HTTP requests (e.g., thumbnails)
- `Subprocess` – Used with yt-dlp for CLI-level command execution

--------------------------------------------------------------------------------
📂 FILE STRUCTURE
--------------------------------------------------------------------------------

- `app.py`                → Main application script
- `requirements.txt`      → All required Python packages
- `cookies.txt`           → (Optional) For yt-dlp session cookies
- `youtube_history.db`    → Auto-generated SQLite database for saved videos
- `mind_map.html`         → Mind map file auto-generated from transcript
- `README.txt`            → This help document

--------------------------------------------------------------------------------
🌐 SUPPORTED LANGUAGES
--------------------------------------------------------------------------------

The following languages are supported for summary generation:

- English, Hindi, Spanish, French, German, Portuguese, Russian,
  Bengali, Tamil, Telugu, Marathi, Gujarati, Malayalam, Kannada, Punjabi, Urdu

--------------------------------------------------------------------------------
🚀 HOW TO SETUP & RUN LOCALLY
--------------------------------------------------------------------------------

🔧 STEP 1: Clone the repository

