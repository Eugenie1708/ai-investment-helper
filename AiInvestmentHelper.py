import os
import random

import aisuite as ai
import gradio as gr
from dotenv import load_dotenv

# =====================================================
# 0) Load API key from .env
# =====================================================
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise RuntimeError(
        "❌ GROQ_API_KEY not found.\n"
        "Make sure .env is in the same folder and contains:\n"
        "GROQ_API_KEY=your_key_here"
    )
os.environ["GROQ_API_KEY"] = api_key

# =====================================================
# 1) Model setup (Groq)
# =====================================================
client = ai.Client()
PROVIDER = "groq"
MODEL = "llama-3.1-8b-instant"   # gemma2-9b-it is decommissioned

# =====================================================
# 2) Preset question buttons
# =====================================================
QUESTION_SETS = {
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

# =====================================================
# 3) LLM helper
# =====================================================
def call_llm(messages):
    resp = client.chat.completions.create(
        model=f"{PROVIDER}:{MODEL}",
        messages=messages,
    )
    return resp.choices[0].message.content.strip()

def generate_reasons(question: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a financial education assistant.\n"
                "Based on the user's question, list FIVE clear and constructive reasons explaining why, "
                "in this scenario, it may make sense to consider funds or bonds (non-trading products).\n"
                "Rewrite the user's question as a title, then respond in bullet points.\n"
                "Rules:\n"
                "- Educational only\n"
                "- No buy/sell instructions\n"
            ),
        },
        {"role": "user", "content": question},
    ]
    return call_llm(messages)

def classify_question(question: str) -> str:
    q = question.lower()
    if any(k in q for k in ["what is", "define", "definition", "difference", "compare", "vs", "versus"]):
        return "Knowledge"
    if any(k in q for k in ["how to invest", "recommend", "suggest", "what should i buy", "i want to invest"]):
        return "Advice"
    if any(k in q for k in ["is it suitable", "for me", "my situation", "i have", "my current"]):
        return "Personalized"
    return "Mixed"

def generate_advice(reasons: str, qtype: str) -> str:
    if qtype == "Knowledge":
        system_prompt = (
            "You are a financial education expert.\n"
            "Use the CONTEXT below.\n"
            "Explain in 3 bullet points, then add 1 sentence relating it to funds or bonds.\n"
            "End with: Educational use only."
        )
    elif qtype == "Personalized":
        system_prompt = (
            "You are a financial educator.\n"
            "Use the CONTEXT below.\n"
            "Provide 3 example allocations (percentages): Conservative / Balanced / Aggressive.\n"
            "Explain who each fits. No buy/sell instructions.\n"
            "End with: Not financial advice."
        )
    else:
        system_prompt = (
            "You are a professional investment educator.\n"
            "Use the CONTEXT below to give constructive guidance.\n"
            "Include asset direction + example allocation ratios + suitable profiles.\n"
            "End with: Educational use only."
        )

    messages = [
        {"role": "system", "content": system_prompt + "\n\nCONTEXT:\n" + reasons}
    ]
    return call_llm(messages)

# =====================================================
# 4) Chat handler (Gradio 6.x: messages format)
# =====================================================
def on_send(user_text, messages_state):
    user_text = (user_text or "").strip()
    if not user_text:
        return "", messages_state

    messages_state = messages_state or []

    # Add user message
    messages_state.append({"role": "user", "content": user_text})

    try:
        reasons = generate_reasons(user_text)
        qtype = classify_question(user_text)
        advice = generate_advice(reasons, qtype)

        assistant_html = (
            f"### 🤖 Investment Reasons\n\n"
            f"{reasons}\n\n"
            f"---\n\n"
            f"### ✅ Recommendation ({qtype})\n\n"
            f"{advice}\n\n"
            f"> Educational only — not financial advice."
        )


        messages_state.append({"role": "assistant", "content": assistant_html})
        return "", messages_state

    except Exception as e:
        messages_state.append({"role": "assistant", "content": f"❌ Error: {e}"})
        return "", messages_state

def pick_topic(topic: str) -> str:
    return random.choice(QUESTION_SETS[topic])

# =====================================================
# 5) UI (theme/css must be passed to launch in Gradio 6+)
# =====================================================
CSS = """
.circle-btn button {
    border-radius: 50px !important;
    padding: 12px 20px !important;
    font-size: 16px;
    background-color: #f0f2f5;
    border: 1px solid #d0d4d9;
}
"""

with gr.Blocks() as demo:
    gr.Markdown("""
    <div style="text-align:center;">
      <h2>AI Investment Helper</h2>
      <p>Ask one question to learn directions for funds and bonds (educational only)</p>
    </div>
    """)

    chatbot = gr.Chatbot(height=420)   # expects messages list in Gradio 6.x
    state = gr.State([])              # keep messages here

    user_box = gr.Textbox(placeholder="Type your investment question here...", lines=2)
    send_btn = gr.Button("🚀 Submit")

    gr.Markdown("<hr><p style='text-align:center'>📌 <b>Not sure what to ask? Start with a topic:</b></p>")
    with gr.Row():
        fund_btn = gr.Button("📈 Funds", elem_classes="circle-btn")
        bond_btn = gr.Button("🧾 Bonds", elem_classes="circle-btn")
        fx_btn = gr.Button("💱 Foreign Currency", elem_classes="circle-btn")
        macro_btn = gr.Button("📊 Macro / Market", elem_classes="circle-btn")

    # Send flow
    send_btn.click(fn=on_send, inputs=[user_box, state], outputs=[user_box, chatbot]).then(
        fn=lambda x: x, inputs=[chatbot], outputs=[state]
    )

    # Topic buttons: put text -> send -> sync state
    fund_btn.click(fn=lambda: pick_topic("Funds"), inputs=[], outputs=[user_box]).then(
        fn=on_send, inputs=[user_box, state], outputs=[user_box, chatbot]
    ).then(fn=lambda x: x, inputs=[chatbot], outputs=[state])

    bond_btn.click(fn=lambda: pick_topic("Bonds"), inputs=[], outputs=[user_box]).then(
        fn=on_send, inputs=[user_box, state], outputs=[user_box, chatbot]
    ).then(fn=lambda x: x, inputs=[chatbot], outputs=[state])

    fx_btn.click(fn=lambda: pick_topic("Foreign Currency"), inputs=[], outputs=[user_box]).then(
        fn=on_send, inputs=[user_box, state], outputs=[user_box, chatbot]
    ).then(fn=lambda x: x, inputs=[chatbot], outputs=[state])

    macro_btn.click(fn=lambda: pick_topic("Macro"), inputs=[], outputs=[user_box]).then(
        fn=on_send, inputs=[user_box, state], outputs=[user_box, chatbot]
    ).then(fn=lambda x: x, inputs=[chatbot], outputs=[state])

    gr.Markdown("""
    <div style="margin-top:20px; padding:10px; background:#f4f4f5; border-radius:10px;">
      ⚠️ Educational only — not financial advice.
    </div>
    """)

demo.launch(server_name="127.0.0.1", server_port=7860, share=False, theme=gr.themes.Soft(), css=CSS)
