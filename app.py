import os
import requests
from flask import Flask, request, Response

app = Flask(__name__)

# --- LLM API Configuration ---
# The API key will be automatically provided by the Canvas environment for gemini-2.0-flash.
# Keep this as an empty string.
API_KEY = "AIzaSyBBTu7LmZkXPGweEsBtr02AVuNgdslzDfQ"
LLM_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

# --- Helper Functions for Text Processing and Metrics ---

def calculate_metrics(original_text, corrected_text):
    """
    Calculates various metrics by comparing original and corrected text.
    These are heuristic calculations as LLMs don't provide direct error counts.
    """
    original_words = original_text.split()
    corrected_words = corrected_text.split()

    total_original_words = len(original_words)
    total_corrected_words = len(corrected_words)

    errors = 0
    correct_words = 0
    # Simple word-by-word comparison for error and correct word count
    for i in range(min(total_original_words, total_corrected_words)):
        if original_words[i] != corrected_words[i]:
            errors += 1
        else:
            correct_words += 1
    # Add remaining words from the longer text as errors if lengths differ
    errors += abs(total_original_words - total_corrected_words)

    accuracy_rate = 0.0
    if total_original_words > 0:
        accuracy_rate = ((total_original_words - errors) / total_original_words) * 100

    # "Missing Data Per Count Time" interpreted as difference in word count
    missing_data_per_count_time = abs(total_original_words - total_corrected_words)

    # "Needs Suggestions": 1 if any errors, 0 otherwise
    needs_suggestions = 1 if errors > 0 else 0

    # "Auto Assistant Becomes 0": If suggestions were needed, assume manual intervention implied.
    auto_assistant_becomes_0 = 1 if needs_suggestions == 1 else 0 # Changed to 1 if manual needed. 0 if full auto.

    return {
        "errors": errors,
        "accuracy_rate": f"{accuracy_rate:.2f}%",
        "correct_words": correct_words,
        "missing_data_per_count_time": missing_data_per_count_time,
        "needs_suggestions": needs_suggestions,
        "auto_assistant_becomes_0": auto_assistant_becomes_0,
    }

def call_llm(prompt_text):
    """
    Makes a call to the Gemini LLM API.
    """
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt_text}]
            }
        ],
        # Add generation config for structured output if needed, but for simple text, it's not strictly necessary.
        # For this use case, we expect plain text back.
        "generationConfig": {
            "temperature": 0.7, # Lower temperature for more deterministic, factual corrections
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 1000
        }
    }
    try:
        response = requests.post(LLM_API_URL, json=payload, headers=headers)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        result = response.json()
        if result and result.get('candidates') and result['candidates'][0].get('content') and result['candidates'][0]['content'].get('parts'):
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            print("LLM response structure unexpected:", result)
            return "Error: Could not get a valid response from the AI."
    except requests.exceptions.RequestException as e:
        print(f"Error calling LLM API: {e}")
        return f"Error: Could not connect to AI. ({e})"
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return f"Error: An internal error occurred. ({e})"

def generate_html(
    input_word_correction="", output_word_correction="", metrics_word_correction=None,
    input_sentence_correction="", output_sentence_correction="", metrics_sentence_correction=None,
    input_command_correction="", output_command_correction="", metrics_command_correction=None,
    input_space_correction="", output_space_correction="", metrics_space_correction=None
):
    """
    Generates the complete HTML page content as a string, including all sections
    and dynamically populating results if provided.
    """
    # Default metrics if not provided
    default_metrics = {
        "errors": "-", "accuracy_rate": "-", "correct_words": "-",
        "missing_data_per_count_time": "-", "needs_suggestions": "-", "auto_assistant_becomes_0": "-"
    }
    metrics_word_correction = metrics_word_correction or default_metrics
    metrics_sentence_correction = metrics_sentence_correction or default_metrics
    metrics_command_correction = metrics_command_correction or default_metrics
    metrics_space_correction = metrics_space_correction or default_metrics

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Virtual Typing Assistant</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            background-color: #F0F4F8; /* Light blue-gray background */
            color: #2D3748; /* Dark text */
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 2rem auto;
            padding: 2rem;
            background-color: #FFFFFF; /* White card background */
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            border-radius: 1rem;
        }}
        .block-section {{
            background-color: #F8FAFC; /* Lighter background for sections */
            border-radius: 0.75rem;
            padding: 1.5rem;
            margin-bottom: 2rem;
            border: 1px solid #E2E8F0; /* Light border */
        }}
        h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            color: #1A202C;
            text-align: center;
            margin-bottom: 2rem;
        }}
        h2 {{
            font-size: 1.8rem;
            font-weight: 600;
            color: #2C5282; /* Blue heading */
            margin-bottom: 1.5rem;
            border-bottom: 2px solid #BFDBFE; /* Light blue underline */
            padding-bottom: 0.5rem;
        }}
        label {{
            font-weight: 500;
            color: #4A5568;
            margin-bottom: 0.5rem;
            display: block;
        }}
        textarea {{
            width: 100%;
            padding: 1rem;
            border: 1px solid #CBD5E0;
            border-radius: 0.5rem;
            font-size: 1rem;
            background-color: #FFFFFF;
            resize: vertical;
            min-height: 100px;
        }}
        button {{
            background-color: #4C51BF; /* Darker blue button */
            color: white;
            padding: 0.75rem 1.5rem;
            border-radius: 0.5rem;
            border: none;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            transition: background-color 0.3s ease, transform 0.2s ease;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        button:hover {{
            background-color: #434190; /* Even darker blue on hover */
            transform: translateY(-2px);
        }}
        .result-box {{
            background-color: #EBF8FF; /* Very light blue for results */
            border: 1px dashed #90CDF4;
            border-radius: 0.5rem;
            padding: 1rem;
            margin-top: 1.5rem;
            font-family: 'Courier New', monospace;
            white-space: pre-wrap; /* Preserve whitespace and wrap text */
            word-wrap: break-word; /* Break long words */
            min-height: 50px;
            color: #2A4365; /* Dark blue for result text */
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-top: 1.5rem;
        }}
        .metric-item {{
            background-color: #E0F2F7; /* Another light background for metrics */
            border-radius: 0.5rem;
            padding: 1rem;
            text-align: center;
            font-size: 0.95rem;
            font-weight: 500;
            color: #2D3748;
            box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.05);
        }}
        .metric-item strong {{
            display: block;
            font-size: 1.2rem;
            color: #3182CE; /* Blue for metric values */
            margin-top: 0.25rem;
        }}
        footer {{
            text-align: center;
            margin-top: 3rem;
            padding-top: 1.5rem;
            border-top: 1px solid #CBD5E0;
            color: #718096;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Virtual Typing Assistant</h1>

        <!-- Block 1: Misspelled Words to Correctly Spelled Words -->
        <div class="block-section">
            <h2>1. Misspelled Words Correction</h2>
            <form method="POST" action="/">
                <input type="hidden" name="action" value="word_correction">
                <label for="input_word_correction">Enter misspelled words:</label>
                <textarea id="input_word_correction" name="input_text" rows="4" placeholder="e.g., mispelled wrods for corecction" class="rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500">{input_word_correction}</textarea>
                <button type="submit" class="mt-4 rounded-lg">Correct Words</button>

                <h3 class="text-lg font-semibold text-gray-700 mt-6 mb-3">Results:</h3>
                <div class="result-box rounded-lg shadow-inner">
                    {output_word_correction}
                </div>
                <div class="metrics">
                    <div class="metric-item rounded-lg">Errors: <strong>{metrics_word_correction['errors']}</strong></div>
                    <div class="metric-item rounded-lg">Accuracy Rate: <strong>{metrics_word_correction['accuracy_rate']}</strong></div>
                    <div class="metric-item rounded-lg">Correct Words: <strong>{metrics_word_correction['correct_words']}</strong></div>
                    <div class="metric-item rounded-lg">Missing Data per Count Time: <strong>{metrics_word_correction['missing_data_per_count_time']}</strong></div>
                    <div class="metric-item rounded-lg">Needs Suggestions: <strong>{metrics_word_correction['needs_suggestions']}</strong></div>
                    <div class="metric-item rounded-lg">Auto Assistant Becomes 0: <strong>{metrics_word_correction['auto_assistant_becomes_0']}</strong></div>
                </div>
                <p class="text-sm text-gray-600 mt-4">Correct Answer should get the Correct Answer, and Auto Assistant becomes 0 if manual suggestions are needed.</p>
            </form>
        </div>

        <!-- Block 2: Misspelled Sentences to Correctly Spelled Sentences -->
        <div class="block-section">
            <h2>2. Misspelled Sentences Correction</h2>
            <form method="POST" action="/">
                <input type="hidden" name="action" value="sentence_correction">
                <label for="input_sentence_correction">Enter misspelled sentences:</label>
                <textarea id="input_sentence_correction" name="input_text" rows="4" placeholder="e.g., this is a gramatticaly uncorrect sentance." class="rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500">{input_sentence_correction}</textarea>
                <button type="submit" class="mt-4 rounded-lg">Correct Sentences</button>

                <h3 class="text-lg font-semibold text-gray-700 mt-6 mb-3">Results:</h3>
                <div class="result-box rounded-lg shadow-inner">
                    {output_sentence_correction}
                </div>
                <div class="metrics">
                    <div class="metric-item rounded-lg">Errors: <strong>{metrics_sentence_correction['errors']}</strong></div>
                    <div class="metric-item rounded-lg">Accuracy Rate: <strong>{metrics_sentence_correction['accuracy_rate']}</strong></div>
                    <div class="metric-item rounded-lg">Correct Words: <strong>{metrics_sentence_correction['correct_words']}</strong></div>
                    <div class="metric-item rounded-lg">Missing Data per Count Time: <strong>{metrics_sentence_correction['missing_data_per_count_time']}</strong></div>
                    <div class="metric-item rounded-lg">Needs Suggestions: <strong>{metrics_sentence_correction['needs_suggestions']}</strong></div>
                    <div class="metric-item rounded-lg">Auto Assistant Becomes 0: <strong>{metrics_sentence_correction['auto_assistant_becomes_0']}</strong></div>
                </div>
                 <p class="text-sm text-gray-600 mt-4">Correct Answer should get the Correct Answer, and Auto Assistant becomes 0 if manual suggestions are needed.</p>
            </form>
        </div>

        <!-- Block 3: Wrong Commands to Correct Commands -->
        <div class="block-section">
            <h2>3. Command Correction</h2>
            <form method="POST" action="/">
                <input type="hidden" name="action" value="command_correction">
                <label for="input_command_correction">Enter a wrong command:</label>
                <textarea id="input_command_correction" name="input_text" rows="4" placeholder="e.g., open da fiile on dekstop" class="rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500">{input_command_correction}</textarea>
                <button type="submit" class="mt-4 rounded-lg">Correct Command</button>

                <h3 class="text-lg font-semibold text-gray-700 mt-6 mb-3">Results:</h3>
                <div class="result-box rounded-lg shadow-inner">
                    {output_command_correction}
                </div>
                <div class="metrics">
                    <div class="metric-item rounded-lg">Errors: <strong>{metrics_command_correction['errors']}</strong></div>
                    <div class="metric-item rounded-lg">Accuracy Rate: <strong>{metrics_command_correction['accuracy_rate']}</strong></div>
                    <div class="metric-item rounded-lg">Correct Words: <strong>{metrics_command_correction['correct_words']}</strong></div>
                    <div class="metric-item rounded-lg">Missing Data per Count Time: <strong>{metrics_command_correction['missing_data_per_count_time']}</strong></div>
                    <div class="metric-item rounded-lg">Needs Suggestions: <strong>{metrics_command_correction['needs_suggestions']}</strong></div>
                    <div class="metric-item rounded-lg">Auto Assistant Becomes 0: <strong>{metrics_command_correction['auto_assistant_becomes_0']}</strong></div>
                </div>
                 <p class="text-sm text-gray-600 mt-4">Correct Answer should get the Correct Answer, and Auto Assistant becomes 0 if manual suggestions are needed.</p>
            </form>
        </div>

        <!-- Block 4: Wrong Spaces to Right Spaces -->
        <div class="block-section">
            <h2>4. Spacing Correction</h2>
            <form method="POST" action="/">
                <input type="hidden" name="action" value="space_correction">
                <label for="input_space_correction">Enter text with wrong spacing:</label>
                <textarea id="input_space_correction" name="input_text" rows="4" placeholder="e.g., Thisis badlyspaced text with toomany or toolittle spaces." class="rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500">{input_space_correction}</textarea>
                <button type="submit" class="mt-4 rounded-lg">Correct Spacing</button>

                <h3 class="text-lg font-semibold text-gray-700 mt-6 mb-3">Results:</h3>
                <div class="result-box rounded-lg shadow-inner">
                    {output_space_correction}
                </div>
                <div class="metrics">
                    <div class="metric-item rounded-lg">Errors: <strong>{metrics_space_correction['errors']}</strong></div>
                    <div class="metric-item rounded-lg">Accuracy Rate: <strong>{metrics_space_correction['accuracy_rate']}</strong></div>
                    <div class="metric-item rounded-lg">Correct Words: <strong>{metrics_space_correction['correct_words']}</strong></div>
                    <div class="metric-item rounded-lg">Missing Data per Count Time: <strong>{metrics_space_correction['missing_data_per_count_time']}</strong></div>
                    <div class="metric-item rounded-lg">Needs Suggestions: <strong>{metrics_space_correction['needs_suggestions']}</strong></div>
                    <div class="metric-item rounded-lg">Auto Assistant Becomes 0: <strong>{metrics_space_correction['auto_assistant_becomes_0']}</strong></div>
                </div>
                <p class="text-sm text-gray-600 mt-4">Correct Answer should get the Correct Answer, and Auto Assistant becomes 0 if manual suggestions are needed.</p>
            </form>
        </div>
    </div>
    <footer>
        <p>&copy; 2024 Virtual Typing Assistant. All rights reserved.</p>
    </footer>
</body>
</html>
    """
    return html_content

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Handles both GET and POST requests for the main page.
    On POST, it processes the input using LLM and regenerates the HTML with results.
    """
    if request.method == 'POST':
        action = request.form.get('action')
        input_text = request.form.get('input_text', '')
        
        corrected_output = ""
        metrics = None
        prompt_prefix = ""

        if action == "word_correction":
            prompt_prefix = "Correct the spelling of these words: "
        elif action == "sentence_correction":
            prompt_prefix = "Correct the grammar and spelling of this sentence: "
        elif action == "command_correction":
            # This task is highly dependent on context, making a general LLM prompt challenging.
            # We'll ask it to interpret and correct.
            prompt_prefix = "Interpret and correct this natural language command. Output only the corrected command: "
        elif action == "space_correction":
            prompt_prefix = "Correct the spacing in this text. Output only the text with corrected spacing: "
        
        full_prompt = f"{prompt_prefix}{input_text}"
        corrected_output = call_llm(full_prompt)
        metrics = calculate_metrics(input_text, corrected_output)

        # Regenerate the entire page with the results for the specific block
        # and preserve input for the submitted block
        if action == "word_correction":
            return Response(generate_html(
                input_word_correction=input_text,
                output_word_correction=corrected_output,
                metrics_word_correction=metrics
            ), mimetype='text/html')
        elif action == "sentence_correction":
            return Response(generate_html(
                input_sentence_correction=input_text,
                output_sentence_correction=corrected_output,
                metrics_sentence_correction=metrics
            ), mimetype='text/html')
        elif action == "command_correction":
            return Response(generate_html(
                input_command_correction=input_text,
                output_command_correction=corrected_output,
                metrics_command_correction=metrics
            ), mimetype='text/html')
        elif action == "space_correction":
            return Response(generate_html(
                input_space_correction=input_text,
                output_space_correction=corrected_output,
                metrics_space_correction=metrics
            ), mimetype='text/html')
        
    # Initial GET request or unknown action: render the empty form
    return Response(generate_html(), mimetype='text/html')

if __name__ == '__main__':
    # When running locally, set debug=True for development.
    # For deployment in a production environment, debug should be False.
    # In the Canvas environment, this will be handled automatically.
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('PORT', 5000))
