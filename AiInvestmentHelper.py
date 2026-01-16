# Install dependencies locally: pip install aisuite[all] gradio

import os
import random
import aisuite as ai
import gradio as gr

# ---- API Key (Groq) ----
# Set your GROQ_API_KEY environment variable before running this script
# For example: export GROQ_API_KEY=your_key_here
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("Please set the GROQ_API_KEY environment variable")
os.environ["GROQ_API_KEY"] = api_key

# ---- Model setup ----
client = ai.Client()
provider = "groq"
planner_model = "gemma2-9b-it"
writer_model = "gemma2-9b-it"

# Optional: chat history (Gradio already keeps history, but you can keep this if you want)
history = []

# ---- Preset question buttons ----
question_sets = {
    "Funds": [
        "What is an index fund?",
        "Are funds suitable for long-term investing?",
        "How should a beginner choose a suitable fund?"
    ],
    "Bonds": [
        "Is now a good time to invest in bonds?",
        "Are bonds less risky than stocks?",
        "What types of bonds are suitable for conservative investors?"
    ],
    "Foreign Currency": [
        "Which is better: USD time deposit or USD bonds?",
        "Can I invest in funds using foreign currency?",
        "Will FX volatility affect foreign-currency funds?"
    ],
    "Macro": [
        "With current economic uncertainty, how should I allocate assets?",
        "What investment themes are worth watching right now?",
        "Will inflation continue? How should I respond?"
    ]
}

# ---- Step 1: Generate 5 investment reasons ----
def generate_reasons(user_question: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "Based on the user's question, list five clear and constructive reasons explaining why, "
                "in this scenario, it may make sense to consider non-trading financial products such as "
                "funds or bonds.\n"
                "Rewrite the user's question as a title and respond in bullet points.\n"
                "Example: If the user asks 'Can I invest in funds using foreign currency?', your title should be "
                "'Can I invest in funds using foreign currency? Here are five reasons worth considering:'"
            )
        },
        {"role": "user", "content": user_question}
    ]

    resp = client.chat.completions.create(
        model=f"{provider}:{planner_model}",
        messages=messages
    )
    return resp.choices[0].message.content.strip()

# ---- Step 2: Classify question type (routing) ----
def classify_question_type(user_input: str) -> str:
    text = user_input.lower()

    # Knowledge-based: definitions / differences / comparisons
    if any(k in text for k in ["what is", "define", "definition", "difference", "compare", "vs", "versus"]):
        return "Knowledge"

    # Advice-based: general recommendations
    elif any(k in text for k in ["how to invest", "what should i buy", "recommend", "suggest", "i want to invest"]):
        return "Advice"

    # Personalized: suitability / personal situation
    elif any(k in text for k in ["is it suitable for me", "for my situation", "i have", "i am", "my current", "i want"]):
        return "Personalized"

    # Fallback
    else:
        return "Mixed"

# ---- Step 3: Generate the final advice ----
def generate_advice(reasons: str, question_type: str = "Advice") -> str:
    if question_type == "Knowledge":
        system_prompt = (
            "You are a financial education expert. Use a concise and professional tone to explain the concept.\n"
            "Give three bullet points, then add one final sentence explaining how this concept relates to funds or bonds."
        )
    elif question_type == "Personalized":
        system_prompt = (
            "You are a financial advisor. Based on the context below, provide personalized guidance.\n"
            "Offer three sample asset allocation mixes: Conservative, Balanced, Aggressive (use percentages).\n"
            "Explain who each mix fits. Clearly emphasize: this is not financial advice."
        )
    else:
        system_prompt = (
            "You are a professional investment consultant. Based on the reasons below, provide practical guidance.\n"
            "Use a calm, professional tone. Include suggested asset directions, example allocation ratios, and suitable profiles.\n"
            "End with a disclaimer: For educational purposes only."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": reasons}
    ]

    resp = client.chat.completions.create(
        model=f"{provider}:{writer_model}",
        messages=messages
    )
    return resp.choices[0].message.content.strip()

# ---- Gradio main chatbot function ----
def chatbot(user_input, chat_history):
    reasons = generate_reasons(user_input)
    qtype = classify_question_type(user_input)
    advice = generate_advice(reasons, qtype)

    full_response = (
        "<div style='background-color:#f8f9fa;border-radius:10px;padding:10px'>"
        "🤖 <b>Investment Reasons</b><br>"
        f"{reasons}<br><br>"
        f"✅ <b>Recommendation ({qtype})</b><br>"
        f"{advice}"
        "</div>"
    )

    chat_history.append((f"{user_input}", full_response))
    return "", chat_history

def set_and_submit(topic):
    q = random.choice(question_sets[topic])
    return q, gr.update()

# ---- Build Gradio UI ----
with gr.Blocks(
    theme=gr.themes.Soft(),
    css="""
    .circle-btn button {
        border-radius: 50px !important;
        padding: 12px 20px !important;
        font-size: 16px;
        background-color: #f0f2f5;
        border: 1px solid #d0d4d9;
    }
    .gr-textbox textarea {
        font-size: 16px;
        border-radius: 12px;
    }
    .gr-button {
        font-size: 16px;
    }
    """
) as demo:
    gr.Markdown("""
    <div style='text-align:center;'>
      <h2>AI Investment Helper</h2>
      <p>Ask one simple question to understand directions for funds and bonds</p>
    </div>
    """)

    chatbot_interface = gr.Chatbot(label="", height=400)
    user_input = gr.Textbox(label="", placeholder="Type your investment question here...", lines=2)
    submit_btn = gr.Button("🚀 Submit", size="lg")

    gr.Markdown("<hr><p style='text-align:center'>📌 <b>Not sure what to ask? Start with a topic:</b></p>")
    with gr.Row():
        fund_btn = gr.Button("📈 Funds", elem_classes="circle-btn")
        fx_btn = gr.Button("💱 Foreign Currency", elem_classes="circle-btn")
        bond_btn = gr.Button("🧾 Bonds", elem_classes="circle-btn")
        macro_btn = gr.Button("📊 What should I watch now?", elem_classes="circle-btn")

    fund_btn.click(fn=lambda: set_and_submit("Funds"), inputs=[], outputs=[user_input, chatbot_interface]).then(
        fn=chatbot, inputs=[user_input, chatbot_interface], outputs=[user_input, chatbot_interface]
    )
    fx_btn.click(fn=lambda: set_and_submit("Foreign Currency"), inputs=[], outputs=[user_input, chatbot_interface]).then(
        fn=chatbot, inputs=[user_input, chatbot_interface], outputs=[user_input, chatbot_interface]
    )
    bond_btn.click(fn=lambda: set_and_submit("Bonds"), inputs=[], outputs=[user_input, chatbot_interface]).then(
        fn=chatbot, inputs=[user_input, chatbot_interface], outputs=[user_input, chatbot_interface]
    )
    macro_btn.click(fn=lambda: set_and_submit("Macro"), inputs=[], outputs=[user_input, chatbot_interface]).then(
        fn=chatbot, inputs=[user_input, chatbot_interface], outputs=[user_input, chatbot_interface]
    )

    submit_btn.click(fn=chatbot, inputs=[user_input, chatbot_interface], outputs=[user_input, chatbot_interface])

    gr.Markdown("""
    <div style='background-color:#f4f4f5;border-radius:12px;padding:12px;margin-top:24px'>
      <b>☁️ Reminder:</b><br>
      This system is for educational purposes only and does not constitute financial advice.
      Please make decisions based on your own risk assessment.
    </div>
    """)

demo.launch()
